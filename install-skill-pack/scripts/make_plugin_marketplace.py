#!/usr/bin/env python3
"""Turn a downloaded skills repo (with a top-level skills/ dir) into an installable
LOCAL Claude Code plugin by writing .claude-plugin/plugin.json + marketplace.json.

Cross-platform (Windows / macOS / Linux). Standard library only.

After running, install it from an INTERACTIVE Claude Code session (one line at a time):
    /plugin marketplace add <repo-path-without-spaces>
    /plugin install <plugin-name>@<marketplace-name>

If the repo path contains spaces, make a space-free link first and point /plugin at it:
    Windows (PowerShell): New-Item -ItemType Junction -Path C:\\Skills\\pack -Target "C:\\path with spaces"
    macOS / Linux:        ln -s "/path with spaces" ~/skills-pack

Examples:
    python make_plugin_marketplace.py --repo "D:/Medical_Science skill" \
        --plugin medical-science-skills --marketplace medical-science --owner kwotachu
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="path to the skills repo (its root)")
    ap.add_argument("--plugin", required=True, help="plugin name, kebab-case")
    ap.add_argument("--marketplace", required=True, help="marketplace name, kebab-case")
    ap.add_argument("--owner", default="local", help="owner/author name")
    ap.add_argument("--description", default="Local skill pack", help="plugin description")
    a = ap.parse_args()

    repo = Path(a.repo).expanduser().resolve()
    if not repo.is_dir():
        raise SystemExit(f"repo not found: {repo}")
    cp = repo / ".claude-plugin"
    cp.mkdir(parents=True, exist_ok=True)

    if not (repo / "skills").is_dir():
        print(f"WARNING: {repo / 'skills'} not found. A plugin auto-discovers a top-level skills/ dir; "
              "make sure the repo has one (or a single SKILL.md at the root).")

    plugin = {
        "name": a.plugin,
        "description": a.description,
        "version": "1.0.0",
        "author": {"name": a.owner},
    }
    marketplace = {
        "name": a.marketplace,
        "owner": {"name": a.owner},
        "plugins": [
            {"name": a.plugin, "source": ".", "description": a.description}
        ],
    }
    (cp / "plugin.json").write_text(json.dumps(plugin, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (cp / "marketplace.json").write_text(json.dumps(marketplace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("Wrote:")
    print("  ", cp / "plugin.json")
    print("  ", cp / "marketplace.json")
    print("\nNext — inside an interactive Claude Code session, ONE LINE AT A TIME:")
    print(f"  /plugin marketplace add {repo}")
    print(f"  /plugin install {a.plugin}@{a.marketplace}")
    if " " in str(repo):
        print("\nNOTE: the path contains a space. `/plugin marketplace add` may reject it.")
        print("Make a space-free junction/symlink and point /plugin at THAT instead (see header).")


if __name__ == "__main__":
    main()
