"""The confidence gate: turning belief into an action.

The model reports belief and certainty. Turning that into an action is business
logic, and keeping the split is what makes the system auditable later -- so the
thresholds live here, in your code, named and tunable, rather than inside a
prompt or a middleware default.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable, Mapping, TypeVar

from .types import EXIT_OPTION, Answer

T = TypeVar("T")


class Exit(str, Enum):
    """The four exits. A gate with only ACT and ABSTAIN throws away most of the value."""

    ACT = "act"           # confident, and the action is cheap to undo
    ESCALATE = "escalate"  # uncertain, and a better answer is purchasable
    HUMAN = "human"        # policy, regardless of confidence
    ABSTAIN = "abstain"    # uncertain, and no better answer is available in budget


@dataclass(frozen=True)
class Decision:
    exit: Exit
    label: str | float | None
    certainty: float
    reason: str

    def __bool__(self) -> bool:
        return self.exit is Exit.ACT


def gate(
    answer: Answer,
    *,
    tau_act: float = 0.90,
    tau_ask: float = 0.50,
    policy_flags: Iterable[bool] = (),
    policy_reason: str = "policy: irreversible, costs money, or externally visible",
    exit_option: str = EXIT_OPTION,
) -> Decision:
    """Route one answer to one of the four exits.

    `policy_flags` beats confidence unconditionally. Anything irreversible,
    anything that costs money, and anything externally visible gets a human
    regardless of how certain the classifier was -- that is a policy in code,
    not a vibe in a prompt.

    `tau_act` comes from the cost of a wrong action; `tau_ask` from your
    escalation budget. Do not share one tau across actions with different blast
    radii -- see thresholds_for_actions() below.
    """
    certainty = answer.certainty

    if any(policy_flags):
        return Decision(Exit.HUMAN, answer.value, certainty, policy_reason)

    if answer.type == "choice" and answer.choice == exit_option:
        return Decision(
            Exit.HUMAN, answer.choice, certainty,
            f"'{exit_option}' is an exit, not a bucket -- out-of-distribution input",
        )

    if certainty >= tau_act:
        return Decision(Exit.ACT, answer.value, certainty, f"certainty {certainty:.2f} >= {tau_act}")
    if certainty >= tau_ask:
        return Decision(
            Exit.ESCALATE, answer.value, certainty,
            f"certainty {certainty:.2f} in [{tau_ask}, {tau_act}) -- buy a better answer",
        )
    return Decision(
        Exit.ABSTAIN, answer.value, certainty,
        f"certainty {certainty:.2f} < {tau_ask} -- no answer is better than a guess",
    )


def cascade(
    answer: Answer,
    *,
    tau: float = 0.90,
    fallback: Callable[[], T],
    accept: Callable[[Answer], T] | None = None,
) -> T:
    """Accept when confident, escalate when unsure.

    `fallback` is called only when certainty < tau, so the expensive path costs
    nothing on the accepted majority. Expect roughly a third of in-envelope
    traffic to escalate at tau=0.90, and more than half on harder traffic.

    If the escalation path never fires, tau is too loose and you have quietly
    built an unsupervised system.
    """
    if answer.certainty >= tau:
        return accept(answer) if accept else answer.value  # type: ignore[return-value]
    return fallback()


def thresholds_for_actions(table: Mapping[str, float]) -> Callable[[Answer], Decision]:
    """Per-label thresholds, because blast radius differs within one question.

        route = thresholds_for_actions({
            "read_only":   0.70,
            "local_edit":  0.85,
            "destructive": 0.95,
            "external":    1.01,   # unreachable on purpose: always a human
            "other":       1.01,
        })
        decision = route(result.answers["risk"])

    Keeping the always-escalate cases in the same table as the thresholds beats
    a special case somewhere else in the file.
    """

    def _route(answer: Answer) -> Decision:
        label = str(answer.value)
        tau_act = table.get(label, 1.01)
        return gate(answer, tau_act=tau_act, tau_ask=0.0)

    return _route


def aligned_pairwise(
    probs_ab: Mapping[str, float],
    probs_ba: Mapping[str, float],
    *,
    a: str = "a",
    b: str = "b",
    tie: str | None = "tie",
) -> tuple[str, float, dict[str, float]]:
    """Average a pairwise judgement across both candidate orders.

    Position bias is real and removing it costs one extra call at hundredths of
    a cent. Gate on the returned q, never on either single call's confidence.

    Returns (verdict, q, aligned_probabilities).
    """
    aligned = {
        a: (probs_ab.get(a, 0.0) + probs_ba.get(b, 0.0)) / 2,
        b: (probs_ab.get(b, 0.0) + probs_ba.get(a, 0.0)) / 2,
    }
    if tie:
        aligned[tie] = (probs_ab.get(tie, 0.0) + probs_ba.get(tie, 0.0)) / 2
    total = sum(aligned.values())
    if total > 0:
        aligned = {k: v / total for k, v in aligned.items()}
    verdict = max(aligned, key=aligned.get)
    return verdict, aligned[verdict], aligned
