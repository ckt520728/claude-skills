@echo off
cd /d "%~dp0"
".build-venv\Scripts\python.exe" scripts\open_mobile.py
if errorlevel 1 pause
