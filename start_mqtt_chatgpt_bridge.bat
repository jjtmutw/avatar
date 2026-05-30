@echo off
cd /d "%~dp0"
if "%OPENAI_API_KEY%"=="" (
  set /p OPENAI_API_KEY=Paste OPENAI_API_KEY and press Enter: 
)
if "%OPENAI_MODEL%"=="" set OPENAI_MODEL=gpt-4o-mini
python mqtt_chatgpt_bridge.py
pause
