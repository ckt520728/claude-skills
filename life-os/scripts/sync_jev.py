"""Vendor the jev-engineering skill's runnable layer into lifeos/jev/, verbatim.

Life OS *uses* the skill; it does not reimplement it. The skill lives on another drive
(D:\2026 JEV Engineering), and lifeos/ runs from Google Drive on any machine, so the package
is copied rather than path-imported. A copy can drift, so every file is hashed into
lifeos/JEV_VENDOR.json and scripts/checks.sh fails if the vendored tree no longer matches
its manifest -- i.e. if anyone hand-edits the vendored copy instead of fixing the skill.

Usage:
    python scripts/sync_jev.py            # copy + rewrite the manifest
    python scripts/sync_jev.py --check    # verify only; exit 1 on drift
"""
import hashlib
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.environ.get(
    "JEV_SKILL_DIR", r"D:\2026 JEV Engineering\skills\jev-engineering")
SRC = os.path.join(SKILL, "assets", "jev")
DST = os.path.join(ROOT, "lifeos", "jev")
MANIFEST = os.path.join(ROOT, "lifeos", "JEV_VENDOR.json")
KEEP = (".py", ".json")


def _files(base):
    out = []
    for d, dirs, names in os.walk(base):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        for n in names:
            if n.endswith(KEEP):
                out.append(os.path.relpath(os.path.join(d, n), base).replace(os.sep, "/"))
    return sorted(out)


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _version(base):
    with open(os.path.join(base, "__init__.py"), encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip("\"'")
    return "unknown"


def check():
    if not os.path.exists(MANIFEST):
        print("FAIL: no manifest at %s" % MANIFEST)
        return 1
    with open(MANIFEST, encoding="utf-8") as fh:
        man = json.load(fh)
    bad = []
    have = set(_files(DST))
    for rel, digest in man["files"].items():
        p = os.path.join(DST, rel)
        if rel not in have or _sha(p) != digest:
            bad.append(rel)
    extra = have - set(man["files"])
    for rel in bad:
        print("DRIFT: lifeos/jev/%s differs from the manifest" % rel)
    for rel in sorted(extra):
        print("DRIFT: lifeos/jev/%s is not in the manifest" % rel)
    if os.path.isdir(SRC):
        upstream = {r: _sha(os.path.join(SRC, r)) for r in _files(SRC)}
        stale = sorted(r for r in set(upstream) | set(man["files"])
                       if upstream.get(r) != man["files"].get(r))
        if stale:
            print("NOTE: skill has moved on since the last sync (%d files); run "
                  "python scripts/sync_jev.py" % len(stale))
    print("jev %s vendored, %d files, %s" % (
        man["version"], len(man["files"]), "clean" if not (bad or extra) else "DRIFTED"))
    return 1 if (bad or extra) else 0


def sync():
    if not os.path.isdir(SRC):
        print("FAIL: skill not found at %s (set JEV_SKILL_DIR)" % SRC)
        return 1
    if os.path.isdir(DST):
        shutil.rmtree(DST)
    files = _files(SRC)
    for rel in files:
        dst = os.path.join(DST, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(SRC, rel), dst)
    man = {
        "source": SKILL,
        "version": _version(SRC),
        "note": "Verbatim copy. Fix bugs in the skill, then re-sync; never edit here.",
        "files": {r: _sha(os.path.join(DST, r)) for r in files},
    }
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(man, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print("synced jev %s: %d files -> lifeos/jev/" % (man["version"], len(files)))
    return 0


if __name__ == "__main__":
    sys.exit(check() if "--check" in sys.argv else sync())
