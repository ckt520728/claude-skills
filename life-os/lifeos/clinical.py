"""The clinical section: read locally, transmit only numbers.

Activated by the user on **2026-09-29** at level `derived` (UNKNOWNS.md U4, now resolved).

    never     nothing reads the section
    local     code may read it; nothing derived from it may be transmitted
    derived   <- CHOSEN: code may read it, and may transmit numeric facts only
    full      the raw text may be placed in a model prompt

The whole point of this module is that "the coach must not see patient text" is enforced by
**structure**, not by a sentence in a prompt that a model is trusted to obey. Two mechanisms
do that work:

1. `extract_section()` returns raw text and is the only function that can. Its return value
   is never returned by anything else in this module, so a caller that wants raw text has to
   ask for it by name — there is no path where it arrives by accident.

2. `ClinicalDigest` has fixed `__slots__` that can hold **numbers and booleans only**, and
   `as_dict()` runs `assert_transmittable()` before returning. A string cannot be smuggled
   into the thing that goes to the model, because the container refuses to carry one.

`eval/test_smoke.py` pins this: it builds a digest from clinical text full of distinctive
tokens and asserts that not one of those tokens appears anywhere in the transmittable output.
That test is the actual guarantee. The docstrings are just an explanation of it.

Why counting bullets is a reasonable proxy: the user's daily note keeps cases as a bullet
list under `**待處理個案**`. The count of open items is the workload signal that matters for
coaching ("six pending cases tonight, and dq_read dropped three points"), and it carries no
patient information at all.
"""

import io
import os
import re

__all__ = [
    "ClinicalAccessDenied",
    "ClinicalDigest",
    "CLINICAL_FRONTMATTER_KEYS",
    "extract_section",
    "digest_from_text",
    "digest_from_file",
    "assert_transmittable",
    "load_band",
]

# The keys nightly.js writes into the daily note's frontmatter. Frontmatter is the
# transmittable surface; the `## 🏥 臨床` body is not. Keeping the derived facts in
# frontmatter means the coach reads them the same way it reads dq_* scores, and never
# has a reason to open the body at all.
CLINICAL_FRONTMATTER_KEYS = ("clinical_pending", "clinical_load")

_BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
_EMPTY_BULLET = re.compile(r"^\s*[-*+]\s*$")
_H2 = re.compile(r"^##\s+", re.M)

# Case-count -> 1..5 load band. Thresholds are named here rather than inline so the
# mapping is auditable, and they are display/context only: nothing automatic keys off them.
LOAD_THRESHOLDS = ((0, 1), (2, 2), (5, 3), (9, 4))
LOAD_MAX = 5


class ClinicalAccessDenied(Exception):
    """A caller asked for more clinical access than the config grants."""


def load_band(pending):
    """Map an open-case count to 1..5. None stays None."""
    if pending is None:
        return None
    band = LOAD_MAX
    for ceiling, value in LOAD_THRESHOLDS:
        if pending <= ceiling:
            band = value
            break
    return band


class ClinicalDigest(object):
    """Numeric facts derived from the clinical section. Cannot carry text.

    `__slots__` is the enforcement: there is nowhere to put a string. Adding a string field
    here would be a deliberate act that breaks the purity test, which is the point.
    """

    __slots__ = ("pending_cases", "case_lines", "load", "has_content")

    def __init__(self, pending_cases=None, case_lines=None, load=None, has_content=False):
        self.pending_cases = pending_cases
        self.case_lines = case_lines
        self.load = load
        self.has_content = has_content

    def as_dict(self):
        """The transmittable form. Verified pure before it is handed out."""
        out = {
            "clinical_pending": self.pending_cases,
            "clinical_load": self.load,
        }
        assert_transmittable(out)
        return out

    def as_context_line(self):
        """One 繁中 line safe to put in a coaching prompt. Numbers only."""
        if not self.has_content or self.pending_cases is None:
            return "臨床：今日無紀錄"
        return "臨床：待處理 %d 例，負荷 %s/5" % (
            self.pending_cases,
            self.load if self.load is not None else "—",
        )

    def __repr__(self):
        return "ClinicalDigest(pending=%s, load=%s)" % (self.pending_cases, self.load)


def assert_transmittable(mapping):
    """Raise unless every value is a number, bool or None.

    This is the gate between the clinical section and anything that leaves the machine.
    A string value means raw text has leaked into the derived layer.
    """
    for key, value in mapping.items():
        if value is None or isinstance(value, bool) or isinstance(value, (int, float)):
            continue
        raise ClinicalAccessDenied(
            "refusing to transmit %r: derived clinical facts must be numeric, got %r"
            % (key, type(value).__name__)
        )
    return True


def extract_section(text, heading):
    """Return the raw body of `## heading`, up to the next H2 or EOF.

    LOCAL USE ONLY. The return value of this function must never be placed in a prompt,
    a log line, an error message, or a network call while `clinical_access` is below `full`.
    Every caller in this codebase passes it straight into `digest_from_text` and discards it.
    """
    pattern = re.compile(r"^##\s*" + re.escape(heading.strip()) + r"\s*$", re.M)
    m = pattern.search(text or "")
    if not m:
        return ""
    nxt = _H2.search(text, m.end())
    end = nxt.start() if nxt else len(text)
    return text[m.end():end]


def _count_cases(section):
    """Count non-empty bullet lines. Bold labels like `**待處理個案**：` are not bullets."""
    lines = 0
    cases = 0
    for line in (section or "").splitlines():
        if _EMPTY_BULLET.match(line):
            lines += 1
            continue
        m = _BULLET.match(line)
        if m:
            lines += 1
            body = m.group(1).strip()
            # A bullet holding only formatting or a placeholder is not a case.
            if body and body not in ("-", "—", "…"):
                cases += 1
    return cases, lines


def digest_from_text(text, config):
    """Derive numeric clinical facts from a note's full text.

    Raises ClinicalAccessDenied when the config forbids reading the section at all.
    """
    if not config.clinical_local_ok:
        raise ClinicalAccessDenied(
            "clinical_access is %r — reading the clinical section is not permitted"
            % config.clinical_access
        )

    section = extract_section(text, config.clinical_heading)
    if not section.strip():
        return ClinicalDigest(pending_cases=0, case_lines=0, load=load_band(0), has_content=False)

    cases, lines = _count_cases(section)
    # `section` goes out of scope here and is never returned, logged or stored.
    return ClinicalDigest(
        pending_cases=cases,
        case_lines=lines,
        load=load_band(cases),
        has_content=True,
    )


def digest_from_file(path, config):
    """Same, reading from a daily note on disk. Returns an empty digest if absent."""
    if not os.path.exists(path):
        return ClinicalDigest()
    with io.open(path, "r", encoding="utf-8") as fh:
        return digest_from_text(fh.read(), config)


def coach_context(digest, config):
    """The clinical facts a coaching prompt may receive, given the access level.

    `derived` -> numeric facts. `full` would additionally permit raw text, and this
    function deliberately still does not return it: widening that is a separate,
    explicit change, not a side effect of flipping one config value.
    """
    if not config.clinical_derived_ok:
        return {}
    return digest.as_dict()
