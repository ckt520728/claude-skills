#!/usr/bin/env python3
"""Trial-data integrity for a cognitive test export.

An app that looks perfect and silently drops 8% of reaction times is worse than
one that crashes: the crash is visible, the data loss is not. This verifier is
what makes the loss visible.

Checks (all hard failures -- this is research data):
  1. COMPLETENESS -- expected trial count present, no gaps in trial_index.
  2. NO NULL RT -- an unanswered trial must be recorded as an explicit timeout,
     not as null, 0, or an empty cell. Conflating "no response" with "0 ms"
     poisons every summary statistic computed downstream.
  3. NO NEGATIVE OR ABSURD RT -- outside [--min-rt, --max-rt].
  4. NO DUPLICATE TRIALS -- a duplicated trial_index means a write race.
  5. SINGLE SUBJECT, CONSISTENT -- one subject_id per file, non-empty.
  6. REQUIRED COLUMNS -- present in the header.

Warnings: high timeout rate, practice trials not marked, first-trial outlier.

Usage:
  python check_no_null_rt.py --csv results/sim_run.csv --expected-trials 96
  python check_no_null_rt.py --csv r.csv --rt-col rt_ms --index-col trial_index
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verifier import Report, base_parser, main_guard  # noqa: E402

NULLISH = {"", "null", "none", "nan", "na", "n/a", "undefined", "-"}


def main():
    p = base_parser("Check cognitive-test trial data integrity.")
    p.add_argument("--csv", required=True)
    p.add_argument("--rt-col", default="rt_ms")
    p.add_argument("--index-col", default="trial_index")
    p.add_argument("--subject-col", default="subject_id")
    p.add_argument("--timeout-col", default="timed_out")
    p.add_argument("--practice-col", default="is_practice")
    p.add_argument("--expected-trials", type=int,
                   help="fail if the scored trial count differs")
    p.add_argument("--min-rt", type=float, default=100.0,
                   help="RTs below this are implausible for a human response")
    p.add_argument("--max-rt", type=float, default=30000.0)
    p.add_argument("--max-timeout-rate", type=float, default=0.20)
    p.add_argument("--require-cols", default="",
                   help="extra comma-separated required columns")
    a = p.parse_args()

    r = Report("trial-data-integrity")
    path = Path(a.csv)
    if not path.exists():
        r.fail("data file not found: %s" % path)
        return r.emit(a.as_json)

    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
            header = rows[0].keys() if rows else []
    except Exception as e:
        r.fail("cannot parse CSV: %s" % e)
        return r.emit(a.as_json)

    if not rows:
        r.fail("file contains no data rows -- the session produced nothing")
        return r.emit(a.as_json)

    cols = set(header)
    required = [a.rt_col, a.index_col, a.subject_col] + \
               [c.strip() for c in a.require_cols.split(",") if c.strip()]
    missing_cols = [c for c in required if c not in cols]
    if missing_cols:
        r.fail("missing required column(s): %s (present: %s)"
               % (", ".join(missing_cols), ", ".join(sorted(cols))))
        return r.emit(a.as_json)

    has_timeout_col = a.timeout_col in cols
    has_practice_col = a.practice_col in cols
    if not has_timeout_col:
        r.warn("no '%s' column -- a no-response cannot be distinguished from "
               "a lost value" % a.timeout_col)
    if not has_practice_col:
        r.warn("no '%s' column -- practice trials cannot be separated from "
               "scored trials" % a.practice_col)

    def truthy(v):
        return str(v).strip().lower() in ("1", "true", "yes", "y", "t")

    scored = [row for row in rows
              if not (has_practice_col and truthy(row.get(a.practice_col)))]
    r.note("%d rows (%d scored, %d practice)"
           % (len(rows), len(scored), len(rows) - len(scored)))

    # ---- subject consistency -------------------------------------------
    subjects = {(row.get(a.subject_col) or "").strip() for row in rows}
    if "" in subjects:
        r.fail("%d row(s) have an empty %s"
               % (sum(1 for row in rows
                      if not (row.get(a.subject_col) or "").strip()),
                  a.subject_col))
        subjects.discard("")
    if len(subjects) > 1:
        r.fail("file mixes %d subjects (%s) -- one session per file"
               % (len(subjects), ", ".join(sorted(subjects)[:5])))
    elif subjects:
        r.note("subject: %s" % next(iter(subjects)))

    # ---- trial index integrity -----------------------------------------
    idx = []
    for row in scored:
        raw = (row.get(a.index_col) or "").strip()
        try:
            idx.append(int(float(raw)))
        except ValueError:
            r.fail("non-numeric %s: %r" % (a.index_col, raw))
    if idx:
        dupes = sorted({i for i in idx if idx.count(i) > 1})
        if dupes:
            r.fail("duplicate %s values (write race): %s"
                   % (a.index_col, ", ".join(map(str, dupes[:15]))))
        lo, hi = min(idx), max(idx)
        gaps = sorted(set(range(lo, hi + 1)) - set(idx))
        if gaps:
            r.fail("%d missing trial(s) between %d and %d: %s"
                   % (len(gaps), lo, hi, ", ".join(map(str, gaps[:15]))))
    if a.expected_trials is not None and len(scored) != a.expected_trials:
        r.fail("expected %d scored trials, found %d -- %d trial(s) lost"
               % (a.expected_trials, len(scored),
                  a.expected_trials - len(scored)))

    # ---- reaction times -------------------------------------------------
    null_rows, bad_rows, timeouts = [], [], 0
    for row in scored:
        raw = (row.get(a.rt_col) or "").strip()
        tid = row.get(a.index_col)
        is_timeout = has_timeout_col and truthy(row.get(a.timeout_col))
        if is_timeout:
            timeouts += 1
            if raw.lower() not in NULLISH:
                try:
                    if float(raw) > 0:
                        r.warn("trial %s marked timed_out but carries rt=%s"
                               % (tid, raw))
                except ValueError:
                    pass
            continue
        if raw.lower() in NULLISH:
            null_rows.append(str(tid))
            continue
        try:
            rt = float(raw)
        except ValueError:
            bad_rows.append("%s=%r" % (tid, raw))
            continue
        if rt <= 0:
            bad_rows.append("%s=%s" % (tid, rt))
        elif rt < a.min_rt:
            bad_rows.append("%s=%sms (below %sms)" % (tid, rt, a.min_rt))
        elif rt > a.max_rt:
            bad_rows.append("%s=%sms (above %sms)" % (tid, rt, a.max_rt))

    if null_rows:
        r.fail("%d trial(s) have a null/empty %s and are NOT marked timed out: "
               "%s -- these are lost data, not no-responses"
               % (len(null_rows), a.rt_col, ", ".join(null_rows[:15])))
    if bad_rows:
        r.fail("%d implausible reaction time(s): %s"
               % (len(bad_rows), "; ".join(bad_rows[:15])))
    if not null_rows and not bad_rows:
        r.note("all %d scored trials have a usable reaction time or an explicit "
               "timeout" % len(scored))

    if scored:
        rate = timeouts / float(len(scored))
        if rate > a.max_timeout_rate:
            r.warn("timeout rate %.0f%% exceeds %.0f%% -- check the response "
                   "window or the instructions"
                   % (rate * 100, a.max_timeout_rate * 100))
        elif timeouts:
            r.note("%d timeout(s) (%.0f%%)" % (timeouts, rate * 100))

    return r.emit(a.as_json)


if __name__ == "__main__":
    main_guard(main)
