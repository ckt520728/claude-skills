#!/usr/bin/env bash
# macOS and Linux launcher. Run with: bash setup.sh
set -e
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
  exec python3 gemini_notebook_mcp.py "$@"
elif command -v python >/dev/null 2>&1; then
  exec python gemini_notebook_mcp.py "$@"
fi
echo "Python 3 was not found. Install it, then run this again." >&2
exit 1
