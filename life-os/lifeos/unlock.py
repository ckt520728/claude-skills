"""The layering rule, as code: Compass's Build Order, plus the 80% consistency gate.

This is [C] — exact rules. Dates are arithmetic, and a model asked "is the weekly review
due yet" will read the date as text and get it wrong at some point (invariant 5).

**Attribution, corrected 2026-09-30.** Session 2 wrote that upstream Compass contains no
layering rule. That was wrong: the full clone shows `Guide/11 Build Order.md` and
`Guide/01 Principles.md` §10, quoting Mike Schmitz — "Pick one workflow, run it for 30 days,
then add the next." The table below is that Build Order, with GTD folded into the Tasks layer:

| Days    | Upstream layer                         | Here                                  |
|---------|----------------------------------------|---------------------------------------|
| 1-30    | daily journaling + daily questions     | `journal`: nightly dq_*, daily dash   |
| 31-60   | habits + weekly note                   | `habits_weekly`: habit canvas, week   |
| 61-90   | first retreat + quarter + theme/values | `retreat`: wheel, planning notes      |
| 91-120  | tasks, projects, people                | `tasks`: task dash, GTD filing        |
| 121-150 | writing boards                         | `writing`: 創作看板                   |
| 151+    | reading / Bible module                 | not adopted — no equivalent asked for |

And upstream's rule: "Do not add a layer while the previous one is below 80% consistency."
Only the journal layer's consistency is *measured* here (days scored in the last 30), because
it is the foundation every later layer reads from. Later layers are gated on the day count
plus that one number. That is a deliberate narrowing, stated rather than hidden.

Capture is never gated: writing a thought into the inbox needs no schedule.

A dormant layer renders greyed out with its unlock date, never hidden.
"""

import datetime

__all__ = [
    "LAYERS", "LAYER_LABELS", "DEFAULT_UNLOCK_DAYS", "CONSISTENCY_WINDOW",
    "CONSISTENCY_REQUIRED", "day_number", "unlock_date", "journal_consistency",
    "is_unlocked", "active_layers", "status_table",
]

# Order matters: each layer's consistency prerequisite is the journal, and display is
# earliest first.
LAYERS = ("journal", "habits_weekly", "retreat", "tasks", "writing")

LAYER_LABELS = {
    "journal": "每日提問與日記",
    "habits_weekly": "習慣畫布與週回顧",
    "retreat": "季度退修、人生輪、人生規劃",
    "tasks": "任務、專案、人物、GTD 歸檔",
    "writing": "創作看板",
}

DEFAULT_UNLOCK_DAYS = {
    "journal": 1, "habits_weekly": 31, "retreat": 61, "tasks": 91, "writing": 121,
}

# Session-1 key names, still accepted so an older config keeps working.
_LEGACY = {"daily": "journal", "weekly": "habits_weekly", "quarterly": "retreat"}

# Upstream: "at least 25 of 30 days scored" and "below 80% consistency". Named constants
# (invariant 6), not numbers inside a dashboard.
CONSISTENCY_WINDOW = 30
CONSISTENCY_REQUIRED = 0.80


def _as_date(value):
    """Accept a date, a datetime, or a YYYY-MM-DD string."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    text = str(value).strip().strip("'\"")
    if not text:
        raise ValueError("empty date")
    return datetime.datetime.strptime(text[:10], "%Y-%m-%d").date()


def day_number(start_date, today=None):
    """1-based day count. start_date itself is day 1. <= 0 means not started."""
    start = _as_date(start_date)
    now = _as_date(today) if today is not None else datetime.date.today()
    return (now - start).days + 1


def unlock_date(start_date, unlock_day):
    """The calendar date on which a layer whose threshold is `unlock_day` opens."""
    return _as_date(start_date) + datetime.timedelta(days=int(unlock_day) - 1)


def normalise_days(raw):
    """Merge a config's unlock_days (new or legacy keys) over the defaults."""
    out = dict(DEFAULT_UNLOCK_DAYS)
    for key, value in (raw or {}).items():
        key = _LEGACY.get(key, key)
        if key in out:
            out[key] = int(value)
    return out


def journal_consistency(scored_dates, start_date=None, today=None, window=CONSISTENCY_WINDOW):
    """Fraction of the last `window` days that have a scored daily note.

    The denominator is the window, but never counts days before `start_date` — on day 10
    a perfect record is 10/10, not 10/30. Returns (fraction, scored, denominator).
    """
    now = _as_date(today) if today is not None else datetime.date.today()
    first = now - datetime.timedelta(days=window - 1)
    if start_date:
        first = max(first, _as_date(start_date))
    denom = (now - first).days + 1
    if denom <= 0:
        return (0.0, 0, 0)
    scored = set()
    for d in scored_dates or ():
        try:
            dd = _as_date(d)
        except ValueError:
            continue
        if first <= dd <= now:
            scored.add(dd)
    return (len(scored) / float(denom), len(scored), denom)


def is_unlocked(config, layer, today=None, consistency=None):
    """True when `layer` is open.

    `consistency` is the journal fraction from `journal_consistency`. When given, every
    layer after the journal also needs it at or above CONSISTENCY_REQUIRED. When None
    (not measured), only the day count applies.
    """
    days = config.unlock_days
    if layer not in days:
        raise KeyError("unknown layer: %r" % layer)
    if layer == LAYERS[0]:
        return True
    if not config.start_date:
        # No start date: the schedule is undefined. Fail closed to the foundation layer.
        return False
    if day_number(config.start_date, today) < days[layer]:
        return False
    if consistency is not None and consistency < CONSISTENCY_REQUIRED:
        return False
    return True


def active_layers(config, today=None, consistency=None):
    return dict((l, is_unlocked(config, l, today, consistency)) for l in LAYERS)


def status_table(config, today=None, consistency=None):
    """Rows of (layer, unlocked, unlock_day, unlock_date_iso, days_remaining, blocked_by).

    `blocked_by` is "" when open, "days" when still waiting on the calendar, and
    "consistency" when the day has come but the journal is below the bar.
    """
    days = config.unlock_days
    rows = []
    current = day_number(config.start_date, today) if config.start_date else 0
    for layer in LAYERS:
        threshold = days[layer]
        unlocked = is_unlocked(config, layer, today, consistency)
        iso = unlock_date(config.start_date, threshold).isoformat() if config.start_date else ""
        remaining = max(0, threshold - current) if config.start_date else None
        if unlocked:
            why = ""
        elif remaining:
            why = "days"
        else:
            why = "consistency"
        rows.append((layer, unlocked, threshold, iso, remaining, why))
    return rows
