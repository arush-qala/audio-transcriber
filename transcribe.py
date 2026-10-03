#!/usr/bin/env python3
"""
Audio Transcriber — converts audio files to text with speaker diarization
via Deepgram's Nova-3 API.

Supports: mp3, wav, m4a, flac, ogg, webm, mp4, aac, wma

Usage:
    python transcribe.py recording.mp3
    python transcribe.py recording.mp3 -o transcript.txt
    python transcribe.py recording.mp3 --print-only

Output format:
    [Speaker 0] (00:00): Hello, thanks for joining us today.
    [Speaker 1] (00:03): Thanks for having me.

Requires: DEEPGRAM_API_KEY in .env file or environment variable.
"""

import argparse
import os
import sys
import time

import requests
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

API_URL = "https://api.deepgram.com/v1/listen"
MODEL = "nova-3"
LANGUAGE = "multi"

MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".webm": "audio/webm",
    ".mp4": "audio/mp4",
    ".aac": "audio/aac",
    ".wma": "audio/x-ms-wma",
}


def get_api_key() -> str:
    key = os.environ.get("DEEPGRAM_API_KEY")
    if not key:
        print("Error: DEEPGRAM_API_KEY not found.", file=sys.stderr)
        print("Add it to the .env file or set it as an environment variable.", file=sys.stderr)
        sys.exit(1)
    return key


def format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def transcribe(audio_path: str, api_key: str, model: str = MODEL, language: str = LANGUAGE) -> dict:
    """Send audio file to Deepgram and return the full API response."""
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    ext = os.path.splitext(audio_path)[1].lower()
    content_type = MIME_TYPES.get(ext, "audio/mpeg")

    print(f"File: {os.path.basename(audio_path)} ({file_size_mb:.1f} MB)")
    print(f"Uploading and transcribing with {model} (language={language}) + diarization...")

    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": content_type,
    }
    params = {
        "model": model,
        "diarize": "true",
        "smart_format": "true",
        "utterances": "true",
        "language": language,
    }

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    resp = requests.post(API_URL, headers=headers, params=params, data=audio_data)

    if resp.status_code != 200:
        print(f"API error ({resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)

    return resp.json()


def format_diarized_transcript(result: dict) -> str:
    """Format the API response into a readable speaker-labeled transcript."""
    utterances = result.get("results", {}).get("utterances", [])

    if not utterances:
        # Fallback to plain transcript if utterances not available
        return result["results"]["channels"][0]["alternatives"][0].get("transcript", "")

    lines = []
    for utt in utterances:
        speaker = utt["speaker"]
        ts = format_timestamp(utt["start"])
        text = utt["transcript"]
        lines.append(f"[Speaker {speaker}] ({ts}): {text}")

    return "\n\n".join(lines)


def format_plain_transcript(result: dict) -> str:
    """Extract just the plain text transcript without speaker labels."""
    return result["results"]["channels"][0]["alternatives"][0].get("transcript", "")


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe mp3 audio files with speaker diarization via Deepgram."
    )
    parser.add_argument("file", help="Path to the audio file (mp3, wav, m4a, flac, etc.)")
    parser.add_argument("-o", "--output", help="Output file path (default: <filename>_transcript.txt)")
    parser.add_argument("--print-only", action="store_true",
                        help="Print transcript to stdout without saving to file")
    parser.add_argument("--no-diarize", action="store_true",
                        help="Skip speaker diarization, output plain text only")
    parser.add_argument("--model", default=MODEL,
                        help="Deepgram model (default: nova-3). e.g. nova-3, nova-2")
    parser.add_argument("--language", default=LANGUAGE,
                        help="Language code or multi (default: multi). e.g. en, es, hi")

    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    api_key = get_api_key()

    start = time.time()
    result = transcribe(args.file, api_key, model=args.model, language=args.language)
    elapsed = time.time() - start

    duration = result.get("metadata", {}).get("duration", 0)
    print(f"Audio duration: {format_timestamp(duration)}")
    print(f"Processing time: {elapsed:.1f}s")

    if args.no_diarize:
        transcript = format_plain_transcript(result)
    else:
        transcript = format_diarized_transcript(result)

    if args.print_only:
        print("\n--- Transcript ---\n")
        print(transcript)
        return

    if args.output:
        out_path = args.output
    else:
        stem = os.path.splitext(os.path.basename(args.file))[0]
        out_dir = os.path.dirname(os.path.abspath(args.file))
        out_path = os.path.join(out_dir, f"{stem}_transcript.txt")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(transcript)

    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
