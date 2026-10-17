@echo off
rem Serves this folder at http://localhost:8000/ so the 3-D explorer can load its modules and data.
cd /d "%~dp0"
start "" http://localhost:8000/explorer.html
python -m http.server 8000
