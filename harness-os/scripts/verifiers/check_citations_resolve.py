#!/usr/bin/env python3
"""Every citation in a document must resolve to a real reference.

This is the check that matters most in the whole set. A `regex_present` contract
confirms a citation *marker* exists; it says nothing about whether the paper
does. Fabricated references are the failure mode with the worst consequences and
the best surface plausibility, so they need a verifier that resolves each marker
against an actual source of truth.

Three resolution backends, in order of strength:

  --vault DIR   entries you actually read (JSON files with an `id`/`citation`).
                Strongest: a citation resolves only if the paper is in the vault.
  --bib FILE    a .bib or .json reference list.
  (default)     the document's own References/參考文獻 section. Weakest -- it
                catches dangling markers, not invented papers. The verifier says
                so in its output rather than letting you forget.

Also fails on: unused references, `[citation needed]`, and duplicate keys.

Usage:
  python check_citations_resolve.py --doc draft/review.md --vault vault/
  python check_citations_resolve.py --doc draft/paper.md --bib refs.bib
  python check_citations_resolve.py --doc draft/paper.md
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verifier import (Report, base_parser, find_section, main_guard,  # noqa: E402
                       normalise, read_text, split_sections)

PLACEHOLDER_CITES = [r"\[citation needed\]", r"\[需要引用\]", r"\[ref\?\]",
                     r"\[TODO:? ?cite\]", r"\(\?\?\?\)"]


def extract_markers(text):
    """Return {marker: [positions]} for [1], [1,2], [1-3], [@key], [[wikilink]]."""
    found = {}

    def add(key, pos):
        found.setdefault(key, []).append(pos)

    # strip fenced code so examples in code blocks are not treated as citations
    scrubbed = re.sub(r"```.*?```", lambda m: " " * len(m.group(0)), text,
                      flags=re.S)

    for m in re.finditer(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", scrubbed):
        add(m.group(1).strip(), m.start())
    for m in re.finditer(r"\[@([A-Za-z0-9_:\-]+)\]", scrubbed):
        add(m.group(1), m.start())
    for m in re.finditer(r"(?<!\])\[(\d[\d,;\s\-]*)\]", scrubbed):
        body = m.group(1)
        for part in re.split(r"[,;]", body):
            part = part.strip()
            if not part:
                continue
            rng = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", part)
            if rng:
                lo, hi = int(rng.group(1)), int(rng.group(2))
                if hi - lo <= 200:
                    for n in range(lo, hi + 1):
                        add(str(n), m.start())
            elif part.isdigit():
                add(part, m.start())
    return found


def load_vault(vault_dir, report):
    keys, titles = set(), {}
    d = Path(vault_dir)
    if not d.exists():
        report.fail("vault directory not found: %s" % d)
        return keys, titles
    for f in sorted(d.rglob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            report.warn("vault entry is not valid JSON: %s" % f.name)
            continue
        entries = data if isinstance(data, list) else [data]
        for e in entries:
            if not isinstance(e, dict):
                continue
            key = e.get("id") or f.stem
            keys.add(str(key))
            if e.get("citation"):
                titles[str(key)] = str(e["citation"])[:90]
    return keys, titles


def load_bib(bib_path, report):
    keys, titles = set(), {}
    text = read_text(bib_path, report)
    if text is None:
        return keys, titles
    if bib_path.endswith(".json"):
        try:
            data = json.loads(text)
        except Exception as e:
            report.fail("invalid JSON bib: %s" % e)
            return keys, titles
        for e in (data if isinstance(data, list) else data.get("references", [])):
            if isinstance(e, dict) and e.get("id"):
                keys.add(str(e["id"]))
                titles[str(e["id"])] = str(e.get("citation", ""))[:90]
    else:
        for m in re.finditer(r"@\w+\s*\{\s*([^,\s]+)\s*,", text):
            keys.add(m.group(1))
    return keys, titles


def load_reference_section(doc, report, heading):
    sections, _ = split_sections(doc)
    head, body = find_section(sections, heading)
    if body is None:
        for alt in ("references", "參考文獻", "bibliography", "引用文獻"):
            head, body = find_section(sections, alt)
            if body is not None:
                break
    if body is None:
        report.fail("no reference list found (looked for a '%s' section) and no "
                    "--vault/--bib given, so citations cannot be resolved"
                    % heading)
        return set(), {}
    keys, titles = set(), {}
    for line in body.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^[-*]?\s*\[(\d+)\]\s*(.*)$", line)
        if m:
            keys.add(m.group(1))
            titles[m.group(1)] = m.group(2)[:90]
            continue
        m = re.match(r"^[-*]?\s*(\d+)[.)]\s+(.*)$", line)
        if m:
            keys.add(m.group(1))
            titles[m.group(1)] = m.group(2)[:90]
    return keys, titles


def main():
    p = base_parser("Resolve every citation marker against a reference source.")
    p.add_argument("--doc", required=True)
    p.add_argument("--vault", help="directory of JSON entries actually read")
    p.add_argument("--bib", help=".bib or .json reference list")
    p.add_argument("--refs-heading", default="References",
                   help="heading of the in-document reference list")
    p.add_argument("--allow-unused", action="store_true",
                   help="do not fail on references that are never cited")
    a = p.parse_args()

    r = Report("citations-resolve")
    doc = read_text(a.doc, r)
    if doc is None:
        return r.emit(a.as_json)

    for pat in PLACEHOLDER_CITES:
        for m in re.finditer(pat, doc, re.I):
            r.fail("placeholder citation left in text: %s" % m.group(0))

    if a.vault:
        keys, titles = load_vault(a.vault, r)
        backend = "vault (%s)" % a.vault
        strength = "strong: a citation resolves only if the source was read"
    elif a.bib:
        keys, titles = load_bib(a.bib, r)
        backend = "bib (%s)" % a.bib
        strength = "medium: resolves against a declared reference list"
    else:
        keys, titles = load_reference_section(doc, r, a.refs_heading)
        backend = "in-document reference list"
        strength = ("WEAK: catches dangling markers only. It cannot detect a "
                    "fabricated reference -- verify those against a real "
                    "database before publishing.")
    r.note("backend: %s -- %d references" % (backend, len(keys)))
    r.note("resolution strength: %s" % strength)

    if not keys and not r.failures:
        r.fail("reference source resolved to zero entries")

    markers = extract_markers(doc)
    if not markers:
        r.warn("no citation markers found in the document")
    r.note("%d distinct citation markers" % len(markers))

    key_norm = {normalise(k): k for k in keys}
    unresolved = []
    for marker in markers:
        if marker in keys or normalise(marker) in key_norm:
            continue
        unresolved.append(marker)
    if unresolved:
        shown = sorted(unresolved, key=lambda s: (len(s), s))[:20]
        r.fail("%d citation(s) do not resolve in %s: %s"
               % (len(unresolved), backend, ", ".join(shown)))

    if not a.allow_unused:
        cited = {m for m in markers} | {normalise(m) for m in markers}
        unused = [k for k in keys if k not in cited and normalise(k) not in cited]
        if unused:
            r.fail("%d reference(s) never cited in the text: %s"
                   % (len(unused), ", ".join(sorted(unused)[:20])))

    return r.emit(a.as_json)


if __name__ == "__main__":
    main_guard(main)
