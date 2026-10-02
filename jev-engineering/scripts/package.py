"""建立可安裝的 skill/plugin ZIP；排除 cache 與工作區專用的 CLAUDE.md。"""
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]


def source_files():
    for folder in ("skills/jev-engineering", "agents"):
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                yield path
    for name in (".claude-plugin/plugin.json", "README.md", "UNKNOWNS.md"):
        yield ROOT / name


def main():
    manifest = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    artifacts = {}
    for kind in ("plugin.zip", "skill"):
        target = dist / f"jev-engineering-{version}.{kind}"
        with ZipFile(target, "w", ZIP_DEFLATED) as archive:
            for path in source_files():
                relative = path.relative_to(ROOT)
                if kind == "skill":
                    if relative.parts[0] != "skills":
                        continue
                    relative = relative.relative_to("skills")
                archive.writestr(relative.as_posix(), path.read_bytes())
        with ZipFile(target) as archive:
            assert archive.testzip() is None
            for name in archive.namelist():
                source = ROOT / ("skills" if kind == "skill" else "") / name
                assert archive.read(name) == source.read_bytes(), name
        artifacts[target.name] = hashlib.sha256(target.read_bytes()).hexdigest()
    (dist / "SHA256.json").write_text(json.dumps(artifacts, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifacts, indent=2))


if __name__ == "__main__":
    main()
