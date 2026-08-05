@echo off
setlocal
cd /d "%~dp0\.."
title J.A.R.V.I.S (Lite)
echo Starting J.A.R.V.I.S in Lite mode (no HUD, lower RAM)...
echo Say "hey jarvis" when ready. Ctrl+C to quit.
echo.
python -u main.py
echo.
echo J.A.R.V.I.S stopped.
pause
