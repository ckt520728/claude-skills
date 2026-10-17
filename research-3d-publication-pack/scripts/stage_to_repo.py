"""
stage_to_repo.py -- Copy the deliverables from the working Output folder into a homepage repo
clone, rewriting cross-folder paths for the repo layout. Never pushes.

Output layout (working)          Repo layout (published)
  site/                    ->      <site_dir>/          (default hhsa-3d/)
  blog/<post>.html         ->      blog/<post>.html
  deck/<deck>.html         ->      slides/<slug>.html   (../site/ and ../paper/figures/ rewritten)
  deck/<deck>.pptx         ->      slides/<slug>.pptx
  paper/                   ->      NOT copied (pre-submission; public repo = preprint)

Also removes Google Drive desktop.ini files from .git (they break git with
"fatal: bad object refs/desktop.ini") and adds desktop.ini to .git/info/exclude.

Usage:
  python stage_to_repo.py <output_dir> <repo_dir> --site-dir hhsa-3d \
      --blog blog/my-post.html --deck deck/My_Deck.html --pptx deck/My_Deck.pptx --slug my-deck
"""

import argparse
import re
import shutil
from pathlib import Path

SKIP = {"desktop.ini", "start_local_server.bat", "Thumbs.db"}


def clean_git(repo):
    git = repo / ".git"
    n = 0
    for f in git.rglob("desktop.ini"):
        f.unlink()
        n += 1
    excl = git / "info" / "exclude"
    excl.parent.mkdir(parents=True, exist_ok=True)
    text = excl.read_text(encoding="utf-8") if excl.exists() else ""
    if "desktop.ini" not in text.split():
        excl.write_text(text.rstrip("\n") + "\ndesktop.ini\n", encoding="utf-8")
    return n


def copy_tree(src, dst):
    count = 0
    for f in src.rglob("*"):
        if f.is_file() and f.name not in SKIP:
            out = dst / f.relative_to(src)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, out)
            count += 1
    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output_dir")
    ap.add_argument("repo_dir")
    ap.add_argument("--site-dir", default="hhsa-3d")
    ap.add_argument("--blog", required=True, help="path under output_dir, e.g. blog/post.html")
    ap.add_argument("--deck", required=True, help="path under output_dir, e.g. deck/Deck.html")
    ap.add_argument("--pptx", required=True)
    ap.add_argument("--slug", required=True, help="published file stem in slides/")
    a = ap.parse_args()

    out, repo = Path(a.output_dir), Path(a.repo_dir)
    if not (repo / ".git").exists():
        raise SystemExit(f"{repo} is not a git clone")
    print("removed desktop.ini from .git:", clean_git(repo))
    print("site files:", copy_tree(out / "site", repo / a.site_dir))

    blog = out / a.blog
    (repo / "blog").mkdir(exist_ok=True)
    shutil.copy2(blog, repo / "blog" / blog.name)

    slides = repo / "slides"
    slides.mkdir(exist_ok=True)
    html = (out / a.deck).read_text(encoding="utf-8")
    html = (html.replace("../paper/figures/", f"../{a.site_dir}/assets/img/")
                .replace("../site/", f"../{a.site_dir}/"))
    # A fallback list such as ['../site/x', '../<site_dir>/x'] collapses to one URL after rewriting
    html = re.sub(r"(['\"])([^'\"]+)\1,\s*\1\2\1", r"\1\2\1", html)
    (slides / f"{a.slug}.html").write_text(html, encoding="utf-8")
    shutil.copy2(out / a.pptx, slides / f"{a.slug}.pptx")
    left = [s for s in ("../site/", "../paper/") if s in html]
    print("deck staged; unresolved working-layout paths:", left or "none")
    print("Next: git diff --stat, run the repo tests, audit + smoke test the clone, commit. "
          "Push / merge only with the user's go-ahead.")


if __name__ == "__main__":
    main()
