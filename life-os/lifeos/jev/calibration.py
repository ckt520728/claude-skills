"""Calibration: the machinery that makes a confidence number mean something.

`SKILL.md` makes a specific claim about confidence:

    it is *calibrated*: across many calls, higher confidence means higher accuracy.

For the `jev` provider that property is the vendor's to uphold. For any provider you supply
yourself -- `local`, or `llm`, whose self-reported probabilities are known to be overconfident
-- it is yours, and nothing enforces it unless you measure it. This module is the measurement.

Histogram binning: group observations by the raw score the scorer produced, and report each
bin's *observed* accuracy as the confidence for that band. Simple, stdlib, and auditable --
you can read the reliability table and see exactly why a band is trusted.

**How it degrades is the load-bearing part.** With too few observations a bin returns
`COLD_CONFIDENCE`, which sits below any sane gate, so an untuned layer asks about everything
and acts on nothing. It earns the right to act as evidence accumulates. That makes rule 7's
shadow period structural rather than a discipline someone has to remember:

    rule 7 -- Run a period where the decision layer labels and the old path still decides;
              switch on the confidence bands that matched.

Every escalation a human resolves is one labelled example. The shadow period stops being a
phase you run and finish, and becomes how the layer works.

See `references/10-threshold-tuning.md`.
"""

from __future__ import annotations

import json
import os
from typing import Any, Iterable, Sequence

__all__ = [
    "BINS",
    "MIN_OBSERVATIONS",
    "COLD_CONFIDENCE",
    "Calibrator",
    "brier_score",
    "expected_calibration_error",
]

# Equal-width bins over [0, 1]. Equal-width rather than equal-mass because the reliability
# table is meant to be read by a human, and "0.7-0.8" is legible where "the 7th decile of
# observed scores" is not.
BINS = 10

# Below this many observations, a bin cannot claim to know its own accuracy. A judgement
# call, not a result: small enough to start acting within a couple of weeks of daily use,
# large enough that one lucky run does not unlock automation.
MIN_OBSERVATIONS = 12

# Deliberately low. Must sit below every gate in your policy so a cold layer escalates.
COLD_CONFIDENCE = 0.30


def _bin_index(p: float | None) -> int:
    if p is None:
        return 0
    idx = int(p * BINS)
    return BINS - 1 if idx >= BINS else (0 if idx < 0 else idx)


def _bin_label(i: int) -> str:
    return f"{i / BINS:.1f}-{(i + 1) / BINS:.1f}"


class Calibrator:
    """Per-question histogram calibration, persisted as JSON you own.

    Each question id calibrates separately. One global mapping would let an easy question
    lend its accuracy to a hard one, which is exactly the failure that makes a confidence
    number untrustworthy -- and it is invisible unless you separate them.
    """

    def __init__(self, path: str | None = None, data: dict[str, dict[int, list[int]]] | None = None):
        self.path = path
        # {question_id: {bin_index: [n_correct, n_total]}}
        self.data: dict[str, dict[int, list[int]]] = data or {}

    # -- persistence ----------------------------------------------------
    @classmethod
    def load(cls, path: str | None) -> "Calibrator":
        """Read from disk. A corrupt or absent file starts cold rather than raising.

        Failing to `ask` is the safe direction (SKILL.md: hooks fail to ask, never to allow),
        and a calibration file is exactly the kind of thing that gets half-written when a
        process is killed.
        """
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                data = {
                    qid: {int(k): list(v) for k, v in bins.items()}
                    for qid, bins in (raw.get("questions") or {}).items()
                }
                return cls(path=path, data=data)
            except (ValueError, OSError, TypeError, AttributeError):
                return cls(path=path)
        return cls(path=path)

    def save(self) -> bool:
        if not self.path:
            return False
        payload: dict[str, Any] = {
            "version": 1,
            "bins": BINS,
            "min_observations": MIN_OBSERVATIONS,
            "questions": {
                qid: {str(k): v for k, v in bins.items()} for qid, bins in self.data.items()
            },
        }
        parent = os.path.dirname(self.path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        with open(self.path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return True

    # -- learning -------------------------------------------------------
    def observe(self, question_id: str, raw_confidence: float, was_correct: bool) -> list[int]:
        """Record one labelled outcome. The only way the layer learns anything."""
        bins = self.data.setdefault(question_id, {})
        cell = bins.setdefault(_bin_index(raw_confidence), [0, 0])
        cell[1] += 1
        if was_correct:
            cell[0] += 1
        return cell

    def observations(self, question_id: str | None = None) -> int:
        if question_id is not None:
            return sum(c[1] for c in (self.data.get(question_id) or {}).values())
        return sum(c[1] for bins in self.data.values() for c in bins.values())

    # -- the mapping ----------------------------------------------------
    def calibrate(self, question_id: str, raw_confidence: float) -> float:
        """Map a raw score onto observed accuracy, or COLD_CONFIDENCE if too sparse."""
        cell = (self.data.get(question_id) or {}).get(_bin_index(raw_confidence))
        if not cell or cell[1] < MIN_OBSERVATIONS:
            return COLD_CONFIDENCE
        # Laplace smoothing: a bin that is 12/12 must not claim 1.00.
        return (cell[0] + 1.0) / (cell[1] + 2.0)

    def is_warm(self, question_id: str, raw_confidence: float) -> bool:
        cell = (self.data.get(question_id) or {}).get(_bin_index(raw_confidence))
        return bool(cell and cell[1] >= MIN_OBSERVATIONS)

    # -- reporting ------------------------------------------------------
    def reliability(self, question_id: str) -> list[tuple[str, int, float, bool]]:
        """Rows of (band, n, observed_accuracy, warm). This is the audit artefact."""
        bins = self.data.get(question_id) or {}
        rows = []
        for i in range(BINS):
            cell = bins.get(i)
            if not cell or cell[1] == 0:
                continue
            rows.append((_bin_label(i), cell[1], cell[0] / cell[1], cell[1] >= MIN_OBSERVATIONS))
        return rows

    def report(self, question_id: str) -> str:
        n = self.observations(question_id)
        if n == 0:
            return f"{question_id}: cold (0 observations) -- every decision escalates"
        rows = self.reliability(question_id)
        warm = sum(1 for r in rows if r[3])
        return f"{question_id}: {n} observations, {warm}/{len(rows)} bins warm"


def brier_score(pairs: Sequence[tuple[float | None, bool]]) -> float | None:
    """Mean squared error of probabilistic predictions. Lower is better; 0.25 is a coin flip."""
    usable = [(p, c) for p, c in pairs if p is not None]
    if not usable:
        return None
    return sum((p - (1.0 if c else 0.0)) ** 2 for p, c in usable) / len(usable)


def expected_calibration_error(pairs: Iterable[tuple[float | None, bool]]) -> float | None:
    """Weighted mean gap between stated confidence and observed accuracy.

    The number that answers "does my confidence mean anything". Near 0 says a stated 0.8 is
    right about 80% of the time. At 0.3 the number is decorative, and a gate built on it is
    not a gate -- which is the failure mode this whole module exists to make visible.

    Note it penalises *under*-confidence too. A layer that says 0.30 while being right 100%
    of the time scores badly here and is nonetheless safe: it escalates. Read ECE alongside
    the reliability table rather than on its own.
    """
    usable = [(p, c) for p, c in pairs if p is not None]
    if not usable:
        return None
    buckets: dict[int, list[tuple[float, bool]]] = {}
    for p, correct in usable:
        buckets.setdefault(_bin_index(p), []).append((p, correct))
    total = len(usable)
    ece = 0.0
    for items in buckets.values():
        conf = sum(p for p, _ in items) / len(items)
        acc = sum(1.0 for _, c in items if c) / len(items)
        ece += (len(items) / total) * abs(conf - acc)
    return ece
