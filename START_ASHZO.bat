@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" launch_ashzo.py
) else (
  echo First run: double-click CREATE_DESKTOP_ICON.bat to set things up.
  pause
)
