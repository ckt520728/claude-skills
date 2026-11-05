#!/usr/bin/env bash
# Starts the dashboard on macOS or Linux. Keep this terminal open while you use it.
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1
exec uv run --no-project --python 3.12 --with-requirements requirements.txt python run_ui.py
