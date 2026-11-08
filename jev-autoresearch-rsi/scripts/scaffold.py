#!/usr/bin/env python3
"""
Create a new Jev Autoresearch RSI project from the template. Standard library only; works on Windows, macOS and Linux.

    python scaffold.py ./my-autoresearch --topic "Agentic autoresearch" --kb-root "~/Vault/知識庫/My Topic" \
        --owner "Dr. X" --blog-author "Dr. X" --blog-site https://example.org --notebook <notebooklm-id>

Refuses to write into a folder that already has files, so it cannot overwrite existing work.
Also copies the three Jev subagents into <target>/.claude/agents/ for Claude Code.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL / "assets" / "template"
RENAMES = {"gitignore.txt": ".gitignore", "env.example.txt": ".env.example"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", type=Path)
    parser.add_argument("--title", default="Autoresearch RSI Knowledge Dashboard")
    parser.add_argument("--owner", default="")
    parser.add_argument("--topic", default="")
    parser.add_argument("--language", default="en", choices=["en", "zh-TW"], help="Paper and deck language")
    parser.add_argument("--blog-language", default="zh-TW", choices=["en", "zh-TW"])
    parser.add_argument("--kb-root", default="", help="Folder for the wiki, ideally inside an Obsidian vault. Empty = ./knowledge_base")
    parser.add_argument("--kb-queue", default="", help="Optional markdown file that mirrors KB RSI decisions")
    parser.add_argument("--notebook", default="", help="NotebookLM / Gemini Notebook id queried through the nlm CLI")
    parser.add_argument("--blog-author", default="")
    parser.add_argument("--blog-site", default="https://example.org", help="Public site root used in the sitemap entry")
    parser.add_argument("--no-clinical-trials", action="store_true")
    parser.add_argument("--claude-only", action="store_true", help="Drop the OpenAI and Gemini models from the tiers")
    args = parser.parse_args()

    if args.target.exists() and any(args.target.iterdir()):
        print(f"Refusing to write: {args.target} is not empty.", file=sys.stderr)
        return 1

    shutil.copytree(TEMPLATE, args.target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".rsi", "outputs", "desktop.ini"))
    for old, new in RENAMES.items():
        (args.target / old).rename(args.target / new)
    for folder in ("references/saved_answers", "outputs"):
        (args.target / folder).mkdir(parents=True, exist_ok=True)
    (args.target / ".phi_blocklist.txt").write_text(
        "# Known identifiers, one per line. Text containing any of these is rejected.\n"
        "# This is a safety net for names you already know, not de-identification. Never commit this file.\n",
        encoding="utf-8",
    )
    agents = args.target / ".claude" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    for md in (SKILL / "agents").glob("jev-*.md"):
        shutil.copy2(md, agents / md.name)

    path = args.target / "project.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    config.update(title=args.title, owner=args.owner, default_topic=args.topic, language=args.language,
                  blog_language=args.blog_language)
    config["sources"]["clinical_trials"] = not args.no_clinical_trials
    config["sources"]["notebooklm_id"] = args.notebook
    kb_root = str(Path(args.kb_root).expanduser()).replace("\\", "/") if args.kb_root else ""
    kb_queue = str(Path(args.kb_queue).expanduser()).replace("\\", "/") if args.kb_queue else ""
    config["knowledge_base"].update(root=kb_root, queue_md=kb_queue)
    config["blog"].update(author=args.blog_author, site_url=args.blog_site)
    if args.claude_only:
        config["tiers"] = {t: [m for m in refs if m.startswith("claude:")] for t, refs in config["tiers"].items()}
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Created {args.target}")
    print("Next:")
    print("  1. Copy .env.example to .env and add only the keys you use (never commit .env).")
    print("  2. Re-check model ids and prices:  python run_agent.py --models openai   (and gemini)")
    print("  3. No-spend check:                 python run_agent.py --check")
    print("  4. Offline tests, then the dashboard: start_dashboard.ps1 / start_dashboard.sh  (http://127.0.0.1:8090/)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
