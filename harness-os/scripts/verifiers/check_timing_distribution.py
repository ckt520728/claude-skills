#!/usr/bin/env python3
"""Timing-quality checks for reaction-time data.

`check_no_null_rt.py` asks whether the data is there. This asks whether it is
*measurable* -- a full set of reaction times can still be scientifically
worthless if the clock was wrong.

Checks:
  1. CLOCK QUANTISATION (fail) -- if nearly every RT is a multiple of some
     granularity above 4ms, the app used a low-resolution clock (`Date.now()`,
     a setInterval tick, a rounded frame time) instead of `performance.now()`.
     Millisecond-level cognitive measures are meaningless at 15ms resolution,
     and nothing else in the pipeline will ever notice.
  2. ZERO VARIANCE (fail) -- identical or near-identical RTs mean a constant is
     being written, not a measurement.
  3. CONDITION COLLAPSE (fail, when --condition-col is given) -- a condition
     with fewer than --min-per-condition usable trials cannot be analysed.
  4. FIRST-TRIAL OUTLIER (warning) -- trial 1 far above the rest: asset loading
     or first-paint latency is being counted as response time.
  5. IMPLAUSIBLE SPEED (warning) -- a run of sub-200ms responses suggests
     button-mashing rather than task performance.

Usage:
  python check_timing_distribution.py --csv results/sim_run.csv
  python check_timing_distribution.py --csv r.csv --condition-col condition
"""

from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verifier import Report, base_parser, main_guard  # noqa: E402

NULLISH = {"", "null", "none", "nan", "na", "n/a", "undefined", "-"}


def gcd_granularity(values, candidates=(1, 2, 4, 5, 8, 10, 15, 16, 17, 20,
                                        25, 32, 33, 50, 100)):
    """Smallest granularity g > 4 such that ~all values are multiples of g."""
    best = None
    for g in candidates:
        if g <= 4:
            continue
        hits = sum(1 for v in values if abs(v - round(v / g) * g) < 0.5)
        if hits / float(len(values)) >= 0.95:
            best = g
            break
    return best


def main():
    p = base_parser("Check reaction-time distribution quality.")
    p.add_argument("--csv", required=True)
    p.add_argument("--rt-col", default="rt_ms")
    p.add_argument("--index-col", default="trial_index")
    p.add_argument("--condition-col")
    p.add_argument("--practice-col", default="is_practice")
    p.add_argument("--timeout-col", default="timed_out")
    p.add_argument("--min-per-condition", type=int, default=8)
    p.add_argument("--min-trials", type=int, default=10,
                   help="below this the distribution checks are not meaningful")
    p.add_argument("--fast-threshold", type=float, default=200.0)
    p.add_argument("--max-fast-rate", type=float, default=0.10)
    a = p.parse_args()

    r = Report("timing-distribution")
    path = Path(a.csv)
    if not path.exists():
        r.fail("data file not found: %s" % path)
        return r.emit(a.as_json)

    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    except Exception as e:
        r.fail("cannot parse CSV: %s" % e)
        return r.emit(a.as_json)
    if not rows:
        r.fail("no data rows")
        return r.emit(a.as_json)
    if a.rt_col not in rows[0]:
        r.fail("no '%s' column (present: %s)"
               % (a.rt_col, ", ".join(sorted(rows[0].keys()))))
        return r.emit(a.as_json)

    def truthy(v):
        return str(v).strip().lower() in ("1", "true", "yes", "y", "t")

    usable = []
    for row in rows:
        if a.practice_col in row and truthy(row.get(a.practice_col)):
            continue
        if a.timeout_col in row and truthy(row.get(a.timeout_col)):
            continue
        raw = (row.get(a.rt_col) or "").strip()
        if raw.lower() in NULLISH:
            continue
        try:
            rt = float(raw)
        except ValueError:
            continue
        if rt > 0:
            usable.append((row, rt))

    values = [v for _, v in usable]
    if len(values) < a.min_trials:
        r.fail("only %d usable reaction times (need >= %d) -- cannot assess "
               "timing quality" % (len(values), a.min_trials))
        return r.emit(a.as_json)

    r.note("%d usable RTs, median %.0fms, range %.0f-%.0fms"
           % (len(values), statistics.median(values), min(values), max(values)))

    # ---- 1. clock quantisation -----------------------------------------
    gran = gcd_granularity(values)
    if gran:
        r.fail("reaction times are quantised to ~%dms -- a low-resolution "
               "clock is in use (Date.now(), a timer tick, or a rounded frame "
               "time). Use performance.now(); at this resolution the timing "
               "data cannot support millisecond-level conclusions." % gran)
    else:
        r.note("no clock quantisation detected")

    # ---- 2. variance ----------------------------------------------------
    if len(set(values)) == 1:
        r.fail("every reaction time is identical (%.1fms) -- a constant is "
               "being written, not a measurement" % values[0])
    else:
        sd = statistics.pstdev(values)
        if sd < 1.0:
            r.fail("reaction-time standard deviation is %.2fms -- implausibly "
                   "low for human responses" % sd)
        else:
            r.note("SD %.0fms" % sd)

    # ---- 3. condition coverage -----------------------------------------
    if a.condition_col:
        if a.condition_col not in rows[0]:
            r.fail("no '%s' column" % a.condition_col)
        else:
            counts = {}
            for row, _ in usable:
                key = (row.get(a.condition_col) or "(blank)").strip()
                counts[key] = counts.get(key, 0) + 1
            thin = {k: n for k, n in counts.items()
                    if n < a.min_per_condition}
            if thin:
                r.fail("condition(s) with fewer than %d usable trials: %s"
                       % (a.min_per_condition,
                          ", ".join("%s=%d" % kv for kv in sorted(thin.items()))))
            else:
                r.note("conditions: %s"
                       % ", ".join("%s=%d" % kv for kv in sorted(counts.items())))

    # ---- 4. first-trial outlier (warning) -------------------------------
    if a.index_col in rows[0]:
        indexed = []
        for row, rt in usable:
            try:
                indexed.append((int(float(row.get(a.index_col))), rt))
            except (TypeError, ValueError):
                pass
        if len(indexed) > 5:
            indexed.sort()
            first_rt = indexed[0][1]
            rest = [v for _, v in indexed[1:]]
            med = statistics.median(rest)
            if med > 0 and first_rt > 2.0 * med:
                r.warn("first trial (%.0fms) is %.1fx the median of the rest "
                       "(%.0fms) -- asset loading or first paint is being "
                       "counted as response time; preload and discard or flag "
                       "trial 1" % (first_rt, first_rt / med, med))

    # ---- 5. implausible speed (warning) ---------------------------------
    fast = [v for v in values if v < a.fast_threshold]
    if fast:
        rate = len(fast) / float(len(values))
        if rate > a.max_fast_rate:
            r.warn("%.0f%% of responses are under %.0fms -- likely "
                   "button-mashing rather than task performance"
                   % (rate * 100, a.fast_threshold))
        else:
            r.note("%d response(s) under %.0fms (%.0f%%)"
                   % (len(fast), a.fast_threshold, rate * 100))

    return r.emit(a.as_json)


if __name__ == "__main__":
    main_guard(main)
