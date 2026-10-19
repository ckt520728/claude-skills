"""Composite decisions: shapes that one call cannot express.

The hard limit everything here works around: **questions in one request cannot
read each other's answers.** They are evaluated in parallel against one state. So
any decision whose second half depends on the first half's answer is either

  * a DAG of rounds -- `run_plan()`, one call per round, later rounds seeing
    earlier answers;
  * speculation -- `speculative()`, ask every branch in ONE call and discard the
    answers for branches not taken, which is nearly free and has no extra latency;
  * a funnel -- `two_stage_choice()`, coarse family then member, for label sets too
    large for one `Choice`;
  * or a vote -- `ensemble()`, the same judgement asked several ways, where
    disagreement becomes the uncertainty signal.

Reach for speculation before a DAG. A round is a round trip; a speculative
question is a few hundred tokens.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Sequence

from .client import decide
from .types import Answer, Choice, Noul, Question, Result, Score

MAX_CHOICE_OPTIONS = 255


# ---- sequential rounds (a DAG) ----------------------------------------------


@dataclass
class Round:
    """One call in a plan.

    `state` builds this round's state from the original input plus every answer so
    far -- that is how a later round reads an earlier one's verdict. `when` skips
    the round entirely, which is what makes a plan a DAG rather than a chain.
    """

    name: str
    questions: Mapping[str, Question] | Callable[[dict[str, Any], dict[str, Answer]], Mapping[str, Question]]
    state: Callable[[dict[str, Any], dict[str, Answer]], Mapping[str, Any]] | None = None
    when: Callable[[dict[str, Any], dict[str, Answer]], bool] | None = None


@dataclass
class PlanResult:
    answers: dict[str, Answer] = field(default_factory=dict)
    rounds_run: list[str] = field(default_factory=list)
    rounds_skipped: list[str] = field(default_factory=list)
    calls: int = 0
    input_tokens: int = 0
    latency_ms: float = 0.0
    results: list[Result] = field(default_factory=list)

    def __getitem__(self, qid: str) -> Answer:
        return self.answers[qid]

    def get(self, qid: str, default: Any = None) -> Any:
        return self.answers.get(qid, default)


def run_plan(
    base_state: Mapping[str, Any],
    rounds: Sequence[Round],
    **decide_kwargs: Any,
) -> PlanResult:
    """Run a DAG of decision rounds, each seeing every earlier answer.

        plan = [
            Round("triage", {"kind": Choice(...)}),
            Round(
                "deep",
                questions={"severity": Score(...)},
                when=lambda s, a: a["kind"].choice == "bug",
                state=lambda s, a: {**s, "classified_as": a["kind"].choice},
            ),
        ]
        out = run_plan({"issue": issue}, plan)

    Question ids must be unique across the whole plan -- a later round overwriting
    an earlier answer silently is the bug this refuses to have.
    """
    out = PlanResult()
    state = dict(base_state)

    for rnd in rounds:
        if rnd.when and not rnd.when(state, out.answers):
            out.rounds_skipped.append(rnd.name)
            continue

        questions = rnd.questions(state, out.answers) if callable(rnd.questions) else rnd.questions
        if not questions:
            out.rounds_skipped.append(rnd.name)
            continue

        if clash := set(questions) & set(out.answers):
            raise ValueError(
                f"round {rnd.name!r} reuses question id(s) {sorted(clash)} already answered. "
                f"Ids must be unique across a plan so no answer is silently overwritten."
            )

        round_state = dict(rnd.state(state, out.answers)) if rnd.state else state
        result = decide(round_state, questions, **decide_kwargs)

        out.answers.update(result.answers)
        out.rounds_run.append(rnd.name)
        out.calls += 1
        out.input_tokens += result.input_tokens
        out.latency_ms += result.latency_ms
        out.results.append(result)

    return out


# ---- speculation ------------------------------------------------------------


def speculative(
    state: Mapping[str, Any],
    shared: Mapping[str, Question],
    branches: Mapping[str, Mapping[str, Question]],
    *,
    select: Callable[[dict[str, Answer]], str],
    **decide_kwargs: Any,
) -> tuple[str, dict[str, Answer], Result]:
    """Ask about every branch in one call, then use only the branch you take.

    This is the cheap way to avoid a second round trip. The unused answers cost
    their own tokens and nothing else -- no extra state transfer, no extra latency
    worth measuring.

        branch, answers, result = speculative(
            state,
            shared={"route": Choice(instructions="...", criteria={"refund":..., "replace":...})},
            branches={
                "refund":  {"refund_amount_ok": Noul(instructions="...")},
                "replace": {"stock_available": Noul(instructions="...")},
            },
            select=lambda a: a["route"].choice,
        )

    Returns (branch taken, shared answers plus that branch's answers, raw result).
    """
    questions: dict[str, Question] = dict(shared)
    prefixed: dict[str, dict[str, str]] = {}

    for branch, branch_questions in branches.items():
        prefixed[branch] = {}
        for qid, question in branch_questions.items():
            key = f"{branch}__{qid}"
            if key in questions:
                raise ValueError(f"speculative question id collision on {key!r}.")
            questions[key] = question
            prefixed[branch][key] = qid

    result = decide(state, questions, **decide_kwargs)

    shared_answers = {qid: result.answers[qid] for qid in shared}
    branch = select(shared_answers)
    if branch not in branches:
        return branch, shared_answers, result

    taken = dict(shared_answers)
    for key, qid in prefixed[branch].items():
        taken[qid] = result.answers[key]
    return branch, taken, result


# ---- high-cardinality funnel ------------------------------------------------


def two_stage_choice(
    state: Mapping[str, Any],
    families: Mapping[str, str],
    members: Mapping[str, Mapping[str, str]],
    *,
    instructions: str,
    member_instructions: str | None = None,
    tau: float = 0.85,
    **decide_kwargs: Any,
) -> tuple[Optional[str], Optional[str], float, str]:
    """Coarse family, then member. For label sets a single `Choice` handles badly.

    Above roughly 30 options a flat `Choice` degrades; above 255 it is unavailable.
    Two calls are markedly more accurate than one wide one -- and if the family is
    uncertain the second call is skipped, so an ambiguous item costs one call, not
    two.

    Returns (family, member, member_confidence, reason). Either may be None.
    """
    fam = dict(families)
    fam.setdefault("other", "None of the families fits.")

    first = decide(state, {"family": Choice(instructions=instructions, criteria=fam)}, **decide_kwargs)
    family_answer = first.answers["family"]
    family = str(family_answer.choice or "other")
    family_confidence = float(family_answer.confidence or 0.0)

    if family == "other" or family_confidence < tau:
        return (None, None, family_confidence,
                f"family uncertain ({family} at {family_confidence:.2f} < {tau}) -- not narrowing further")

    pool = dict(members.get(family) or {})
    if not pool:
        return (family, None, family_confidence, f"family {family} at {family_confidence:.2f}, no members defined")
    pool.setdefault("other", "None of the members fits.")

    second = decide(
        {**state, "selected_family": family},
        {"member": Choice(
            instructions=member_instructions or f"{instructions} The family is already known to be '{family}'.",
            criteria=pool,
        )},
        **decide_kwargs,
    )
    member_answer = second.answers["member"]
    member = str(member_answer.choice or "other")
    member_confidence = float(member_answer.confidence or 0.0)

    if member == "other" or member_confidence < tau:
        return (family, None, member_confidence,
                f"family {family} at {family_confidence:.2f}, member uncertain "
                f"({member} at {member_confidence:.2f})")
    return (family, member, member_confidence,
            f"{family}/{member} at {family_confidence:.2f}/{member_confidence:.2f}")


def shortlist_then_choose(
    state: Mapping[str, Any],
    candidates: Mapping[str, str],
    *,
    score_instructions: str,
    choose_instructions: str,
    keep: int = 8,
    score_levels: Sequence[str] = ("Clearly not a fit", "Possible", "Strong fit"),
    **decide_kwargs: Any,
) -> tuple[Optional[str], float, list[tuple[str, float]]]:
    """Score every candidate in one call, then `Choice` over the best few.

    The pattern for high cardinality when the candidates are heterogeneous enough
    that a family tree does not fit. Filter obvious mismatches in code first -- you
    are paying per candidate.
    """
    if not candidates:
        return None, 0.0, []

    scored = decide(
        {**state, "candidates": dict(candidates)},
        {f"score__{key}": Score(instructions=f"{score_instructions} Candidate: {desc}",
                                criteria=list(score_levels))
         for key, desc in candidates.items()},
        **decide_kwargs,
    )
    ranking = sorted(
        ((key, float(scored.answers[f"score__{key}"].score or 0.0)) for key in candidates),
        key=lambda t: -t[1],
    )
    top = [k for k, _ in ranking[:keep]]
    if len(top) == 1:
        return top[0], float(scored.answers[f"score__{top[0]}"].confidence or 0.0), ranking

    final = decide(
        state,
        {"pick": Choice(
            instructions=choose_instructions,
            criteria={**{k: candidates[k] for k in top}, "other": "None of the shortlist fits."},
        )},
        **decide_kwargs,
    )
    answer = final.answers["pick"]
    pick = None if answer.choice == "other" else str(answer.choice)
    return pick, float(answer.confidence or 0.0), ranking


# ---- ensembles --------------------------------------------------------------


@dataclass(frozen=True)
class EnsembleVerdict:
    winner: Optional[str]
    agreement: float
    mean_confidence: float
    votes: dict[str, int]
    per_variant: dict[str, tuple[Optional[str], float]]
    reason: str

    @property
    def unanimous(self) -> bool:
        return self.agreement >= 1.0


def ensemble(
    state: Mapping[str, Any],
    variants: Mapping[str, Choice],
    *,
    tau_agreement: float = 0.75,
    **decide_kwargs: Any,
) -> EnsembleVerdict:
    """Ask the same judgement several ways in ONE call and vote.

    The point is not accuracy, it is a *second* uncertainty signal. Confidence tells
    you how peaked one distribution is; agreement across rephrasings tells you
    whether the verdict survives the wording. They fail differently -- and the case
    the decision layer handles worst, an elaborately written wrong answer, is one
    where confidence stays high. Disagreement catches some of what confidence misses.

    Variants must use the SAME option keys. Rephrase the instructions and the
    criteria text, not the label set.

    `tau_agreement` defaults to 0.75, which for three variants means unanimity.
    A 2-of-3 majority passing would make the signal nearly free to satisfy and
    defeat the point -- raise coverage by adding variants, not by lowering the bar.
    """
    if len(variants) < 2:
        raise ValueError("An ensemble needs at least two variants.")
    keysets = {frozenset(v.criteria) for v in variants.values()}
    if len(keysets) != 1:
        raise ValueError("All ensemble variants must offer the same option keys.")

    result = decide(state, dict(variants), **decide_kwargs)

    per_variant: dict[str, tuple[Optional[str], float]] = {}
    for name in variants:
        answer = result.answers[name]
        per_variant[name] = (answer.choice, float(answer.confidence or 0.0))

    votes = Counter(choice for choice, _ in per_variant.values() if choice)
    if not votes:
        return EnsembleVerdict(None, 0.0, 0.0, {}, per_variant, "no variant returned a label")

    winner, count = votes.most_common(1)[0]
    agreement = count / len(variants)
    mean_confidence = sum(c for _, c in per_variant.values()) / len(per_variant)

    if agreement < tau_agreement:
        return EnsembleVerdict(
            None, agreement, mean_confidence, dict(votes), per_variant,
            f"rephrasings disagree ({dict(votes)}, agreement {agreement:.2f} < {tau_agreement}) "
            f"-- escalate even though mean confidence is {mean_confidence:.2f}",
        )
    return EnsembleVerdict(
        winner, agreement, mean_confidence, dict(votes), per_variant,
        f"{winner} with {agreement:.2f} agreement, mean confidence {mean_confidence:.2f}",
    )


def debiased_pairwise(
    question: str,
    candidate_a: str,
    candidate_b: str,
    *,
    instructions: str,
    tie_label: str | None = "tie",
    **decide_kwargs: Any,
) -> tuple[str, float, dict[str, float]]:
    """Judge a pair in BOTH orders in ONE call and average the aligned probabilities.

    Position bias is real and this removes it for the price of a second question
    rather than a second call. Gate on the returned q, never on either presentation.
    """
    criteria = {"a": "The first response is better.", "b": "The second response is better."}
    if tie_label:
        criteria[tie_label] = "Neither is clearly better."

    result = decide(
        {"question": question, "forward": {"first": candidate_a, "second": candidate_b},
         "reversed": {"first": candidate_b, "second": candidate_a}},
        {
            "forward": Choice(instructions=f"{instructions} Judge the pair under `forward`.",
                              criteria=criteria, exit_option=tie_label or "a"),
            "reversed": Choice(instructions=f"{instructions} Judge the pair under `reversed`.",
                               criteria=criteria, exit_option=tie_label or "a"),
        },
        **decide_kwargs,
    )

    fwd = result.answers["forward"].probabilities
    rev = result.answers["reversed"].probabilities
    aligned = {
        "a": (fwd.get("a", 0.0) + rev.get("b", 0.0)) / 2,
        "b": (fwd.get("b", 0.0) + rev.get("a", 0.0)) / 2,
    }
    if tie_label:
        aligned[tie_label] = (fwd.get(tie_label, 0.0) + rev.get(tie_label, 0.0)) / 2
    total = sum(aligned.values())
    if total > 0:
        aligned = {k: v / total for k, v in aligned.items()}
    verdict = max(aligned, key=aligned.get)
    return verdict, aligned[verdict], aligned
