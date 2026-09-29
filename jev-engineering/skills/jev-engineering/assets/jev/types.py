"""Typed question primitives and answers for a System One decision layer.

Three primitives, matching the documented wire format:

    Choice  -> one of N options   (returns choice, probabilities, confidence)
    Score   -> an ordered rubric  (returns fractional score, probabilities, confidence)
    Noul    -> a yes/no statement (returns a probability; NO confidence field)

Rule 1 lives here as validation, not as advice: the question id never reaches
the model, so anything the model needs must be in `instructions` or `criteria`.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence, Union

MAX_CHOICE_OPTIONS = 255
MIN_SCORE_LEVELS = 2
MAX_SCORE_LEVELS = 10

# Conventional exit option (rule 4). Never auto-approve this label.
EXIT_OPTION = "other"


class QuestionSpecError(ValueError):
    """A question was specified in a way the decision layer cannot use well."""


def _check_instructions(instructions: str, where: str) -> None:
    if not instructions or not instructions.strip():
        raise QuestionSpecError(
            f"{where}: instructions are required. The question id is never sent to the "
            f"model, so an empty instruction means the model is told nothing (rule 1)."
        )
    if len(instructions.strip()) < 12:
        warnings.warn(
            f"{where}: instructions are very short ({instructions!r}). Describe the "
            f"situation to judge, not a mood (rule 3).",
            stacklevel=3,
        )


@dataclass(frozen=True)
class Choice:
    """Select one option from a defined set (up to 255).

    `exit_option` names the option that means "none of these fits" (rule 4). It
    defaults to "other"; set it when the natural exit has a domain name -- a
    pairwise judgement's "tie", a triage queue's "needs-human". Whatever it is
    named, never auto-approve it: it exists to route the unknown to a person.
    """

    instructions: str
    criteria: Mapping[str, str]
    exit_option: str = EXIT_OPTION

    def __post_init__(self) -> None:
        _check_instructions(self.instructions, "Choice")
        n = len(self.criteria)
        if n < 2:
            raise QuestionSpecError(f"Choice needs at least 2 options, got {n}.")
        if n > MAX_CHOICE_OPTIONS:
            raise QuestionSpecError(
                f"Choice supports at most {MAX_CHOICE_OPTIONS} options, got {n}. "
                f"Filter in code, Score the survivors, then Choice over the shortlist."
            )
        for key, text in self.criteria.items():
            if not text or not str(text).strip():
                raise QuestionSpecError(
                    f"Choice option {key!r} has no criteria text. The option name carries "
                    f"no meaning for the model; the decision lives in this text (rule 1)."
                )
        if self.exit_option not in self.criteria:
            warnings.warn(
                f"Choice has no {self.exit_option!r} exit option. Without one, "
                f"out-of-distribution inputs are forced into a real bucket and uncertainty "
                f"is hidden (rule 4). Pass exit_option= if yours has another name.",
                stacklevel=3,
            )

    def to_wire(self) -> dict[str, Any]:
        return {
            "type": "choice",
            "instructions": self.instructions,
            "criteria": {str(k): str(v) for k, v in self.criteria.items()},
        }


@dataclass(frozen=True)
class Score:
    """Rate state against 2-10 ordered, described levels.

    `criteria` must be ordered worst -> best (or low -> high). The returned score
    is probability-weighted across levels, so it is fractional in 0..len-1.
    """

    instructions: str
    criteria: Sequence[str]

    def __post_init__(self) -> None:
        _check_instructions(self.instructions, "Score")
        n = len(self.criteria)
        if not (MIN_SCORE_LEVELS <= n <= MAX_SCORE_LEVELS):
            raise QuestionSpecError(
                f"Score needs {MIN_SCORE_LEVELS}-{MAX_SCORE_LEVELS} levels, got {n}."
            )
        for i, level in enumerate(self.criteria):
            text = str(level).strip()
            if not text:
                raise QuestionSpecError(f"Score level {i} has no description.")
            if text.replace(".", "").isdigit():
                raise QuestionSpecError(
                    f"Score level {i} is the bare number {text!r}. Bare numeric levels "
                    f"strip the rubric of meaning; describe the situation (rule 3)."
                )

    @property
    def max_score(self) -> float:
        return float(len(self.criteria) - 1)

    def to_wire(self) -> dict[str, Any]:
        return {
            "type": "score",
            "instructions": self.instructions,
            "criteria": [str(c) for c in self.criteria],
        }


@dataclass(frozen=True)
class Noul:
    """A yes/no statement. Returns the probability the statement is true.

    Phrase `instructions` as a statement to be judged true, not as a question:
    "Every deliverable named in the goal now exists." reads better to the model
    than "Are the deliverables done?".
    """

    instructions: str
    criteria: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        _check_instructions(self.instructions, "Noul")

    def to_wire(self) -> dict[str, Any]:
        wire: dict[str, Any] = {"type": "noul", "instructions": self.instructions}
        if self.criteria:
            wire["criteria"] = {str(k): str(v) for k, v in self.criteria.items()}
        return wire


Question = Union[Choice, Score, Noul]


@dataclass(frozen=True)
class Answer:
    """One answer, keyed by your question id.

    `certainty` normalises across primitives so a single gate can consume any of
    them -- but see the warning on `certainty`: a derived Noul certainty is NOT
    on the same scale as a native Choice confidence.
    """

    id: str
    type: str
    choice: str | None = None
    score: float | None = None
    noul: float | None = None
    confidence: float | None = None
    probabilities: dict[str, float] = field(default_factory=dict)

    @property
    def value(self) -> Any:
        """The answer itself, whatever its primitive."""
        if self.type == "choice":
            return self.choice
        if self.type == "score":
            return self.score
        return self.noul

    @property
    def certainty(self) -> float:
        """A 0-1 certainty usable by a shared gate.

        For Choice/Score this is the provider's native `confidence`. For a Noul
        there is no confidence field, so this is DERIVED as abs(noul-0.5)*2 --
        your statistic, on a different scale. Tune Noul thresholds separately;
        reusing a Choice threshold here is a silent mis-set.
        """
        if self.type == "noul":
            if self.noul is None:
                return 0.0
            return abs(self.noul - 0.5) * 2.0
        if self.confidence is not None:
            return float(self.confidence)
        # Fall back to max label probability, which correlates with the native
        # value at Spearman 0.95-0.999 and is the standard q = max_k p_k.
        return max(self.probabilities.values()) if self.probabilities else 0.0

    @property
    def q(self) -> float:
        """Max label probability. The literature's confidence signal."""
        return max(self.probabilities.values()) if self.probabilities else self.certainty

    @classmethod
    def from_wire(cls, qid: str, wire: Mapping[str, Any]) -> "Answer":
        probs = wire.get("probabilities") or {}
        return cls(
            id=qid,
            type=str(wire.get("type", "")),
            choice=wire.get("choice"),
            score=None if wire.get("score") is None else float(wire["score"]),
            noul=None if wire.get("noul") is None else float(wire["noul"]),
            confidence=None if wire.get("confidence") is None else float(wire["confidence"]),
            probabilities={str(k): float(v) for k, v in probs.items()},
        )


# Vendor-listed price: $0.042 per million input tokens, output free.
USD_PER_INPUT_TOKEN = 0.042 / 1_000_000


@dataclass(frozen=True)
class Result:
    """One decision call. `answers` is keyed by your question ids."""

    model: str
    answers: dict[str, Answer]
    usage: dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    provider: str = "jev"
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def input_tokens(self) -> int:
        return int(self.usage.get("input_tokens", 0))

    @property
    def cost_usd(self) -> float:
        """Cost of this call at the listed input-token rate. Output is free."""
        return self.input_tokens * USD_PER_INPUT_TOKEN

    def __getitem__(self, qid: str) -> Answer:
        return self.answers[qid]

    @classmethod
    def from_wire(
        cls,
        wire: Mapping[str, Any],
        *,
        latency_ms: float = 0.0,
        provider: str = "jev",
    ) -> "Result":
        answers = {
            qid: Answer.from_wire(qid, spec)
            for qid, spec in (wire.get("answers") or {}).items()
        }
        return cls(
            model=str(wire.get("model", "")),
            answers=answers,
            usage={str(k): int(v) for k, v in (wire.get("usage") or {}).items()},
            latency_ms=latency_ms,
            provider=provider,
            raw=dict(wire),
        )
