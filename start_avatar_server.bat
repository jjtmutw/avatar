@echo off
cd /d "%~dp0"
echo Starting XiaoZheng Avatar server...
echo.
echo Open this URL in your browser:
echo http://localhost:8765/ai_avatar_realtime.html?mqtt=1
echo.
echo Keep this window open while using the avatar page.
echo Press Ctrl+C to stop.
echo.
python -m http.server 8765 --bind 127.0.0.1
pause
