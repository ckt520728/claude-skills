#!/usr/bin/env python3
"""Terminology consistency against a declared glossary.

Sections drafted in parallel drift in vocabulary: 認知功能 in section 2,
認知能力 in section 4, "cognitive performance" in the abstract. Reviewers read
that as sloppiness; readers read it as three different concepts.

Glossary format (JSON):

    {
      "terms": [
        {"canonical": "心率變異性 (HRV)",
         "variants": ["心率變異度", "心跳變異性", "HRV 指標"],
         "must_define": true},
        {"canonical": "Stroop task", "variants": ["Stroop test", "史楚普測驗"]}
      ]
    }

Checks:
  1. VARIANT USE (fail) -- a declared variant appears; use the canonical form.
  2. UNUSED TERM (warning) -- a glossary term never appears. Either the glossary
     is stale or a section is missing.
  3. UNDEFINED (fail) -- a `must_define` term is used but never defined, where
     "defined" means it appears in a definition section or with a parenthetical.

Usage:
  python check_glossary.py --doc draft/paper.md --glossary draft/glossary.json
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verifier import (Report, base_parser, main_guard, read_json,  # noqa: E402
                       read_text)


def occurrences(text, term):
    """Count occurrences. Word boundaries for ASCII terms; plain substring for
    CJK, which has no spaces to anchor a boundary on."""
    if re.search(r"[一-鿿]", term):
        return [m.start() for m in re.finditer(re.escape(term), text)]
    return [m.start() for m in
            re.finditer(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(term),
                        text, re.I)]


def main():
    p = base_parser("Check terminology consistency against a glossary.")
    p.add_argument("--doc", required=True)
    p.add_argument("--glossary", required=True)
    p.add_argument("--max-report", type=int, default=12)
    a = p.parse_args()

    r = Report("glossary")
    doc = read_text(a.doc, r)
    gl = read_json(a.glossary, r)
    if doc is None or gl is None:
        return r.emit(a.as_json)

    terms = gl.get("terms", gl if isinstance(gl, list) else [])
    if not terms:
        r.fail("glossary has no 'terms'")
        return r.emit(a.as_json)
    r.note("%d glossary terms" % len(terms))

    # Ignore fenced code -- variable names are not terminology drift.
    scrubbed = re.sub(r"```.*?```", " ", doc, flags=re.S)

    violations = 0
    for entry in terms:
        if isinstance(entry, str):
            entry = {"canonical": entry, "variants": []}
        canonical = entry.get("canonical")
        if not canonical:
            continue
        variants = entry.get("variants", []) or []

        canon_hits = occurrences(scrubbed, canonical)
        # A variant that is a substring of the canonical form (e.g. "HRV" inside
        # "心率變異性 (HRV)") would match spuriously; subtract those positions.
        canon_spans = [(s, s + len(canonical)) for s in canon_hits]

        for v in variants:
            hits = [s for s in occurrences(scrubbed, v)
                    if not any(a0 <= s < b0 for a0, b0 in canon_spans)]
            if hits:
                violations += 1
                if violations <= a.max_report:
                    r.fail("variant '%s' used %d time(s); canonical form is "
                           "'%s'" % (v, len(hits), canonical))

        if not canon_hits and not any(occurrences(scrubbed, v) for v in variants):
            r.warn("glossary term '%s' never appears in the document"
                   % canonical)

        if entry.get("must_define") and canon_hits:
            core = re.sub(r"\s*[（(].*?[)）]\s*", "", canonical).strip()
            defined = bool(
                re.search(r"%s\s*[（(]" % re.escape(core), scrubbed)
                or re.search(r"[（(]\s*%s\s*[)）]" % re.escape(core), scrubbed)
                or re.search(r"%s\s*(?:是|指|定義為|means|is defined as|refers to)"
                             % re.escape(core), scrubbed, re.I))
            if not defined:
                r.fail("term '%s' is marked must_define but is never defined "
                       "(no parenthetical gloss or definitional phrase)"
                       % canonical)

    if violations > a.max_report:
        r.fail("... and %d further variant use(s) not listed"
               % (violations - a.max_report))
    if not violations:
        r.note("no variant terminology found")

    return r.emit(a.as_json)


if __name__ == "__main__":
    main_guard(main)
