# Audio Transcriber

Turn audio files into readable transcripts with speaker labels, powered by Deepgram's Nova-3 speech-to-text API.

Built for interviews, meetings, lectures, and Voice Memos recordings where you need to know who said what and when.

## What it does

- Transcribes `mp3, wav, m4a, flac, ogg, webm, mp4, aac, wma`
- Speaker diarization: `[Speaker 0] (00:02): Hello...`
- Two ways to use it: command line script or browser UI with drag and drop
- Model picker in the web UI: Nova-3 multilingual (default), Nova-3 single language with full language list, Nova-2
- Smart formatting, utterances with timestamps, copy and download as `.txt`

No local ML. Audio is sent to Deepgram's hosted API for transcription.

## Requirements

- Python 3.9+
- A Deepgram API key (pay as you go, pre-recorded Nova-3 monolingual is about $0.0043/min, multilingual about $0.0052/min, diarization included free on pre-recorded)

## Install

```bash
bash setup.sh
source venv/bin/activate
```

Create a `.env` file in this folder (never commit it):

```
DEEPGRAM_API_KEY=your_key_here
```

## Use

### Option 1: Browser UI (easiest)

```bash
python serve.py
```

Open `http://localhost:8000`, paste your API key once, pick a model from the dropdown, drop in an audio file, click Transcribe.

macOS Voice Memos tip: drag the memo from Voice Memos to your Desktop first to get the `.m4a` file, then drag that file into the page. Direct drag from Voice Memos into the browser is not supported by Apple.

### Option 2: Command line

```bash
source venv/bin/activate
python transcribe.py recording.mp3
python transcribe.py recording.mp3 -o transcript.txt
python transcribe.py recording.mp3 --print-only
python transcribe.py recording.mp3 --model nova-3 --language multi
python transcribe.py recording.mp3 --model nova-3 --language en
python transcribe.py recording.mp3 --model nova-2 --language en
```

Defaults are `--model nova-3 --language multi`.

## Models

| Choice | Params | Best for |
|---|---|---|
| Nova-3 multilingual (default) | `model=nova-3&language=multi` | Mixed-language audio (en, es, fr, de, hi, ru, pt, ja, it, nl), also fine on English-only |
| Nova-3 single | `model=nova-3&language=<code>` | One known language, cheapest rate, 60+ codes supported |
| Nova-2 | `model=nova-2&language=en` | Legacy, filler-word use cases |

## Files

- `transcribe.py` - CLI, sends file bytes to `https://api.deepgram.com/v1/listen`
- `serve.py` - stdlib-only local server, serves `index.html` and proxies `/api/transcribe` to Deepgram (browsers cannot call Deepgram directly due to CORS)
- `index.html` - self-contained UI, no framework, no build step

## Privacy

Your API key stays local: CLI reads it from `.env`, web UI stores it in browser `localStorage` and sends it per-request as `X-Api-Key` which the proxy rewrites to Deepgram's auth header.
