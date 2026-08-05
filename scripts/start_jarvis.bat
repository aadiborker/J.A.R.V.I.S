@echo off
setlocal
cd /d "%~dp0\.."
title J.A.R.V.I.S
echo Starting J.A.R.V.I.S...
echo Say "hey jarvis" when ready. Close this window or Ctrl+C to stop.
echo.
python main.py
echo.
echo J.A.R.V.I.S stopped.
pause
