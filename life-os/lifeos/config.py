"""Read the SSOT at Life OS/Meta/Compass Config.md.

Stdlib only (invariant 1), so there is no PyYAML here. Instead there is a deliberately
narrow frontmatter parser that handles exactly the shapes the config file uses:

    key: scalar
    key:
      - scalar
    key:
      - id: x
        prompt: y
    key:
      sub: scalar

What it does NOT handle, on purpose: anchors, multi-line scalars (| and >), inline
flow collections ({a: 1}, [1, 2]), quoted keys, nested lists inside lists, documents
with more than one level of mapping nesting.

If the config ever needs one of those, the honest move is to widen the config's shape
back down to this subset rather than to grow a YAML implementation in here. A partial
YAML parser that silently mis-reads one key is worse than no parser, which is why
`parse_frontmatter` raises on anything it does not recognise instead of guessing.
"""

import os
import re

__all__ = [
    "ConfigError",
    "parse_frontmatter",
    "split_frontmatter",
    "load_config",
    "Config",
    "CLINICAL_LEVELS",
]

# Graduated clinical access. Ordered least to most permissive.
# Decided 2026-09-29 by the user: "derived".
CLINICAL_LEVELS = ("never", "local", "derived", "full")

_TRUE = ("true", "yes", "on")
_FALSE = ("false", "no", "off")


class ConfigError(Exception):
    """The config could not be read, or was read ambiguously."""


def _scalar(raw):
    """Coerce a YAML scalar to int / bool / None / str. Strips inline comments."""
    s = raw.strip()

    # An inline comment only counts when preceded by whitespace, so that a value
    # like "#1 priority" survives.
    if s and not (s.startswith('"') or s.startswith("'")):
        m = re.search(r"\s+#", s)
        if m:
            s = s[: m.start()].strip()

    if (len(s) >= 2) and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    if s == "" or s == "~" or s.lower() == "null":
        return None
    low = s.lower()
    if low in _TRUE:
        return True
    if low in _FALSE:
        return False
    if re.match(r"^-?\d+$", s):
        return int(s)
    if re.match(r"^-?\d+\.\d+$", s):
        return float(s)
    return s


def _strip_lines(text):
    """Drop blank lines and whole-line comments, keeping (indent, content) pairs."""
    out = []
    for line in text.splitlines():
        if line.strip() == "":
            continue
        if line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        out.append((indent, line.strip()))
    return out


def parse_frontmatter(text):
    """Parse the YAML subset described in this module's docstring.

    Raises ConfigError on any construct outside the subset.
    """
    lines = _strip_lines(text)
    root = {}
    i = 0
    n = len(lines)

    while i < n:
        indent, content = lines[i]
        if indent != 0:
            raise ConfigError("unexpected indentation at top level: %r" % content)
        if content.startswith("- "):
            raise ConfigError("top-level list is not supported: %r" % content)
        if ":" not in content:
            raise ConfigError("expected 'key: value', got %r" % content)

        key, _, rest = content.partition(":")
        key = key.strip()
        rest = rest.strip()

        if rest != "":
            root[key] = _scalar(rest)
            i += 1
            continue

        # Block follows. Collect every line indented deeper than this key.
        j = i + 1
        block = []
        while j < n and lines[j][0] > indent:
            block.append(lines[j])
            j += 1

        if not block:
            root[key] = None
        elif block[0][1].startswith("- "):
            root[key] = _parse_list(block)
        else:
            root[key] = _parse_map(block)
        i = j

    return root


def _parse_list(block):
    """A list of scalars, or a list of flat mappings."""
    base = block[0][0]
    items = []
    idx = 0
    while idx < len(block):
        indent, content = block[idx]
        if indent != base or not content.startswith("- "):
            raise ConfigError("malformed list item: %r" % content)
        body = content[2:].strip()

        if ":" in body and not body.startswith(("\"", "'")):
            # list of mappings: first pair is on the dash line, the rest are indented
            item = {}
            k, _, v = body.partition(":")
            item[k.strip()] = _scalar(v)
            idx += 1
            while idx < len(block) and block[idx][0] > base and not block[idx][1].startswith("- "):
                sub = block[idx][1]
                if ":" not in sub:
                    raise ConfigError("expected 'key: value' inside list item: %r" % sub)
                sk, _, sv = sub.partition(":")
                item[sk.strip()] = _scalar(sv)
                idx += 1
            items.append(item)
        else:
            items.append(_scalar(body))
            idx += 1
    return items


def _parse_map(block):
    """A flat mapping one level below its key."""
    base = block[0][0]
    out = {}
    for indent, content in block:
        if indent != base:
            raise ConfigError("nested mapping deeper than one level: %r" % content)
        if ":" not in content:
            raise ConfigError("expected 'key: value', got %r" % content)
        k, _, v = content.partition(":")
        out[k.strip()] = _scalar(v)
    return out


def split_frontmatter(raw):
    """Return (frontmatter_text, body). Raises ConfigError if there is no frontmatter."""
    if not raw.startswith("---"):
        raise ConfigError("file does not start with '---'")
    # Find the closing fence on its own line.
    m = re.search(r"^---\s*$", raw[3:], re.M)
    if not m:
        raise ConfigError("frontmatter is not closed by '---'")
    fm = raw[3 : 3 + m.start()]
    body = raw[3 + m.end() :]
    return fm, body


class Config(object):
    """Typed accessors over the parsed config, with the defaults in one place."""

    def __init__(self, data, path=None):
        self.data = data or {}
        self.path = path

    # -- plain values ---------------------------------------------------
    @property
    def start_date(self):
        return str(self.data.get("start_date") or "")

    @property
    def daily_note_folder(self):
        # `daily_folder` is upstream Compass's key (value there: "01 Journal/Daily").
        return (self.data.get("daily_note_folder")
                or self.data.get("daily_folder")
                or "每日筆記")

    @property
    def reflection_heading(self):
        return self.data.get("reflection_heading") or "💡 今日反思"

    @property
    def clinical_heading(self):
        return self.data.get("clinical_heading") or "🏥 臨床"

    @property
    def clinical_access(self):
        """One of CLINICAL_LEVELS. Defaults to the most restrictive.

        Decided by the user on 2026-09-29: `derived`. See UNKNOWNS.md U4.

            never    nothing reads the section at all
            local    code may read it; nothing derived from it may be transmitted
            derived   code may read it and may transmit *numeric* facts only
            full      the raw text may be placed in a model prompt

        An unrecognised value falls back to `never` rather than being trusted — a typo in
        the config must not silently widen access.
        """
        raw = self.data.get("clinical_access") or "never"
        return raw if raw in CLINICAL_LEVELS else "never"

    @property
    def clinical_local_ok(self):
        """May code read the section at all?"""
        return self.clinical_access in ("local", "derived", "full")

    @property
    def clinical_derived_ok(self):
        """May numeric facts derived from the section be put in a prompt?"""
        return self.clinical_access in ("derived", "full")

    @property
    def clinical_full_ok(self):
        """May the raw text be put in a prompt? Requires an explicit `full`."""
        return self.clinical_access == "full"

    # -- collections ----------------------------------------------------
    # Two config shapes are accepted, because upstream Compass and this repo differ.
    # Verified against the real repo 2026-09-29 (UNKNOWNS.md U1):
    #
    #   upstream Compass          this repo
    #   questions:                dq_questions:
    #     - key: dq_goals           - id: dq_read
    #       text: Did I ...            prompt: 我今天...
    #   habits:                   habits:
    #     - habit_journal           - id: habit_move
    #                                 name: 動 20 分鐘
    #
    # Upstream's flat string lists cannot carry a display name separate from the key,
    # which a 繁體中文 vault needs — `habit_move` is not a label a human wants to read.
    # So this repo keeps the richer shape and *also* parses upstream's, rather than
    # forcing a choice between interop and legibility.
    def _normalize(self, item, prefix, group):
        """Accept a bare string, {id,prompt/name}, or upstream {key,text}."""
        if isinstance(item, str):
            return {"id": item, "name": item, "prompt": item}
        if not isinstance(item, dict):
            return None

        ident = item.get("id") or item.get("key")
        if not ident:
            return None
        ident = str(ident)
        if not ident.startswith(prefix):
            raise ConfigError(
                "%s entry %r must start with %r (invariant 7)" % (group, ident, prefix)
            )

        label = item.get("prompt") or item.get("text") or item.get("name") or ident
        out = dict(item)
        out["id"] = ident
        out.setdefault("prompt", label)
        out.setdefault("name", label)
        return out

    def _ids(self, key, prefix, alt=None):
        raw = self.data.get(key)
        if raw is None and alt:
            raw = self.data.get(alt)
        out = []
        for item in raw or []:
            norm = self._normalize(item, prefix, key)
            if norm:
                out.append(norm)
        return out

    @property
    def dq_questions(self):
        # `questions` is upstream Compass's key for the same list.
        return self._ids("dq_questions", "dq_", alt="questions")

    @property
    def habits(self):
        return self._ids("habits", "habit_")

    @property
    def wheel_areas(self):
        return self._ids("wheel_areas", "wheel_")

    @property
    def dq_ids(self):
        return [q["id"] for q in self.dq_questions]

    @property
    def habit_ids(self):
        return [h["id"] for h in self.habits]

    @property
    def wheel_ids(self):
        return [w["id"] for w in self.wheel_areas]

    # -- memento (upstream Compass feature, Meta/views/memento.js) ------
    # birthdate + life_expectancy render "weeks lived / weeks remaining". It is the
    # emotional engine of the whole system: the reason to answer the questions tonight
    # rather than eventually. Both optional; absent birthdate simply disables it.
    @property
    def birthdate(self):
        raw = self.data.get("birthdate")
        return str(raw).strip().strip("'\"")[:10] if raw else ""

    @property
    def life_expectancy(self):
        try:
            return int(self.data.get("life_expectancy") or 80)
        except (TypeError, ValueError):
            return 80

    @property
    def memento_ok(self):
        return bool(self.birthdate)

    @property
    def unlock_days(self):
        # Compass Build Order layers; legacy daily/weekly/quarterly keys still accepted.
        from .unlock import normalise_days
        return normalise_days(self.data.get("unlock_days"))

    # -- Compass folder map (upstream keys, placed under Life OS/) -------
    def folder(self, key, default):
        raw = self.data.get(key)
        return str(raw).strip().strip("'\"") if raw else default

    @property
    def weekly_folder(self):
        return self.folder("weekly_folder", "Life OS/01 Journal/Weekly")

    @property
    def quarterly_folder(self):
        return self.folder("quarterly_folder", "Life OS/01 Journal/Quarterly")

    @property
    def retreat_folder(self):
        return self.folder("retreat_folder", "Life OS/02 Retreats")

    @property
    def projects_folder(self):
        return self.folder("projects_folder", "Life OS/04 Projects")

    @property
    def people_folder(self):
        return self.folder("people_folder", "Life OS/05 People")

    @property
    def tasks_file(self):
        return self.folder("tasks_file", "Life OS/08 Tasks/任務總表.md")

    @property
    def display_bands(self):
        raw = self.data.get("display_bands") or {}
        return {"good": int(raw.get("good", 8)), "watch": int(raw.get("watch", 6))}

    def validate(self):
        """Return a list of human-readable problems. Empty list means healthy."""
        problems = []
        if not self.start_date:
            problems.append("start_date is missing — the unlock schedule cannot be computed")
        if not self.dq_questions and not self.habits:
            problems.append("no dq_questions and no habits — the nightly loop has nothing to ask")
        if len(self.dq_questions) > 6:
            problems.append(
                "%d dq_questions — over 5 turns a 30-second ritual into a chore"
                % len(self.dq_questions)
            )
        # validate() is a health check: it reports problems, it does not throw.
        # A mistyped prefix must arrive as a readable line, not as a traceback out of
        # checks.sh. Note that prefix enforcement makes a *cross-group* duplicate
        # structurally impossible, so this loop only ever catches within-group ones.
        seen = {}
        groups = []
        for name, getter in (("dq_questions", lambda: self.dq_questions),
                             ("habits", lambda: self.habits),
                             ("wheel_areas", lambda: self.wheel_areas)):
            try:
                groups.append((name, getter()))
            except ConfigError as exc:
                problems.append(str(exc))
        for group, items in groups:
            for item in items:
                ident = item.get("id")
                if ident in seen:
                    problems.append("duplicate id %r in %s and %s" % (ident, seen[ident], group))
                elif ident:
                    seen[ident] = group
        raw_level = self.data.get("clinical_access")
        if raw_level is not None and raw_level not in CLINICAL_LEVELS:
            problems.append(
                "clinical_access is %r, which is not one of %s — falling back to 'never'"
                % (raw_level, ", ".join(CLINICAL_LEVELS))
            )
        if self.clinical_full_ok:
            problems.append(
                "clinical_access is 'full': raw patient-adjacent text will be placed in "
                "model prompts. Confirm this is intended (UNKNOWNS.md U4)"
            )
        return problems


def load_config(path):
    """Read and parse the config markdown file at `path`."""
    if not os.path.exists(path):
        raise ConfigError("config not found: %s" % path)
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    fm, _body = split_frontmatter(raw)
    return Config(parse_frontmatter(fm), path=path)
