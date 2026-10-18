@echo off
cd /d "%~dp0"
if exist "dist\Voice2Txt\Voice2Txt.exe" (
  start "" "dist\Voice2Txt\Voice2Txt.exe"
) else (
  ".venv\Scripts\python.exe" run_desktop.py
  if errorlevel 1 pause
)
