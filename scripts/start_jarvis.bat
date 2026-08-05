@echo off
setlocal
cd /d "%~dp0\.."
title J.A.R.V.I.S
echo Starting J.A.R.V.I.S...
echo.
python -u main.py
echo.
echo J.A.R.V.I.S stopped.
pause
