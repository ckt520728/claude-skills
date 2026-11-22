"""Inline {{IMG:name}} (assets/name.jpg|png) as base64 and {{DATA:name}} (assets/name.json) into the deck.

python build_deck.py <deck folder> <output name.html>     (standard library only)
Edit build/deck_template.html, never the output.
"""
import base64, pathlib, re, sys

deck = pathlib.Path(sys.argv[1]).resolve()
name = sys.argv[2]
tpl = (deck / "build" / "deck_template.html").read_text(encoding="utf-8")

def img(m):
    for ext, mime in (("jpg", "jpeg"), ("png", "png")):
        p = deck / "assets" / f"{m.group(1)}.{ext}"
        if p.exists():
            return f"data:image/{mime};base64," + base64.b64encode(p.read_bytes()).decode()
    raise FileNotFoundError(m.group(1))

html = re.sub(r"\{\{IMG:(\w+)\}\}", img, tpl)
html = re.sub(r"\{\{DATA:(\w+)\}\}", lambda m: (deck / "assets" / f"{m.group(1)}.json").read_text(encoding="utf-8"), html)
assert "{{" not in html, "unreplaced placeholder"
out = deck / "output" / name
out.parent.mkdir(exist_ok=True)
out.write_text(html, encoding="utf-8")
n = len(re.findall(r'<section class="slide', html))
mb = out.stat().st_size / 1e6
print(f"{out.name}: {n} slides, {mb:.2f} MB")
assert mb < 16, "Artifact pages must be <= 16 MB"
