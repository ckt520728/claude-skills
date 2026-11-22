"""Scan HTML / PPTX / panel files for confidential terms. Exit 1 on any hit.

python leak_scan.py terms.txt out/Deck.html out/Deck.pptx out/panels/*.html
terms.txt: one term per line (manuscript ID, cohort, journal, author surnames, result numbers such as 0.901,
"manuscript's", the private notebook URL, the case patient's real name). Lines starting with # are ignored.
Base64 data URIs are stripped before scanning so short numbers do not match inside images.
"""
import pathlib, re, sys, zipfile

terms = [t.strip() for t in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if t.strip() and not t.startswith("#")]

def texts(path):
    p = pathlib.Path(path)
    if p.suffix.lower() == ".pptx":
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.endswith((".xml", ".rels")):
                    yield f"{p.name}:{n}", z.read(n).decode("utf-8", "ignore")
    else:
        yield p.name, p.read_text(encoding="utf-8", errors="ignore")

bad = 0
for f in sys.argv[2:]:
    for where, t in texts(f):
        t = re.sub(r"data:[\w/+.-]+;base64,[A-Za-z0-9+/=]+", "", t)
        for term in terms:
            for m in re.finditer(re.escape(term), t):
                bad += 1
                print(f"HIT {term!r} in {where}: ...{t[max(0, m.start()-50):m.end()+50]!r}...")
print("leak scan:", "CLEAN" if not bad else f"{bad} hits")
sys.exit(1 if bad else 0)
