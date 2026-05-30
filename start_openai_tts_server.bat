@echo off
cd /d "%~dp0"
if "%OPENAI_API_KEY%"=="" (
  echo Please set OPENAI_API_KEY before starting this server.
  pause
  exit /b 1
)
python openai_tts_server.py
