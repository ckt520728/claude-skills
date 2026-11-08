"""Project settings from project.json, and local secrets from .env. Works the same on any OS."""

from __future__ import annotations

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
RUNS_DIR = OUTPUT_DIR / "runs"
REFERENCES_DIR = BASE_DIR / "references"
SAVED_ANSWERS_DIR = REFERENCES_DIR / "saved_answers"
RSI_DIR = BASE_DIR / ".rsi"
PHI_FILE = BASE_DIR / ".phi_blocklist.txt"


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


_load_env(BASE_DIR / ".env")
CONFIG = json.loads((BASE_DIR / "project.json").read_text(encoding="utf-8"))
LANGUAGE = CONFIG.get("language", "en")
LANGUAGE_NAME = {"zh-TW": "Traditional Chinese (Taiwan)", "en": "English"}.get(LANGUAGE, LANGUAGE)
