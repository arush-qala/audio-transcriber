#!/bin/bash
# Setup script for audio-transcriber
# Run: bash setup.sh

set -e

echo "=== Audio Transcriber Setup ==="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

echo "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Setup complete ==="
echo ""
echo "To use:"
echo "  cd \"$SCRIPT_DIR\""
echo "  source venv/bin/activate"
echo "  python transcribe.py <audio_file.mp3>"
