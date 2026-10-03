@echo off
REM Setup script for audio-transcriber (Windows)
REM Run: setup.bat

echo === Audio Transcriber Setup ===

cd /d "%~dp0"

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists.
)

echo Installing Python dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo === Setup complete ===
echo.
echo To use:
echo   cd "%~dp0"
echo   venv\Scripts\activate.bat
echo   python transcribe.py ^<audio_file.mp3^>
