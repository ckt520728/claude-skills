#!/usr/bin/env python3
"""Every source document must have a vault entry.

The silent skip is the worst failure in corpus work: a report covering 34 of 40
papers looks exactly like a report covering all 40, and nothing in the output
says otherwise. This verifier is the only thing standing between you and that.

Checks:
  1. COVERAGE (fail) -- every file in --sources has an entry in --vault.
  2. SCHEMA (fail) -- every entry has the required fields, non-empty.
  3. ORPHANS (warning) -- vault entries with no corresponding source file.
  4. THINNESS (warning) -- entries suspiciously short for a real summary.

Matching is by stem, case-insensitively, with punctuation normalised, so
`Lin_2026_Agentic Harness.pdf` matches `lin_2026_agentic_harness.json`.

Usage:
  python check_coverage.py --sources Reference/ --vault vault/
  python check_coverage.py --sources refs/ --vault vault/ --ext .pdf,.epub \
      --require id,citation,findings
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verifier import Report, base_parser, main_guard  # noqa: E402

DEFAULT_REQUIRED = ["id", "citation", "question", "method", "findings"]


def key_of(name):
    """Normalise a filename stem so source and vault names can be compared."""
    s = name.lower()
    s = re.sub(r"[\s_\-.,()\[\]]+", "", s)
    return s


def main():
    p = base_parser("Assert every source document has a vault entry.")
    p.add_argument("--sources", required=True, help="directory of source files")
    p.add_argument("--vault", required=True, help="directory of JSON entries")
    p.add_argument("--ext", default=".pdf",
                   help="comma-separated source extensions")
    p.add_argument("--require", default=",".join(DEFAULT_REQUIRED),
                   help="comma-separated required fields in each entry")
    p.add_argument("--min-chars", type=int, default=300,
                   help="warn if an entry's text content is shorter than this")
    p.add_argument("--allow-missing", default="",
                   help="comma-separated source stems that are known-excluded")
    a = p.parse_args()

    r = Report("corpus-coverage")
    src_dir, vault_dir = Path(a.sources), Path(a.vault)
    if not src_dir.exists():
        r.fail("sources directory not found: %s" % src_dir)
        return r.emit(a.as_json)
    if not vault_dir.exists():
        r.fail("vault directory not found: %s" % vault_dir)
        return r.emit(a.as_json)

    exts = {e.strip().lower() for e in a.ext.split(",") if e.strip()}
    sources = sorted(f for f in src_dir.rglob("*")
                     if f.is_file() and f.suffix.lower() in exts)
    if not sources:
        r.fail("no source files with extension(s) %s under %s"
               % (", ".join(sorted(exts)), src_dir))
        return r.emit(a.as_json)

    entries = {}
    for f in sorted(vault_dir.rglob("*.json")):
        if f.name.startswith("_") or f.name == "index.json":
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            r.fail("vault entry is not valid JSON: %s (%s)" % (f.name, e))
            continue
        for e in (data if isinstance(data, list) else [data]):
            if isinstance(e, dict):
                eid = str(e.get("id") or f.stem)
                if eid in entries:
                    # Silently overwriting means one paper's summary is lost and
                    # coverage still reads as complete -- exactly the invisible
                    # failure this verifier exists to catch.
                    r.fail("duplicate vault id '%s' in %s and %s -- one entry "
                           "is shadowing the other"
                           % (eid, entries[eid][0], f.name))
                entries[eid] = (f.name, e)

    r.note("%d source files, %d vault entries" % (len(sources), len(entries)))

    index = {}
    for eid, (fname, e) in entries.items():
        index[key_of(eid)] = (eid, e)
        index.setdefault(key_of(Path(fname).stem), (eid, e))
        src_hint = e.get("source_file") or e.get("source")
        if src_hint:
            index.setdefault(key_of(Path(str(src_hint)).stem), (eid, e))

    excluded = {key_of(s) for s in a.allow_missing.split(",") if s.strip()}
    required = [f.strip() for f in a.require.split(",") if f.strip()]

    missing, matched = [], {}
    for f in sources:
        k = key_of(f.stem)
        if k in excluded:
            r.note("excluded by --allow-missing: %s" % f.name)
            continue
        hit = index.get(k)
        if hit is None:
            hit = next((v for kk, v in index.items()
                        if kk and (kk in k or k in kk) and len(kk) > 12), None)
        if hit is None:
            missing.append(f.name)
        else:
            matched[hit[0]] = hit[1]

    if missing:
        r.fail("%d source(s) have no vault entry: %s"
               % (len(missing), "; ".join(missing[:15])))
    else:
        r.note("coverage complete: every source has an entry")

    for eid, e in sorted(matched.items()):
        empty = [f for f in required
                 if not e.get(f) or (isinstance(e.get(f), str)
                                     and not e[f].strip())]
        if empty:
            r.fail("entry '%s' missing/empty required field(s): %s"
                   % (eid, ", ".join(empty)))
        size = len(json.dumps(e, ensure_ascii=False))
        if size < a.min_chars:
            r.warn("entry '%s' is only %d chars -- likely a stub, not a summary"
                   % (eid, size))

    orphans = [eid for eid in entries if eid not in matched]
    if orphans:
        r.warn("%d vault entr(ies) match no source file: %s"
               % (len(orphans), ", ".join(sorted(orphans)[:10])))

    return r.emit(a.as_json)


if __name__ == "__main__":
    main_guard(main)
