# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Model upgrade check (every session)

Every time you read this file or touch audio-transcriber files, check Deepgram
for newer speech-to-text models before doing other work:

1. Fetch `https://developers.deepgram.com/docs/models-languages-overview`
   and `https://developers.deepgram.com/changelog`.
2. Note the current defaults in `transcribe.py` (`MODEL`, `LANGUAGE`) and the
   `index.html` model dropdown.
3. If a newer general-purpose model exists (e.g. Nova-4, Nova-5, new Flux
   generation) that fits file transcription + diarization, tell the user what
   it is, how accuracy, capability, and cost compare, and the exact param
   change needed.
4. Suggest only. Never change model defaults without explicit approval.

## What this is

A thin client over Deepgram's hosted speech-to-text API (`nova-3` multilingual model) with speaker
diarization. There is no local ML — all transcription happens on Deepgram's servers. The
project ships two independent front-ends over the same API: a Python CLI and a browser UI
backed by a tiny proxy.

## Commands

```bash
bash setup.sh                          # creates venv/, installs requests + python-dotenv

source venv/bin/activate
python transcribe.py recording.mp3     # -> recording_transcript.txt (next to the input)
python transcribe.py rec.mp3 -o out.txt
python transcribe.py rec.mp3 --print-only      # stdout, no file
python transcribe.py rec.mp3 --no-diarize      # plain text, no speaker labels

python serve.py                        # web UI at http://localhost:8000 (opens browser)
python serve.py 3000                   # custom port
python serve.py --no-browser           # don't auto-open
```

There are no tests, linters, or build step. This is a git repository pushed to
GitHub as a public repo (see README.md); `.env` is git-ignored and must never
be committed.

## Architecture

Two entry points hit the same Deepgram endpoint (`https://api.deepgram.com/v1/listen`),
sending raw audio bytes as the POST body with options passed as URL query params:

- **`transcribe.py`** — standalone CLI. Builds the query params dict in `transcribe()`,
  POSTs via `requests`, then `format_diarized_transcript()` turns the `results.utterances[]`
  array into `[Speaker N] (mm:ss): text` lines. Falls back to the plain channel transcript
  if utterances are absent.
- **`serve.py` + `index.html`** — the web stack. `index.html` is a single self-contained
  file (inline CSS + vanilla JS, no framework, no build). `serve.py` is a **stdlib-only**
  HTTP server (no pip deps) whose only real job is to proxy `POST /api/transcribe` to
  Deepgram — the browser can't call Deepgram directly because of CORS. The proxy forwards
  the query string **verbatim** and copies the audio body through unchanged; it does not
  parse or modify the Deepgram options.

### Two different API-key mechanisms (important)

- CLI reads `DEEPGRAM_API_KEY` from `.env` (via `python-dotenv`) or the environment.
- Web UI takes the key from a browser input, stores it in `localStorage`, and sends it
  per-request in the `X-Api-Key` header. `serve.py` reads that header and rewrites it as
  Deepgram's `Authorization: Token <key>`. The `.env` key is never used by the web path.

### Where Deepgram options live

- `transcribe.py` — defaults `MODEL = "nova-3"`, `LANGUAGE = "multi"`.
  Override per-run with `--model` / `--language`
  (e.g. `--model nova-2 --language en`, `--model nova-3 --language hi`).
- Web UI (`index.html`) — `Model` dropdown (default Nova-3 multilingual):
  Nova-3 multi (`language=multi`), Nova-3 single (reveals a `Language`
  dropdown, default `en`), Nova-2 (`language=en`). `buildParams()` assembles
  the query string; `serve.py` forwards it verbatim and needs no change.

## Gotchas

- **Duplicated `MIME_TYPES`** map exists in both `transcribe.py:34` and `index.html:463`;
  the supported-extension list in `index.html` (dropzone `accept`, `SUPPORTED_EXT`) must
  match too.
- **Two virtualenvs** are present on disk: `venv/` (what `setup.sh` creates and the docs
  assume) and a stray `.venv/`. Use `venv/`.
- `serve.py` builds its own SSL context with a `certifi` → system-cert fallback
  (`_build_ssl_context`) to avoid macOS cert-verification failures; keep that if touching
  the proxy.
- Large files: the proxy uses a 600s timeout and the browser XHR matches it; transcription
  is single-shot (no chunking) and relies on Deepgram handling files up to ~2GB.
