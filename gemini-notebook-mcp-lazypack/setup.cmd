@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY (
  echo Python 3 was not found. Install it with: winget install Python.Python.3.12
  echo Then run this file again.
  pause
  exit /b 1
)
%PY% gemini_notebook_mcp.py %*
set "CODE=%ERRORLEVEL%"
echo.
pause
exit /b %CODE%
