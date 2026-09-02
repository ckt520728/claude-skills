#!/usr/bin/env python3
"""Structural coherence for long-form drafts written section-by-section.

Drafting sections in parallel is what makes a long document tractable, and it
reliably breaks the same four things. All four are mechanical:

  1. DUPLICATE PARAGRAPHS (fail) -- near-identical text in two places, which is
     what happens when two section jobs both cover the background.
  2. UNDEFINED ABBREVIATIONS (fail) -- an acronym used before it is expanded.
  3. EMPTY SECTIONS (fail) -- a heading with no body, i.e. an outline that was
     never filled in. This is the truncation failure `no_placeholder` misses,
     because nothing was written at all.
  4. HEADING LEVEL SKIPS (warning) -- H2 followed by H4, usually a paste error.

Uses character k-gram Jaccard similarity, so it works on Chinese and English
alike -- word tokenisation would silently do nothing on CJK text.

Usage:
  python check_coherence.py --doc draft/paper.md
  python check_coherence.py --doc d.md --threshold 0.75 --min-paragraph 200
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verifier import (Report, base_parser, jaccard, main_guard,  # noqa: E402
                       paragraphs, read_text, shingles, split_sections)

# Acronyms that are universally understood or are not acronyms at all.
ABBREV_ALLOWLIST = {
    "AI", "API", "CPU", "GPU", "OS", "PDF", "HTML", "CSS", "JSON", "CSV", "URL",
    "HTTP", "HTTPS", "SQL", "UI", "UX", "ID", "IO", "RAM", "SSD", "USB", "TV",
    "DNA", "RNA", "MRI", "CT", "EEG", "ECG", "EKG", "HRV", "BMI", "WHO", "FDA",
    "USA", "UK", "EU", "PhD", "MD", "OK", "TODO", "NOTE", "IEEE", "APA", "ISO",
}


def find_abbrev_definitions(text):
    """Catch 'Heart Rate Variability (HRV)' and 'HRV (Heart Rate Variability)'."""
    defined = set()
    for m in re.finditer(r"\(([A-Z][A-Za-z0-9]{1,7})\)", text):
        defined.add(m.group(1))
    for m in re.finditer(r"\b([A-Z]{2,8})\s*[（(]\s*[A-Za-z一-鿿]", text):
        defined.add(m.group(1))
    return defined


def main():
    p = base_parser("Check structural coherence of a long-form draft.")
    p.add_argument("--doc", required=True)
    p.add_argument("--threshold", type=float, default=0.80,
                   help="Jaccard similarity above which two paragraphs are "
                        "treated as duplicates")
    p.add_argument("--min-paragraph", type=int, default=160,
                   help="ignore paragraphs shorter than this (headers, "
                        "captions and one-liners repeat legitimately)")
    p.add_argument("--min-section-chars", type=int, default=40,
                   help="a section shorter than this counts as empty")
    p.add_argument("--skip-abbrev", action="store_true",
                   help="disable the abbreviation check")
    a = p.parse_args()

    r = Report("coherence")
    doc = read_text(a.doc, r)
    if doc is None:
        return r.emit(a.as_json)

    sections, order = split_sections(doc)
    r.note("%d sections, %d chars" % (len([h for h in order if h]), len(doc)))

    # ---- 1. duplicate paragraphs ---------------------------------------
    indexed = []
    for head in order:
        for para in paragraphs(sections.get(head, "")):
            if para.startswith(("|", ">", "```", "-", "*")) or "|" in para[:40]:
                continue          # tables, quotes, code, lists repeat by design
            if len(para) >= a.min_paragraph:
                indexed.append((head or "(preamble)", para))

    dupes = []
    grams = [shingles(t) for _, t in indexed]
    for i in range(len(indexed)):
        for j in range(i + 1, len(indexed)):
            sim = jaccard(grams[i], grams[j])
            if sim >= a.threshold:
                dupes.append((sim, indexed[i][0], indexed[j][0],
                              indexed[i][1][:70]))
    for sim, s1, s2, snippet in sorted(dupes, reverse=True)[:12]:
        r.fail("near-duplicate paragraph (%.0f%%) in '%s' and '%s': \"%s...\""
               % (sim * 100, s1, s2, snippet.replace("\n", " ")))
    if not dupes:
        r.note("no duplicate paragraphs among %d candidates" % len(indexed))

    # ---- 2. undefined abbreviations ------------------------------------
    if not a.skip_abbrev:
        defined = find_abbrev_definitions(doc) | ABBREV_ALLOWLIST
        first_use = {}
        for m in re.finditer(r"\b([A-Z]{2,8})\b", doc):
            first_use.setdefault(m.group(1), m.start())
        undefined = []
        for abbr, pos in sorted(first_use.items(), key=lambda kv: kv[1]):
            if abbr in ABBREV_ALLOWLIST:
                continue
            defn = re.search(r"\(%s\)|%s\s*[（(]" % (re.escape(abbr),
                                                     re.escape(abbr)), doc)
            if defn is None or defn.start() > pos:
                undefined.append(abbr)
        if undefined:
            r.fail("abbreviation used before it is expanded: %s"
                   % ", ".join(undefined[:15]))
        else:
            r.note("all abbreviations expanded before first use")

    # ---- 3. empty sections ---------------------------------------------
    empty = [h for h in order
             if h and len(sections.get(h, "").strip()) < a.min_section_chars]
    if empty:
        r.fail("section heading with no content: %s" % "; ".join(empty))

    # ---- 4. heading level skips (warning) ------------------------------
    levels = [(len(m.group(1)), m.group(2).strip())
              for m in re.finditer(r"^(#{1,6})\s+(.*)$", doc, re.M)]
    for (l1, h1), (l2, h2) in zip(levels, levels[1:]):
        if l2 - l1 > 1:
            r.warn("heading level skips H%d -> H%d at '%s'" % (l1, l2, h2))

    return r.emit(a.as_json)


if __name__ == "__main__":
    main_guard(main)
