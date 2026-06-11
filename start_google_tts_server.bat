@echo off
cd /d "%~dp0"
if "%GOOGLE_TTS_API_KEY%"=="" (
  set /p GOOGLE_TTS_API_KEY=Paste GOOGLE_TTS_API_KEY and press Enter: 
)
if "%GOOGLE_TTS_PORT%"=="" set GOOGLE_TTS_PORT=5058
if "%GOOGLE_TTS_LANGUAGE%"=="" set GOOGLE_TTS_LANGUAGE=cmn-TW
if "%GOOGLE_TTS_VOICE%"=="" set GOOGLE_TTS_VOICE=cmn-TW-Wavenet-A
python google_tts_server.py
pause
