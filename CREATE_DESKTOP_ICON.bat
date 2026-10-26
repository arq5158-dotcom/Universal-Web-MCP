@echo off
setlocal
title Ashzo MCP setup
cd /d "%~dp0"
echo.
echo  Ashzo MCP: one-time setup and desktop icon
echo  ------------------------------------------

if not exist ".venv\Scripts\python.exe" (
  echo  Creating the Python environment ^(.venv^)...
  py -3 -m venv .venv 2>nul || python -m venv .venv
  if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  Python 3.10+ is needed. Install it from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^), then run this again.
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" -c "import fastapi, uvicorn, playwright, mcp, httpx" 1>nul 2>nul
if errorlevel 1 (
  echo  Installing what Ashzo MCP needs ^(first run only, a few minutes^)...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo  Installing failed. Check your internet connection and run this again.
    pause
    exit /b 1
  )
  ".venv\Scripts\python.exe" -m playwright install chromium
)

echo  Creating the desktop icon...
".venv\Scripts\python.exe" create_desktop_shortcut.py
if errorlevel 1 (
  pause
  exit /b 1
)

echo.
echo  Done. Starting Ashzo MCP...
start "" ".venv\Scripts\pythonw.exe" launch_ashzo.py
timeout /t 4 >nul
endlocal
