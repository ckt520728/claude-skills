# Starts the dashboard on Windows. Keep this window open while you use it.
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONIOENCODING = "utf-8"
Start-Job -ScriptBlock { Start-Sleep -Seconds 6; Start-Process "http://127.0.0.1:8080/" } | Out-Null
uv run --no-project --python 3.12 --with-requirements requirements.txt python run_ui.py
