"""Assemble a revised deck template from a v1 template plus new slide fragments.

Usage (adapt the CONFIG block, then):  python assemble_from_template.py
- v1 template: sections preceded by  <!-- ============ N TITLE -->  and a single <script> block at the end.
- new_slides.html: each fragment preceded by  <!--@key-->  ; a  <!--@js-->  fragment is appended to the script.
- JS init is keyed by data-key (INIT.key=...), never by slide number.
The v1 file is only read, never written.
"""
import pathlib, re, sys

# ---------------- CONFIG ----------------
B = pathlib.Path(__file__).resolve().parent
V1 = B.parent.parent / "<v1 folder>" / "build" / "deck_template.html"
NEW = B / "new_slides.html"
OUT = B / "deck_template.html"
ORDER = ["cover", 3, 4, "concept", 8, 9, "cta"]          # new keys (str) and kept v1 numbers (int)
HEAD_EDITS = [("CONFIDENTIAL", "LAB SEMINAR · UNPUBLISHED WORK · PLEASE DO NOT REDISTRIBUTE")]
SLIDE_EDITS = {3: [('data-title="Hook"', 'data-key="hook" data-title="Hook"')]}
SCRIPT_EDITS = [("INIT[3]=", "INIT.hook="), ("const k=cur+1;", "const k=slides[cur].dataset.key;")]
LEAK_TERMS = ["<manuscript ID>", "<cohort>", "<author surname>", "manuscript's"]
# ----------------------------------------

def sub(text, pairs):
    """Replace each (old, new); fail loudly if old is missing (silent no-ops are how leaks survive)."""
    for a, b in pairs:
        assert a in text, f"missing: {a[:70]!r}"
        text = text.replace(a, b)
    return text

v1 = V1.read_text(encoding="utf-8")
first = re.search(r"<!-- =+ 1 ", v1).start()
head, rest = v1[:first], v1[first:]
body, script = rest.split("<script>", 1)
slides = {int(m.group(1)): m.group(0) for m in re.finditer(r"<!-- =+ (\d+) .*?</section>\s*", body, re.S)}
new = dict(re.findall(r"<!--@(\w+)-->\n(.*?)(?=<!--@|\Z)", NEW.read_text(encoding="utf-8"), re.S))

head = sub(head, HEAD_EDITS)
for n, pairs in SLIDE_EDITS.items():
    slides[n] = sub(slides[n], pairs)

missing = [k for k in ORDER if (k not in new if isinstance(k, str) else k not in slides)]
assert not missing, f"unknown slides in ORDER: {missing}"
deck = "".join(new[k] if isinstance(k, str) else slides[k] for k in ORDER)
deck = deck.replace('<section class="slide active"', '<section class="slide"').replace('<section class="slide"', '<section class="slide active"', 1)

script = sub(script, SCRIPT_EDITS)
left = re.findall(r"INIT\[\d+\]", script)
assert not left, f"position-keyed init left: {left}"
if "js" in new:
    script = new["js"] + "\n" + script

out = head + deck + "\n<script>" + script
OUT.write_text(out, encoding="utf-8")
print("slides:", len(re.findall(r'<section class="slide', out)), "expected:", len(ORDER))
hits = [t for t in LEAK_TERMS if t in out]
if hits:
    sys.exit(f"LEAK: {hits}")
