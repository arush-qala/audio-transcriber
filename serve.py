#!/usr/bin/env python3
"""
Minimal proxy server for the audio transcriber web frontend.

Serves index.html and proxies API calls to Deepgram (which blocks CORS).
Uses only Python stdlib — no pip dependencies.

Usage:
    python serve.py          # starts on port 8000
    python serve.py 3000     # starts on port 3000
"""

import http.server
import json
import os
import ssl
import sys
import threading
import traceback
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

args = [a for a in sys.argv[1:] if a != "--no-browser"]
NO_BROWSER = "--no-browser" in sys.argv
PORT = int(args[0]) if args else 8000
DEEPGRAM_API = "https://api.deepgram.com/v1/listen"
DEEPGRAM_PROJECTS = "https://api.deepgram.com/v1/projects"
TIMEOUT = 600  # 10 minutes for large files


def _build_ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    for path in ("/etc/ssl/cert.pem", "/usr/local/etc/openssl@3/cert.pem"):
        if os.path.exists(path):
            return ssl.create_default_context(cafile=path)
    return ssl.create_default_context()


SSL_CONTEXT = _build_ssl_context()


def _sum_balances(payload):
    """Sum balance amounts from a Deepgram /balances response.

    Returns (total: float rounded to 2dp, units: str). Sums every record's
    `amount`; takes `units` from the first record, defaulting to 'usd'.
    """
    balances = payload.get("balances", []) if isinstance(payload, dict) else []
    total = 0.0
    units = "usd"
    for i, b in enumerate(balances):
        try:
            total += float(b.get("amount", 0) or 0)
        except (TypeError, ValueError):
            pass
        if i == 0 and b.get("units"):
            units = b["units"]
    return round(total, 2), units


class Handler(http.server.SimpleHTTPRequestHandler):

    def _send_json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _deepgram_get(self, url, api_key):
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", f"Token {api_key}")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as resp:
            return json.loads(resp.read())

    def do_GET(self):
        if self.path.startswith("/api/balance"):
            self.proxy_balance()
        else:
            super().do_GET()

    def proxy_balance(self):
        api_key = self.headers.get("X-Api-Key", "")
        if not api_key:
            self._send_json(401, {"err_msg": "Missing API key"})
            return
        try:
            projects = self._deepgram_get(DEEPGRAM_PROJECTS, api_key)
            plist = projects.get("projects", []) if isinstance(projects, dict) else []
            if not plist:
                self._send_json(200, {"available": False, "reason": "no_projects"})
                return
            project = plist[0]
            pid = project.get("project_id")
            balances = self._deepgram_get(f"{DEEPGRAM_PROJECTS}/{pid}/balances", api_key)
            total, units = _sum_balances(balances)
            self._send_json(200, {
                "balance": total,
                "units": units,
                "project_id": pid,
                "project_name": project.get("name", ""),
            })
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode(errors="replace")[:300]
            except Exception:
                detail = ""
            self._send_json(e.code, {"err_msg": f"Deepgram {e.code}", "detail": detail})
        except Exception as e:
            print(f"[balance error] {type(e).__name__}: {e}", file=sys.stderr)
            self._send_json(502, {"err_msg": f"{type(e).__name__}: {e}"})

    def do_POST(self):
        if self.path.startswith("/api/transcribe"):
            self.proxy_to_deepgram()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Api-Key")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def proxy_to_deepgram(self):
        parsed = urllib.parse.urlparse(self.path)
        query = parsed.query

        api_key = self.headers.get("X-Api-Key", "")
        content_type = self.headers.get("Content-Type", "audio/mpeg")
        content_length = int(self.headers.get("Content-Length", 0))

        body = self.rfile.read(content_length)

        url = f"{DEEPGRAM_API}?{query}"
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Authorization", f"Token {api_key}")
        req.add_header("Content-Type", content_type)

        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CONTEXT) as resp:
                result = resp.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(result)
        except urllib.error.HTTPError as e:
            error_body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(error_body)
        except Exception as e:
            print(f"[proxy error] {type(e).__name__}: {e}", file=sys.stderr)
            traceback.print_exc()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            payload = {"err_msg": f"{type(e).__name__}: {e}"}
            self.wfile.write(json.dumps(payload).encode())

    def log_message(self, format, *args):
        if "/api/" in str(args[0]):
            super().log_message(format, *args)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = http.server.HTTPServer(("", PORT), Handler)
    print(f"Audio Transcriber running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop.\n")
    if not NO_BROWSER:
        print("Opening browser...")
        threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
