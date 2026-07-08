#!/usr/bin/env python3
"""Install skills from a downloaded repo into the GLOBAL skills dir
(~/.claude/skills on macOS/Linux, %USERPROFILE%\\.claude\\skills on Windows).

Cross-platform (Windows / macOS / Linux). Standard library only.
Flattens nested layouts (skills/engineering/<name>/ -> ~/.claude/skills/<name>/)
and skips deprecated/.

Examples:
    # Install the repo's "released" set from its plugin.json:
    python install_global_skills.py --repo "D:/mattpocock-skills" --from-manifest

    # Pick specific skills:
    python install_global_skills.py --repo "D:/mattpocock-skills" --only code-review,tdd,research

    # Symlink instead of copy (auto-updates on git pull; needs Developer Mode/admin on Windows):
    python install_global_skills.py --repo "./skills-repo" --symlink
"""
import argparse
import json
import shutil
from pathlib import Path


def find_leaf_skills(repo: Path):
    """Every directory containing a SKILL.md, excluding deprecated."""
    out = {}
    for p in repo.rglob("SKILL.md"):
        parts = {x.lower() for x in p.parts}
        if "deprecated" in parts:
            continue
        out[p.parent.name] = p.parent
    return out


def from_manifest(repo: Path):
    """Skill dirs listed in the repo's plugin.json 'skills' array, if present."""
    for mpath in (repo / ".claude-plugin" / "plugin.json", repo / "plugin.json"):
        if mpath.is_file():
            try:
                data = json.loads(mpath.read_text(encoding="utf-8"))
            except Exception:
                continue
            out = {}
            for s in data.get("skills", []):
                d = (repo / str(s).replace("./", "")).resolve()
                if (d / "SKILL.md").is_file():
                    out[d.name] = d
            if out:
                return out
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--dest", default=str(Path.home() / ".claude" / "skills"))
    ap.add_argument("--from-manifest", action="store_true", help="use the repo's plugin.json skills list")
    ap.add_argument("--only", help="comma-separated skill folder names")
    ap.add_argument("--symlink", action="store_true", help="symlink instead of copy")
    a = ap.parse_args()

    repo = Path(a.repo).expanduser().resolve()
    if not repo.is_dir():
        raise SystemExit(f"repo not found: {repo}")
    dest = Path(a.dest).expanduser()
    dest.mkdir(parents=True, exist_ok=True)

    if a.from_manifest:
        skills = from_manifest(repo)
        if not skills:
            print("No usable plugin.json skills list; falling back to SKILL.md scan.")
            skills = find_leaf_skills(repo)
    else:
        skills = find_leaf_skills(repo)

    if a.only:
        want = {x.strip() for x in a.only.split(",") if x.strip()}
        skills = {k: v for k, v in skills.items() if k in want}

    if not skills:
        raise SystemExit("No skills matched.")

    done, failed = [], []
    for name, src in sorted(skills.items()):
        target = dest / name
        try:
            if target.is_symlink() or target.is_file():
                target.unlink()
            elif target.exists():
                shutil.rmtree(target)
            if a.symlink:
                target.symlink_to(src, target_is_directory=True)
            else:
                shutil.copytree(src, target)
            done.append(name)
        except Exception as e:  # noqa: BLE001
            failed.append((name, str(e)))

    print(f"Installed {len(done)} skills into {dest}:")
    for d in done:
        print("  +", d)
    if failed:
        print("FAILED:")
        for n, e in failed:
            print("  -", n, e)
        if a.symlink:
            print("Tip: on Windows, symlinks need Developer Mode or admin. Re-run without --symlink to copy.")
    print("\nRestart Claude Code (or run /reload-plugins) to pick up the new skills.")


if __name__ == "__main__":
    main()
