#!/usr/bin/env python3
"""Budget <-> methods alignment for a research proposal.

The most common reviewer-visible defect in a grant application is arithmetic or
consistency, not argument: a total that does not add up, or equipment costed but
never justified in the methods. Both are fully mechanical, so mechanise them.

Three checks:

  1. ARITHMETIC (hard fail) -- every category subtotal is the sum of its items,
     and `total` is the sum of the categories.
  2. JUSTIFICATION (hard fail) -- every equipment line item is mentioned by name
     somewhere in the methods section. Costing something you never justify is
     the failure reviewers actually flag.
  3. COVERAGE (warning) -- instrument-shaped phrases in the methods that never
     appear in the budget. Heuristic, so it warns rather than fails.

Usage:
  python check_budget_alignment.py --doc draft/proposal.md --budget draft/budget.json
  python check_budget_alignment.py --doc d.md --budget b.json --methods 研究方法
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verifier import (Report, base_parser, find_section, main_guard,  # noqa: E402
                       normalise, read_json, read_text, split_sections)

# Phrases that look like a named instrument. Deliberately loose -- this feeds a
# warning, never a failure.
INSTRUMENT_HINTS = [
    r"[A-Z][A-Za-z0-9\-]{2,}\s+(?:system|analyzer|analyser|recorder|scanner|amplifier|spectrometer|microscope)",
    r"[一-鿿]{2,8}(?:儀|系統|分析儀|記錄器|掃描儀|放大器|顯微鏡)",
    r"\b[A-Z]{2,}[- ]?\d{2,}\b",           # model numbers: EEG-64, BP-100
]


def money(v):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        cleaned = re.sub(r"[^\d.\-]", "", v)
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def collect_items(node):
    """Return [(name, amount)] from a category that is a list of items or a
    flat name->amount mapping."""
    items = []
    if isinstance(node, list):
        for entry in node:
            if isinstance(entry, dict):
                name = entry.get("name") or entry.get("item") or entry.get("項目")
                amt = money(entry.get("amount", entry.get("cost",
                                                          entry.get("金額"))))
                items.append((name, amt))
            else:
                items.append((str(entry), None))
    elif isinstance(node, dict):
        for k, v in node.items():
            if k in ("subtotal", "小計", "total"):
                continue
            items.append((k, money(v)))
    return items


def main():
    p = base_parser("Check budget arithmetic and methods alignment.")
    p.add_argument("--doc", required=True, help="proposal markdown")
    p.add_argument("--budget", required=True, help="budget json")
    p.add_argument("--methods", default="研究方法",
                   help="methods section heading (substring match)")
    p.add_argument("--equipment-key", default="equipment",
                   help="budget key holding equipment line items")
    p.add_argument("--tolerance", type=float, default=1.0,
                   help="rounding tolerance for sums")
    a = p.parse_args()

    r = Report("budget-alignment")
    doc = read_text(a.doc, r)
    budget = read_json(a.budget, r)
    if doc is None or budget is None:
        return r.emit(a.as_json)

    # ---- 1. arithmetic -------------------------------------------------
    declared_total = money(budget.get("total", budget.get("總計")))
    if declared_total is None:
        r.fail("budget has no numeric 'total'")

    category_sums = {}
    for key, node in budget.items():
        if key in ("total", "總計") or not isinstance(node, (list, dict)):
            continue
        items = collect_items(node)
        amounts = [amt for _, amt in items if amt is not None]
        if not amounts:
            continue
        s = sum(amounts)
        category_sums[key] = s
        if isinstance(node, dict):
            sub = money(node.get("subtotal", node.get("小計")))
            if sub is not None and abs(sub - s) > a.tolerance:
                r.fail("category '%s' subtotal %s != sum of items %s"
                       % (key, sub, s))

    if category_sums and declared_total is not None:
        grand = sum(category_sums.values())
        if abs(grand - declared_total) > a.tolerance:
            r.fail("total %s != sum of categories %s (%s)"
                   % (declared_total, grand,
                      ", ".join("%s=%s" % kv for kv in
                                sorted(category_sums.items()))))
        else:
            r.note("arithmetic OK: %d categories sum to %s"
                   % (len(category_sums), declared_total))

    # ---- 2. justification ---------------------------------------------
    sections, _ = split_sections(doc)
    head, methods = find_section(sections, a.methods)
    if methods is None:
        r.fail("methods section matching '%s' not found; headings present: %s"
               % (a.methods, ", ".join(h for h in sections if h) or "(none)"))
        return r.emit(a.as_json)
    r.note("methods section: '%s' (%d chars)" % (head, len(methods)))

    methods_norm = normalise(methods)
    equipment = collect_items(budget.get(a.equipment_key, []))
    if not equipment:
        r.warn("no equipment line items under '%s' -- nothing to justify"
               % a.equipment_key)

    unjustified = []
    for name, _ in equipment:
        if not name:
            continue
        if normalise(name) not in methods_norm:
            unjustified.append(name)
    if unjustified:
        r.fail("costed but not justified in methods: %s"
               % "; ".join(unjustified))
    elif equipment:
        r.note("all %d equipment items are named in methods" % len(equipment))

    # ---- 3. coverage (warning only) ------------------------------------
    budget_blob = normalise(" ".join(
        str(n) for cat in budget.values() if isinstance(cat, (list, dict))
        for n, _ in collect_items(cat) if n))
    seen = set()
    for pattern in INSTRUMENT_HINTS:
        for m in re.finditer(pattern, methods):
            phrase = m.group(0).strip()
            if len(phrase) < 3 or phrase.lower() in seen:
                continue
            seen.add(phrase.lower())
            if normalise(phrase) not in budget_blob:
                r.warn("methods mentions '%s' but no budget line matches it"
                       % phrase)

    return r.emit(a.as_json)


if __name__ == "__main__":
    main_guard(main)
