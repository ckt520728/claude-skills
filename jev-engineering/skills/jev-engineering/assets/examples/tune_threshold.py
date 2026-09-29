#!/usr/bin/env python3
"""Threshold sweep with a source-aware split and a written-down selection rule.

Everything else in this skill depends on doing this properly, because thresholds
do not transfer -- not between tasks, not between fallback models, not from a
paper to your workload.

Input: JSONL, one labelled item per line.

    {"id": "1", "source": "thread-9", "truth": "bug",
     "pred": "bug", "confidence": 0.97, "probabilities": {"bug": 0.97, "feature": 0.03},
     "fallback_pred": "bug"}

`source` groups near-duplicates (same thread, same document, same question asked
twice) so they cannot straddle the split and leak. `fallback_pred` is what the
expensive path said; without it the cascade column is unavailable and you can
only sweep coverage.

    python examples/tune_threshold.py labelled.jsonl
    python examples/tune_threshold.py labelled.jsonl --tolerance 2.0 --fee-ratio 290
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

GRID = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99, 1.0]


def load(path: Path) -> list[dict[str, Any]]:
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            items.append(json.loads(line))
    for i, it in enumerate(items):
        if it.get("confidence") is None:
            probs = it.get("probabilities") or {}
            if not probs:
                raise SystemExit(f"item {i}: needs `confidence` or `probabilities`")
            it["confidence"] = max(probs.values())     # q = max_k p_k
    return items


def split_by_source(items: Sequence[dict], selection_share: float = 0.40):
    """40/60 selection/test, split by SOURCE so near-duplicates stay together.

    Hashing the source id makes the split deterministic and reproducible, which
    matters because a split you cannot recreate is a split you cannot defend.
    """
    selection, test = [], []
    for it in items:
        source = str(it.get("source") or it.get("id"))
        h = int(hashlib.sha256(source.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        (selection if h < selection_share else test).append(it)
    return selection, test


def sweep(items: Sequence[dict], *, fee_ratio: float) -> list[dict[str, Any]]:
    """Cascade accuracy, coverage and fee at each tau.

    fee_ratio: how many times more expensive the fallback is per judgment.
    """
    n = len(items)
    if not n:
        return []
    has_fallback = all("fallback_pred" in it for it in items)
    fallback_acc = (
        sum(it["fallback_pred"] == it["truth"] for it in items) / n if has_fallback else None
    )
    cheap_acc = sum(it["pred"] == it["truth"] for it in items) / n

    rows = []
    for tau in GRID:
        accepted = [it for it in items if it["confidence"] >= tau]
        escalated = [it for it in items if it["confidence"] < tau]

        correct = sum(it["pred"] == it["truth"] for it in accepted)
        if has_fallback:
            correct += sum(it["fallback_pred"] == it["truth"] for it in escalated)
        else:
            correct += sum(it["pred"] == it["truth"] for it in escalated)

        # Fee of the cascade relative to running the fallback on everything.
        fee = (n * 1.0 + len(escalated) * fee_ratio) / (n * fee_ratio) if fee_ratio else 0.0

        rows.append({
            "tau": tau,
            "coverage": len(accepted) / n,
            "escalated": len(escalated) / n,
            "accuracy": correct / n,
            "accepted_accuracy": correct_share(accepted),
            "fee_ratio_vs_fallback": fee,
            "retained": (correct / n) / fallback_acc if fallback_acc else None,
        })

    for row in rows:
        row["cheap_only_accuracy"] = cheap_acc
        row["fallback_accuracy"] = fallback_acc
    return rows


def correct_share(items: Sequence[dict]) -> float | None:
    if not items:
        return None
    return sum(it["pred"] == it["truth"] for it in items) / len(items)


def baselines(items: Sequence[dict], tau: float) -> dict[str, float | None]:
    """Random escalation at the same budget, and the label-aware oracle.

    A sweep with no baseline always looks good. If the gate sits closer to
    random than to the oracle, the problem is the signal on your workload, not
    the threshold.
    """
    n = len(items)
    if not n or not all("fallback_pred" in it for it in items):
        return {"random": None, "oracle": None, "auroc": auroc(items)}

    share = sum(1 for it in items if it["confidence"] < tau) / n
    cheap_correct = [it["pred"] == it["truth"] for it in items]
    fb_correct = [it["fallback_pred"] == it["truth"] for it in items]

    # Random: expected accuracy when the same fraction is escalated at random.
    random_acc = sum(
        share * fb + (1 - share) * ch for ch, fb in zip(cheap_correct, fb_correct)
    ) / n

    # Oracle: escalate the cheap layer's errors first.
    budget = round(share * n)
    order = sorted(range(n), key=lambda i: cheap_correct[i])  # wrong ones first
    escalate = set(order[:budget])
    oracle_acc = sum(
        (fb_correct[i] if i in escalate else cheap_correct[i]) for i in range(n)
    ) / n

    return {"random": random_acc, "oracle": oracle_acc, "auroc": auroc(items)}


def auroc(items: Sequence[dict]) -> float | None:
    """AUROC of (1 - confidence) against being wrong: does confidence find errors?

    Around 0.85 the gate works. Near 0.50 confidence carries no information for
    this task and no threshold will help -- stop tuning, fix the state or the
    criteria.
    """
    wrong = [1 - it["confidence"] for it in items if it["pred"] != it["truth"]]
    right = [1 - it["confidence"] for it in items if it["pred"] == it["truth"]]
    if not wrong or not right:
        return None
    wins = sum((w > r) + 0.5 * (w == r) for w in wrong for r in right)
    return wins / (len(wrong) * len(right))


def pick(rows: Sequence[dict], *, tolerance_points: float) -> dict | None:
    """The rule, written down BEFORE looking at the numbers:

    maximise coverage subject to cascade accuracy staying within `tolerance_points`
    of the fallback alone. Choosing a threshold after seeing which one wins is how
    a post-hoc number gets shipped as a validated one.
    """
    eligible = [
        r for r in rows
        if r["fallback_accuracy"] is None
        or r["accuracy"] * 100 >= r["fallback_accuracy"] * 100 - tolerance_points
    ]
    return max(eligible, key=lambda r: r["coverage"]) if eligible else None


def show(title: str, rows: Sequence[dict], n: int) -> None:
    print(f"\n{title}  (n={n})")
    print(f"{'tau':>5} {'coverage':>9} {'escal':>7} {'cascade acc':>12} {'retained':>9} {'fee vs fb':>10}")
    for r in rows:
        ret = f"{r['retained']*100:7.1f}%" if r["retained"] else "      --"
        print(f"{r['tau']:>5.2f} {r['coverage']*100:8.1f}% {r['escalated']*100:6.1f}%"
              f" {r['accuracy']*100:11.1f}% {ret} {r['fee_ratio_vs_fallback']*100:9.1f}%")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("labelled", type=Path)
    ap.add_argument("--tolerance", type=float, default=2.0,
                    help="accuracy points the cascade may lose vs the fallback (default 2.0)")
    ap.add_argument("--fee-ratio", type=float, default=290.0,
                    help="fallback cost per judgment / cheap cost per judgment (default 290)")
    args = ap.parse_args()

    items = load(args.labelled)
    selection, test = split_by_source(items)
    print(f"{len(items)} items -> {len(selection)} selection / {len(test)} test, split by source")
    if len(selection) < 40:
        print("WARNING: selection set under 40 items. A threshold fitted here will not hold.")

    sel_rows = sweep(selection, fee_ratio=args.fee_ratio)
    show("SELECTION SET (fit tau here)", sel_rows, len(selection))

    chosen = pick(sel_rows, tolerance_points=args.tolerance)
    if not chosen:
        print(f"\nNo tau keeps accuracy within {args.tolerance} points of the fallback. "
              f"Fix the criteria text or the state before tuning further.")
        return 1

    tau = chosen["tau"]
    print(f"\nRule: maximise coverage subject to accuracy within {args.tolerance} points of the fallback.")
    print(f"Chosen tau = {tau:.2f}  (coverage {chosen['coverage']*100:.1f}%, "
          f"escalating {chosen['escalated']*100:.1f}%)")

    base = baselines(selection, tau)
    if base["random"] is not None:
        print(f"  baselines at the same budget: random {base['random']*100:.1f}%  "
              f"gate {chosen['accuracy']*100:.1f}%  oracle {base['oracle']*100:.1f}%")
    if base["auroc"] is not None:
        verdict = ("confidence carries no information here -- fix state/criteria, not tau"
                   if base["auroc"] < 0.60 else "usable")
        print(f"  error-detection AUROC {base['auroc']:.3f}  ({verdict})")

    test_rows = [r for r in sweep(test, fee_ratio=args.fee_ratio) if r["tau"] == tau]
    show("TEST SET (touched once, at the end)", test_rows, len(test))
    if test_rows and test_rows[0]["fallback_accuracy"]:
        lost = (test_rows[0]["fallback_accuracy"] - test_rows[0]["accuracy"]) * 100
        held = lost <= args.tolerance
        delta = (f"lost {lost:.2f} points to" if lost > 0
                 else f"beat, by {-lost:.2f} points,")
        print(f"\nHeld out: {delta} the fallback -- "
              f"{'HOLDS' if held else 'DOES NOT HOLD'} at tolerance {args.tolerance}.")
        if not held:
            print("Do not re-tune on the test set. Go back and label more data.")

    print(f"\nFreeze this: tau={tau:.2f}, model=<pin the exact version>, "
          f"date=<today>, label set={args.labelled}, rule=max coverage within "
          f"{args.tolerance} points. Re-tune when the model, criteria text, state "
          f"shape, traffic mix or fallback changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
