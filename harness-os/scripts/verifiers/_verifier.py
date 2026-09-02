"""Shared plumbing for Harness OS profile verifiers.

Every verifier is a standalone CLI that exits 0 (pass) or 1 (fail), so it can be
dropped straight into a contract as `cmd:python .../check_x.py --args`.

Two rules all verifiers follow:

1. **Failures name the specific thing that is wrong**, with enough detail to act
   on without opening the file. "3 citations unresolved" is useless; "[7], [12],
   [19] have no entry in the reference list" is actionable.
2. **Warnings never fail the build.** A verifier that fails on a heuristic
   teaches people to weaken contracts, which is the one thing the whole system
   is built to prevent. Heuristics warn; only deterministic violations fail.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


class Report:
    def __init__(self, name):
        self.name = name
        self.failures = []   # deterministic violations -> exit 1
        self.warnings = []   # heuristics -> reported, exit unaffected
        self.notes = []      # counts and context

    def fail(self, msg):
        self.failures.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def note(self, msg):
        self.notes.append(msg)

    @property
    def passed(self):
        return not self.failures

    def emit(self, as_json=False):
        if as_json:
            print(json.dumps({
                "verifier": self.name,
                "passed": self.passed,
                "failures": self.failures,
                "warnings": self.warnings,
                "notes": self.notes,
            }, indent=2, ensure_ascii=False))
        else:
            status = "PASS" if self.passed else "FAIL"
            print("[%s] %s" % (status, self.name))
            for n in self.notes:
                print("  . %s" % n)
            for w in self.warnings:
                print("  ! warning: %s" % w)
            for f in self.failures:
                print("  X %s" % f)
        return 0 if self.passed else 1


def base_parser(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--json", action="store_true", dest="as_json",
                   help="machine-readable output")
    return p


def read_text(path, report):
    p = Path(path)
    if not p.exists():
        report.fail("file not found: %s" % p)
        return None
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        report.fail("cannot read %s: %s" % (p, e))
        return None


def read_json(path, report):
    text = read_text(path, report)
    if text is None:
        return None
    try:
        return json.loads(text)
    except Exception as e:
        report.fail("invalid JSON in %s: %s" % (path, e))
        return None


def split_sections(md_text):
    """Split markdown into {heading_text: body}, preserving order.

    Content before the first heading is keyed as "" so nothing is silently lost.
    """
    sections = {}
    order = []
    current = ""
    buf = []
    for line in md_text.split("\n"):
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            sections[current] = "\n".join(buf)
            if current not in order:
                order.append(current)
            current = m.group(2).strip()
            buf = []
        else:
            buf.append(line)
    sections[current] = "\n".join(buf)
    if current not in order:
        order.append(current)
    return sections, order


def find_section(sections, wanted):
    """Match a section by case-insensitive substring, so '研究方法' finds
    '三、研究方法與實驗設計'."""
    w = wanted.strip().lower()
    for head, body in sections.items():
        if w in head.lower():
            return head, body
    return None, None


def paragraphs(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def normalise(s):
    """Lowercase, strip punctuation and whitespace runs. CJK-safe: we do not
    tokenise on spaces, so Chinese text still normalises usefully."""
    s = s.lower()
    s = re.sub(r"[^\w一-鿿]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def shingles(s, k=5):
    """Character k-grams. Works for both English and CJK, unlike word tokens."""
    s = normalise(s).replace(" ", "")
    if len(s) < k:
        return {s} if s else set()
    return {s[i:i + k] for i in range(len(s) - k + 1)}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def main_guard(fn):
    """Run a verifier's main() and turn an unexpected crash into a clean FAIL.

    A verifier that crashes must not look like a pass to the shell.
    """
    try:
        sys.exit(fn())
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print("[FAIL] verifier crashed: %s: %s" % (type(e).__name__, e))
        sys.exit(1)
