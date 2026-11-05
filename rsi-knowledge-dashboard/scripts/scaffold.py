#!/usr/bin/env python3
"""
Create a new RSI knowledge dashboard project from the template. Standard library only.

    python scaffold.py ./my-dashboard --title "My Dashboard" --topic "CRISPR base editing" --language en

Refuses to write into a folder that already has files, so it cannot overwrite existing work.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template"
RENAMES = {"gitignore.txt": ".gitignore", "env.example.txt": ".env.example"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", type=Path)
    parser.add_argument("--title", default="RSI Knowledge Dashboard")
    parser.add_argument("--owner", default="")
    parser.add_argument("--topic", default="")
    parser.add_argument("--language", default="en", choices=["en", "zh-TW"])
    parser.add_argument("--provider", default="claude", choices=["claude", "openai_compatible"])
    parser.add_argument("--clinical-trials", action="store_true", help="Also search ClinicalTrials.gov")
    args = parser.parse_args()

    if args.target.exists() and any(args.target.iterdir()):
        print(f"Refusing to write: {args.target} is not empty.", file=sys.stderr)
        return 1

    shutil.copytree(TEMPLATE, args.target, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".rsi", "outputs", "desktop.ini"))
    for old, new in RENAMES.items():
        (args.target / old).rename(args.target / new)
    for folder in ("references/saved_answers", "outputs"):
        (args.target / folder).mkdir(parents=True, exist_ok=True)
    (args.target / ".phi_blocklist.txt").write_text(
        "# Known identifiers, one per line. Text containing any of these is rejected.\n"
        "# This is a safety net for names you already know, not de-identification. Never commit this file.\n",
        encoding="utf-8",
    )

    path = args.target / "project.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    config.update(title=args.title, owner=args.owner, default_topic=args.topic, language=args.language)
    config["sources"]["clinical_trials"] = args.clinical_trials
    if args.provider == "openai_compatible":
        config["provider"] = {
            "type": "openai_compatible", "base_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY",
            "models": ["SET-YOUR-MODEL"], "default_model": "SET-YOUR-MODEL", "price_per_mtok": {"input": 0, "output": 0},
        }
        print('Edit provider in project.json: set base_url, models and price_per_mtok. For a local model, add "free": true.')
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Created {args.target}")
    print("Next: put PDFs in references/, add known identifiers to .phi_blocklist.txt, then run start_dashboard.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
