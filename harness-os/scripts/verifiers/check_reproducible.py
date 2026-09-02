#!/usr/bin/env python3
"""Provenance and reproducibility gate for an analysis result.

A metrics file without a seed, a dataset version and a code version is not a
result -- it is an anecdote. This verifier refuses to let one be published, and
where a previous run exists, checks that the same seed still produces the same
numbers.

Checks:
  1. PROVENANCE (fail) -- required keys present and non-null.
  2. SPLIT HYGIENE (fail) -- if subject lists are recorded, dev and holdout must
     be disjoint. Subject overlap is the leakage that makes a method look good
     and then fail to replicate.
  3. DETERMINISM (fail) -- with --baseline, identical seed must give identical
     metrics within tolerance.
  4. PRE-REGISTRATION (fail) -- with --thresholds, any decision threshold in the
     results must match the value recorded before the holdout run.
  5. PLAUSIBILITY (warning) -- a metric at exactly 1.0, or a CI of width zero.

Usage:
  python check_reproducible.py --results results/dev_metrics.json
  python check_reproducible.py --results r.json --baseline results/prev.json
  python check_reproducible.py --results r.json --thresholds preregistered.json
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verifier import Report, base_parser, main_guard, read_json  # noqa: E402

DEFAULT_REQUIRED = ["seed", "n_subjects", "metric", "dataset_version",
                    "code_version"]


def numeric_leaves(obj, prefix=""):
    """Flatten to {dotted.path: number} so two runs can be compared field-wise."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(numeric_leaves(v, "%s.%s" % (prefix, k) if prefix else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(numeric_leaves(v, "%s[%d]" % (prefix, i)))
    elif isinstance(obj, bool):
        pass
    elif isinstance(obj, (int, float)):
        out[prefix] = float(obj)
    return out


def main():
    p = base_parser("Check result provenance, split hygiene and determinism.")
    p.add_argument("--results", required=True)
    p.add_argument("--baseline", help="previous run to compare against")
    p.add_argument("--thresholds",
                   help="pre-registered decision thresholds (JSON)")
    p.add_argument("--require", default=",".join(DEFAULT_REQUIRED))
    p.add_argument("--tolerance", type=float, default=1e-9)
    a = p.parse_args()

    r = Report("reproducibility")
    res = read_json(a.results, r)
    if res is None:
        return r.emit(a.as_json)

    # ---- 1. provenance --------------------------------------------------
    required = [k.strip() for k in a.require.split(",") if k.strip()]
    missing = [k for k in required
               if k not in res or res[k] is None or res[k] == ""]
    if missing:
        r.fail("missing provenance field(s): %s -- a result without these "
               "cannot be reproduced" % ", ".join(missing))
    else:
        r.note("provenance complete (seed=%s, n=%s, dataset=%s)"
               % (res.get("seed"), res.get("n_subjects"),
                  res.get("dataset_version")))

    # ---- 2. split hygiene ----------------------------------------------
    dev = res.get("dev_subjects") or res.get("train_subjects")
    hold = res.get("holdout_subjects") or res.get("test_subjects")
    if dev and hold:
        overlap = sorted(set(map(str, dev)) & set(map(str, hold)))
        if overlap:
            r.fail("subject leakage: %d subject(s) in BOTH dev and holdout: %s"
                   % (len(overlap), ", ".join(overlap[:10])))
        else:
            r.note("splits disjoint (%d dev / %d holdout)" % (len(dev), len(hold)))
        n = res.get("n_subjects")
        if isinstance(n, int) and n != len(set(map(str, dev)) | set(map(str, hold))):
            r.warn("n_subjects=%s but split lists contain %d unique subjects"
                   % (n, len(set(map(str, dev)) | set(map(str, hold)))))
    else:
        r.warn("no subject split recorded -- leakage cannot be checked")

    # ---- 3. determinism -------------------------------------------------
    if a.baseline:
        base = read_json(a.baseline, r)
        if base is not None:
            if str(base.get("seed")) != str(res.get("seed")):
                r.note("baseline seed %s != current seed %s; determinism check "
                       "skipped" % (base.get("seed"), res.get("seed")))
            else:
                cur, old = numeric_leaves(res), numeric_leaves(base)
                drifted = []
                for k in sorted(set(cur) & set(old)):
                    if k.endswith(("seed", "timestamp", "elapsed", "duration")):
                        continue
                    if abs(cur[k] - old[k]) > a.tolerance:
                        drifted.append("%s: %s -> %s" % (k, old[k], cur[k]))
                if drifted:
                    r.fail("same seed produced different numbers -- the pipeline "
                           "is not deterministic: %s" % "; ".join(drifted[:8]))
                else:
                    r.note("deterministic: %d numeric fields identical at seed %s"
                           % (len(set(cur) & set(old)), res.get("seed")))

    # ---- 4. pre-registration -------------------------------------------
    if a.thresholds:
        pre = read_json(a.thresholds, r)
        if pre is not None:
            declared = pre.get("thresholds", pre)
            actual = res.get("thresholds", {})
            for k, v in (declared or {}).items():
                if k not in actual:
                    r.warn("pre-registered threshold '%s' not reported in "
                           "results" % k)
                elif actual[k] != v:
                    r.fail("threshold '%s' was pre-registered as %s but the "
                           "results use %s -- choosing a threshold after seeing "
                           "the data invalidates the holdout" % (k, v, actual[k]))
            if declared:
                r.note("%d pre-registered threshold(s) checked" % len(declared))

    # ---- 5. plausibility (warnings) -------------------------------------
    for k, v in numeric_leaves(res).items():
        if k.endswith(("accuracy", "auc", "f1", "precision", "recall",
                       "metric")) and v in (0.0, 1.0):
            r.warn("%s is exactly %s -- verify this is real and not a "
                   "degenerate split" % (k, v))
    lo, hi = res.get("ci_low"), res.get("ci_high")
    if isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
        if hi < lo:
            r.fail("ci_high (%s) < ci_low (%s)" % (hi, lo))
        elif hi == lo:
            r.warn("confidence interval has zero width")

    return r.emit(a.as_json)


if __name__ == "__main__":
    main_guard(main)
