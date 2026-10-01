"""[C] arithmetic over the daily notes: means, deltas, streaks, wheel roll-up.

Every number a dashboard or a coaching prompt quotes comes from here, not from a model.
Invariant 5: the model reads dates as text and miscounts at scale. It is also the reason
the coaching prompt is handed *computed* figures rather than asked to compute them —
the LLM's job is the conversation, not the mean.

Two rules this module holds to, both of which matter more than they look:

1. **A missing score is missing, not zero.** Skipping a question on a tired night must not
   drag the mean down, or the metric punishes honesty and the user learns to answer
   everything carelessly instead of some things truthfully.
2. **Denominators are stated.** `Mean.n` travels with `Mean.value` everywhere. A 7-day
   average computed from two answers is not a 7-day average, and a dashboard that hides
   the count invites exactly that misreading.
"""

import datetime
import os
import re

__all__ = ["Mean", "Streak", "read_daily", "collect", "mean_of", "streak_of", "wheel_snapshot"]

_FM_SPLIT = re.compile(r"^---\s*$", re.M)
# Only flat `key: value` pairs are read from a daily note. Daily notes are written by
# nightly.js as flat frontmatter, so nothing deeper is expected; anything deeper is skipped
# rather than guessed at.
_PAIR = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")


class Mean(object):
    """A mean that carries its own denominator."""

    __slots__ = ("key", "value", "n", "window")

    def __init__(self, key, value, n, window):
        self.key = key
        self.value = value  # None when n == 0
        self.n = n
        self.window = window

    @property
    def is_empty(self):
        return self.n == 0

    def __repr__(self):
        v = "None" if self.value is None else ("%.2f" % self.value)
        return "Mean(%s=%s, n=%d/%d)" % (self.key, v, self.n, self.window)


class Streak(object):
    """Consecutive-day run for a boolean habit, plus its hit rate in the window."""

    __slots__ = ("key", "current", "hits", "window", "n")

    def __init__(self, key, current, hits, window, n):
        self.key = key
        self.current = current
        self.hits = hits
        self.window = window
        self.n = n

    @property
    def rate(self):
        """Hits over days actually recorded, or None when nothing was recorded."""
        if self.n == 0:
            return None
        return float(self.hits) / float(self.n)

    def __repr__(self):
        return "Streak(%s, current=%d, %d/%d recorded)" % (
            self.key, self.current, self.hits, self.n
        )


def _coerce(raw):
    s = raw.strip()
    if s == "":
        return None
    if (len(s) >= 2) and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1]
    low = s.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if re.match(r"^-?\d+$", s):
        return int(s)
    if re.match(r"^-?\d+\.\d+$", s):
        return float(s)
    return s


def read_daily(path):
    """Return the flat frontmatter dict of one daily note, or {} if it has none.

    Deliberately does not read the note body. The clinical section lives in the body,
    and Life OS does not read it (UNKNOWNS.md U4).
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except (IOError, OSError):
        return {}
    if not raw.startswith("---"):
        return {}
    m = _FM_SPLIT.search(raw[3:])
    if not m:
        return {}
    out = {}
    for line in raw[3 : 3 + m.start()].splitlines():
        if line.strip() == "" or line.lstrip().startswith("#"):
            continue
        if line.startswith(" ") or line.startswith("\t"):
            continue  # nested; not expected in a daily note
        pair = _PAIR.match(line.strip())
        if pair:
            out[pair.group(1)] = _coerce(pair.group(2))
    return out


def collect(folder, window=7, today=None, fmt="%Y-%m-%d"):
    """Read the last `window` daily notes, most recent first.

    Returns a list of (date, frontmatter_dict) for days whose file exists. Absent days are
    omitted rather than represented as empty, so callers can tell "did not journal" from
    "journalled and skipped that question".
    """
    end = today if isinstance(today, datetime.date) else datetime.date.today()
    rows = []
    for back in range(window):
        day = end - datetime.timedelta(days=back)
        path = os.path.join(folder, day.strftime(fmt) + ".md")
        if os.path.exists(path):
            rows.append((day, read_daily(path)))
    return rows


def mean_of(rows, key, window=None):
    """Mean of `key` across `rows`, ignoring days where it is absent or non-numeric."""
    vals = []
    for _day, fm in rows:
        v = fm.get(key)
        if isinstance(v, bool):
            continue  # a habit, not a score
        if isinstance(v, (int, float)):
            vals.append(float(v))
    w = window if window is not None else len(rows)
    if not vals:
        return Mean(key, None, 0, w)
    return Mean(key, sum(vals) / len(vals), len(vals), w)


def streak_of(rows, key):
    """Current consecutive-day run of `key` being true, counting back from the newest row.

    `rows` must be newest-first, as `collect` returns them. A day with no entry for `key`
    breaks the streak — an unrecorded day is not a success.
    """
    current = 0
    broken = False
    hits = 0
    recorded = 0
    for _day, fm in rows:
        v = fm.get(key)
        if isinstance(v, bool):
            recorded += 1
            if v:
                hits += 1
                if not broken:
                    current += 1
            else:
                broken = True
        else:
            broken = True
    return Streak(key, current, hits, len(rows), recorded)


def delta_vs_mean(today_value, mean):
    """Signed gap between today and the window mean. None when either side is missing.

    This is the number the coaching prompt keys off: a score below its own recent mean is
    the thing worth asking about, not a score below some absolute bar.
    """
    if today_value is None or mean is None or mean.value is None:
        return None
    if isinstance(today_value, bool):
        return None
    return float(today_value) - mean.value


def wheel_snapshot(path, wheel_ids):
    """Read `wheel_*` scores from one retreat note. Missing areas come back as None."""
    fm = read_daily(path)
    return dict((wid, fm.get(wid)) for wid in wheel_ids)


def band(value, bands):
    """Map a score to a display band. Presentation only — never an action.

    Actions gate on confidence in gtd.py, never on these.
    """
    if value is None:
        return "none"
    if value >= bands.get("good", 8):
        return "good"
    if value >= bands.get("watch", 6):
        return "watch"
    return "low"
