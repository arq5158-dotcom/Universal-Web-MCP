@echo off
setlocal
title Ashzo MCP (Docker) setup
cd /d "%~dp0"
echo.
echo  Ashzo MCP (Docker): build the app and create the desktop icon
echo  ------------------------------------------------------------
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0docker\Ashzo-Docker.ps1" -Setup
if errorlevel 1 (
  echo.
  echo  Setup did not finish. The message above says why.
  pause
  exit /b 1
)
echo.
echo  Done. Double-click "Ashzo MCP (Docker)" on your desktop any time to open it.
pause
endlocal
