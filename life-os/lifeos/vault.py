"""Append-only writes into the vault.

Invariant 2 is the one whose violation loses real data, so it is enforced here rather than
left to each caller's care. Everything that writes to a daily note goes through
`append_under_heading`, and that function's contract is narrow on purpose:

    - it never shortens a file
    - it never modifies a byte before its insertion point
    - it refuses to touch the clinical section at all
    - it verifies the result before committing, and raises rather than write a file it
      cannot prove is a superset of what was there

The last point matters because the vault lives on Google Drive (UNKNOWNS.md U6). A lost
update during a sync is survivable when every write is additive; it is not survivable when
a write rewrites a whole file.
"""

import io
import os
import re

__all__ = ["AppendOnlyViolation", "ClinicalSectionBlocked", "append_under_heading", "set_frontmatter"]


class AppendOnlyViolation(Exception):
    """A proposed write would have removed or altered existing content."""


class ClinicalSectionBlocked(Exception):
    """Something tried to read or write the clinical section. See UNKNOWNS.md U4."""


def _heading_re(heading):
    return re.compile(r"^##\s*" + re.escape(heading.strip()) + r"\s*$", re.M)


def _assert_superset(before, after):
    """Every non-whitespace character of `before` must survive, in order, in `after`.

    A subsequence check rather than a substring check, because inserting a block mid-file
    legitimately splits the original text. It still catches deletion, truncation and
    reordering, which are the failures that lose data.
    """
    b = re.sub(r"\s+", "", before)
    a = re.sub(r"\s+", "", after)
    if len(a) < len(b):
        raise AppendOnlyViolation("result is shorter than the original (%d < %d chars)" % (len(a), len(b)))
    i = 0
    for ch in a:
        if i < len(b) and ch == b[i]:
            i += 1
    if i != len(b):
        raise AppendOnlyViolation(
            "original content is not preserved: matched %d of %d characters" % (i, len(b))
        )


def append_under_heading(path, heading, block, clinical_heading=None, create=False):
    """Insert `block` directly beneath `## heading`, creating the heading at EOF if absent.

    Returns True when the file changed. Raises ClinicalSectionBlocked if `heading` is the
    clinical one, and AppendOnlyViolation if the result would not preserve the original.
    """
    if clinical_heading and heading.strip() == clinical_heading.strip():
        raise ClinicalSectionBlocked(
            "refusing to write under %r — clinical_access is never (UNKNOWNS.md U4)" % heading
        )

    if not os.path.exists(path):
        if not create:
            raise IOError("no such file: %s" % path)
        before = ""
    else:
        with io.open(path, "r", encoding="utf-8") as fh:
            before = fh.read()

    # Whitespace-only is a no-op, not an empty insertion: a nightly run where the user
    # skipped the reflection must not stamp a blank bullet into the journal.
    if not (block or "").strip():
        return False
    block = block.rstrip()

    match = _heading_re(heading).search(before)
    if match:
        at = match.end()
        after = before[:at] + "\n\n" + block + before[at:]
    else:
        sep = "" if before == "" else before.rstrip("\n") + "\n\n"
        after = sep + "## " + heading.strip() + "\n\n" + block + "\n"

    _assert_superset(before, after)

    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(after)
    return True


def read_body_without_clinical(path, clinical_heading):
    """Read a note's body with the clinical section removed.

    Anything that hands note content to a model goes through this. The clinical section is
    dropped before the text ever reaches a prompt, so "the agent must not read it" is a
    property of the code path rather than an instruction a model is trusted to follow.
    """
    if not os.path.exists(path):
        return ""
    with io.open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()

    pattern = _heading_re(clinical_heading)
    m = pattern.search(raw)
    if not m:
        return raw
    # Drop from the clinical heading up to the next H2, or EOF.
    nxt = re.compile(r"^##\s+", re.M).search(raw, m.end())
    end = nxt.start() if nxt else len(raw)
    return raw[: m.start()] + raw[end:]


_FM_FENCE = re.compile(r"^---\s*$", re.M)


def set_frontmatter(path, updates, create=False):
    """Add or update flat frontmatter keys, leaving the body and key order untouched.

    Existing keys are replaced in place; new keys are appended to the end of the block.
    The body is never rewritten, so this is safe under invariant 2.
    """
    if not os.path.exists(path):
        if not create:
            raise IOError("no such file: %s" % path)
        lines = ["---", "---", ""]
        raw = "\n".join(lines)
    else:
        with io.open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()

    if not raw.startswith("---"):
        raw = "---\n---\n\n" + raw

    close = _FM_FENCE.search(raw[3:])
    if not close:
        raise ValueError("frontmatter is not closed: %s" % path)

    fm = raw[3 : 3 + close.start()]
    rest = raw[3 + close.end() :]

    fm_lines = [ln for ln in fm.split("\n")]
    remaining = dict(updates)

    for idx, line in enumerate(fm_lines):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", line)
        if m and m.group(1) in remaining:
            key = m.group(1)
            fm_lines[idx] = "%s: %s" % (key, _fmt(remaining.pop(key)))

    tail = ["%s: %s" % (k, _fmt(v)) for k, v in remaining.items()]
    body_fm = "\n".join([ln for ln in fm_lines if ln.strip() != ""] + tail)

    after = "---\n" + body_fm + "\n---" + rest
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(after)
    return True


def _fmt(value):
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return ""
    return str(value)
