@echo off
setlocal
cd /d "%~dp0\..\desktop"
title J.A.R.V.I.S HUD
if not exist node_modules (
  echo Installing Electron dependencies...
  call npm install
)
echo Starting J.A.R.V.I.S HUD...
call npm start
