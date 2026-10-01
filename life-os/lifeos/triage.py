"""The ask-resolution flow: where a decision meets a human and becomes a label.

Until this module existed, `calibrate.py` could learn and nothing ever taught it. The layer
would have stayed cold forever, escalating everything — safe, and useless.

## The trap this module is built around

The obvious design records every decision as an observation. That is wrong, and quietly so.

An `AUTO` decision nobody looked at is **not evidence that it was right**. Recording it as
correct builds a loop that confirms itself: the band looks accurate because nothing ever
contradicts it, its confidence rises, it auto-files more, and it generates even less evidence.
By the time it is visibly wrong the calibration file says it is excellent.

So: **only adjudicated decisions become observations.** A human either agreed or corrected,
and that is the only signal recorded.

Which creates the opposite problem. Once a band goes warm and starts auto-filing, it stops
being adjudicated, so it can never be corrected downward — it is frozen at whatever accuracy
it had when it graduated. Drift becomes invisible.

The fix is **audit sampling**: a fixed fraction of `AUTO` decisions are shown for confirmation
anyway. The user sees "I filed this as X — right?" and one click keeps the band measured. That
is the cost of trusting automation, and it is deliberately not zero.

## Shadow mode, and why the lock is productive

GTD filing is locked until the `tasks` layer opens (day 91, `unlock.py`). But *labelling* is safe from day 1: propose a
bucket, ask the human, record the outcome, write nothing. That is exactly rule 7's shadow
period, and running it during the locked months means the layer arrives at the tasks layer already
carrying evidence instead of stone cold.

So the lock stops being a wait and becomes the training window.
"""

import io
import json
import os
import random
import time

from . import gtd, unlock

__all__ = [
    "AUDIT_SAMPLE_RATE", "Resolution", "Pending",
    "parse_inbox", "propose", "resolve", "needs_human", "sample_for_audit",
    "log_resolution", "load_log", "summarize_log",
]

# Fraction of AUTO decisions still shown for confirmation, so a warm band keeps being
# measured and cannot drift unobserved. Named here (invariant 6) rather than inline.
# 0.2 is a judgement call: high enough to catch drift within a few dozen decisions,
# low enough that automation still feels like automation.
AUDIT_SAMPLE_RATE = 0.2

# Questions worth putting to a human. `duplicate` is excluded: the local layer genuinely
# cannot answer it without reading the vault, so its answer is not a proposal to adjudicate.
ADJUDICATED = ("bucket", "folder", "area", "actionable")


class Resolution(object):
    """One decision, adjudicated. This is the unit that becomes a label."""

    __slots__ = ("question", "proposed", "chosen", "agreed", "verdict",
                 "confidence", "raw_confidence", "audited", "at", "text")

    def __init__(self, question, proposed, chosen, verdict, confidence,
                 raw_confidence, audited=False, at=None, text=""):
        self.question = question
        self.proposed = proposed
        self.chosen = chosen
        self.agreed = (proposed == chosen)
        self.verdict = verdict
        self.confidence = confidence
        self.raw_confidence = raw_confidence
        self.audited = audited
        self.at = at or time.strftime("%Y-%m-%d %H:%M")
        self.text = text

    def as_dict(self):
        return {
            "at": self.at,
            "question": self.question,
            "proposed": self.proposed,
            "chosen": self.chosen,
            "agreed": self.agreed,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "raw_confidence": self.raw_confidence,
            "audited": self.audited,
            # The capture text is kept for the audit trail. Callers handling sensitive
            # captures should truncate or omit it — see `log_resolution(include_text=...)`.
            "text": self.text,
        }

    def __repr__(self):
        return "Resolution(%s: %s->%s %s)" % (
            self.question, self.proposed, self.chosen,
            "agreed" if self.agreed else "CORRECTED")


class Pending(object):
    """A capture with its proposed decisions, waiting for a human."""

    __slots__ = ("text", "decisions")

    def __init__(self, text, decisions):
        self.text = text
        self.decisions = decisions

    def questions_for_human(self, rng=None):
        """Which questions actually need asking, audit sampling included."""
        out = []
        for q in ADJUDICATED:
            d = self.decisions.get(q)
            if d is None:
                continue
            if needs_human(d) or sample_for_audit(d, rng=rng):
                out.append(q)
        return out


def needs_human(decision):
    """True when the gate escalated. These are the asks."""
    return decision is not None and decision.verdict == gtd.ASK


def sample_for_audit(decision, rng=None):
    """True when an AUTO decision is drawn for confirmation anyway.

    Without this, a warm band stops generating evidence the moment it starts acting, and
    any later drift is invisible. See the module docstring.
    """
    if decision is None or decision.verdict != gtd.AUTO:
        return False
    r = rng if rng is not None else random
    return r.random() < AUDIT_SAMPLE_RATE


# ------------------------------------------------------------------ inbox ----
def parse_inbox(path, heading="收件匣"):
    """Read capture bullets from the GTD inbox note.

    Reads only; never writes. Emptying the inbox is the user's action, not the agent's.
    """
    if not os.path.exists(path):
        return []
    with io.open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()

    lines = raw.splitlines()
    out = []
    collecting = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            collecting = heading in stripped
            continue
        if not collecting:
            continue
        if stripped.startswith(("- ", "* ", "+ ")):
            body = stripped[2:].strip()
            # Skip empty placeholder bullets and checked-off items.
            if body and not body.startswith("[x]"):
                out.append(body.lstrip("[ ]").strip() if body.startswith("[ ]") else body)
    return out


# --------------------------------------------------------------- proposing ----
def propose(text, config, layer=None, kb_index_path=None):
    """Clarify + organize for one capture: ONE jev.decide() call, plus the [C] 知識庫 check.

    Hard rules run first inside `assess` (invariant 5), so a capture that trips a guard
    arrives here already forced to ASK regardless of how confident the layer is.
    """
    layer = layer or gtd.layer_for_env()
    decisions = gtd.assess(text, config, layer)
    decisions["duplicate"] = gtd.duplicate_check(text, kb_index_path)
    return Pending(text, decisions)


# --------------------------------------------------------------- resolving ----
def resolve(layer, pending, question, chosen, log_path=None, audited=False,
            save=True, include_text=True):
    """Record one human adjudication, and teach the layer from it.

    This is the wiring. `gtd.record_outcome` updates the calibration bin for the raw score
    that produced this proposal, using the human's pick as the label.

    Returns a Resolution.
    """
    d = pending.decisions.get(question)
    if d is None:
        raise KeyError("no decision for question %r" % question)

    res = Resolution(
        question=question,
        proposed=d.label,
        chosen=chosen,
        verdict=d.verdict,
        confidence=d.confidence,
        raw_confidence=getattr(d, "raw_confidence", None),
        audited=audited,
        text=pending.text if include_text else "",
    )

    # The label. Everything above is bookkeeping; this line is the point of the module.
    gtd.record_outcome(layer, pending.decisions, question, chosen, save=save)

    if log_path:
        log_resolution(log_path, res)
    return res


def resolve_all(layer, pending, answers, log_path=None, save=True, include_text=True):
    """Resolve several questions at once. `answers` is {question: chosen_label}."""
    out = []
    for question, chosen in answers.items():
        audited = needs_human(pending.decisions.get(question)) is False
        out.append(resolve(layer, pending, question, chosen, log_path=log_path,
                           audited=audited, save=save, include_text=include_text))
    return out


# ------------------------------------------------------------------- audit ----
def log_resolution(path, resolution):
    """Append one resolution to a JSONL audit log. Append-only, like everything else."""
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with io.open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(resolution.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")
    return True


def load_log(path):
    """Read the audit log. A malformed line is skipped, never fatal."""
    if not os.path.exists(path):
        return []
    rows = []
    with io.open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def summarize_log(path, question=None):
    """Agreement rate per question, from the audit log.

    This is the number to look at before trusting the layer: what fraction of its proposals
    a human accepted. It is not the same as calibration accuracy — it counts only
    adjudicated decisions, which is exactly the population that should count.
    """
    rows = load_log(path)
    if question:
        rows = [r for r in rows if r.get("question") == question]
    totals = {}
    for r in rows:
        q = r.get("question", "?")
        agreed, total = totals.get(q, (0, 0))
        totals[q] = (agreed + (1 if r.get("agreed") else 0), total + 1)
    return dict(
        (q, {"agreed": a, "total": t, "rate": (a / float(t)) if t else None})
        for q, (a, t) in totals.items()
    )


# ------------------------------------------------------------------ gating ----
def filing_allowed(config, today=None, consistency=None):
    """Whether decisions may be applied to the vault, or only labelled (shadow mode).

    Filing belongs to Compass's Tasks layer (Build Order days 91-120). Before it opens the
    flow proposes, asks, records, and writes nothing — rule 7's shadow period.
    """
    return unlock.is_unlocked(config, "tasks", today, consistency)
