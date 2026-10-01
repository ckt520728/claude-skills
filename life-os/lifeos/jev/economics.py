"""Economics of a routed stack: expected cost per COMPLETED task.

Cost per call is the number that flatters a router. Cost per completed task is
the number that judges it, because a cheap decision that sends work down the
wrong branch pays for the retry as well as the mistake.

    compare_policies()   always-high vs always-low vs routed, per completed task
    expected_task_cost() cost of a tier chain including escalation on failure
    cascade_economics()  fee ratio and break-even escalation rate for a judge cascade
    loop_overhead()      what a decision layer removes from an overnight loop

Every function takes success rates as inputs and never invents them. Measure them
on your own traffic -- `references/10-threshold-tuning.md` is how -- because a
routing policy evaluated against guessed success rates is a spreadsheet, not a
measurement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

from .routing import TIER_ORDER, Model, Registry, RegistryError

# Vendor-listed decision-layer price. See UNKNOWNS.md: not confirmed by direct fetch.
DECISION_USD_PER_MTOK = 0.042


@dataclass(frozen=True)
class TierProfile:
    """What a tier costs and how often it finishes the job unaided.

    `success_rate` is the share of tasks this tier completes CORRECTLY, judged by
    whatever gate you actually use -- tests passing, a reviewer accepting, an eval
    verdict. It is not a benchmark score.
    """

    tier: str
    model: Model
    success_rate: float
    input_mtok: float = 0.02
    output_mtok: float = 0.004
    cached_mtok: float = 0.0
    # Share of this tier's failures that a plain retry at the SAME tier fixes.
    # Deliberately low: most failures are capability, not luck, and a tier that
    # cannot do a task does not start being able to on the third attempt. Setting
    # this near 1.0 is what makes a weak tier look artificially cheap.
    retry_recovery: float = 0.25

    @property
    def call_usd(self) -> float:
        return self.model.cost_usd(
            input_mtok=self.input_mtok, output_mtok=self.output_mtok, cached_mtok=self.cached_mtok
        )


@dataclass(frozen=True)
class PolicyCost:
    name: str
    usd_per_completed_task: float
    expected_calls: float
    escalation_share: float
    completion_rate: float
    detail: str

    def __str__(self) -> str:
        return (f"{self.name:<26} ${self.usd_per_completed_task:.5f}/task  "
                f"{self.expected_calls:.2f} calls  {self.escalation_share*100:5.1f}% escalated  "
                f"{self.completion_rate*100:5.1f}% completed")


def expected_task_cost(
    chain: Sequence[TierProfile],
    *,
    decision_usd: float = 0.0,
    max_attempts_at_top: int = 3,
) -> tuple[float, float, float, float]:
    """Expected cost, calls, escalation share, and COMPLETION RATE for a tier chain.

    The chain is walked weakest-first: each tier is attempted once, and the work
    only reaches the next tier if this one failed. The final tier retries up to
    `max_attempts_at_top` times because there is nowhere left to escalate to --
    but each retry succeeds at `retry_recovery` of the previous attempt's rate,
    since most failures are capability rather than luck.

    That decay is the whole reason this function exists. Treating retries as
    independent coin flips makes a weak tier look cheap, because on paper it
    eventually succeeds; in practice it eventually gives up. Completion rate is
    returned separately rather than only folded into the denominator, so a policy
    that leaves a third of tasks unfinished cannot present as the cheap option.

    Returns (usd_per_completed_task, expected_calls, escalation_share, completion_rate).
    """
    if not chain:
        raise ValueError("expected_task_cost needs at least one tier in the chain.")

    reach = 1.0          # probability the work is still unfinished at this stage
    cost = decision_usd
    calls = 0.0
    completed = 0.0
    escalated_mass = 0.0

    for i, profile in enumerate(chain[:-1]):
        cost += reach * profile.call_usd
        calls += reach
        completed += reach * profile.success_rate
        reach *= 1.0 - profile.success_rate
        if i == 0:
            escalated_mass = reach

    top = chain[-1]
    p = min(1.0, max(0.0, top.success_rate))
    for _ in range(max(1, max_attempts_at_top)):
        cost += reach * top.call_usd
        calls += reach
        completed += reach * p
        reach *= 1.0 - p
        p *= top.retry_recovery      # a retry is markedly less likely to land

    completion = max(1e-9, completed)
    return cost / completion, calls, (escalated_mass if len(chain) > 1 else 0.0), completion


def compare_policies(
    profiles: Mapping[str, TierProfile],
    *,
    routed_tier_mix: Mapping[str, float],
    router_accuracy: float = 0.90,
    decision_input_mtok: float = 0.001,
    max_attempts_at_top: int = 3,
) -> list[PolicyCost]:
    """The table that decides whether routing was worth building.

    `routed_tier_mix` is the share of your traffic that genuinely belongs in each
    tier -- measured by labelling real requests, not guessed. `router_accuracy` is
    how often the router puts a task in the right tier; a misroute downward costs
    a wasted attempt plus the correct tier afterwards, which is the whole risk.

    Returns one row per policy, cheapest first.
    """
    for tier in routed_tier_mix:
        if tier not in profiles:
            raise ValueError(f"routed_tier_mix names tier {tier!r} with no profile.")
    total = sum(routed_tier_mix.values())
    if total <= 0:
        raise ValueError("routed_tier_mix must sum to something positive.")
    mix = {k: v / total for k, v in routed_tier_mix.items()}

    ordered = [profiles[t] for t in TIER_ORDER if t in profiles]
    decision_usd = decision_input_mtok * DECISION_USD_PER_MTOK

    rows: list[PolicyCost] = []

    # Single-tier policies: one tier for everything, escalating nowhere.
    for tier in TIER_ORDER:
        if tier not in profiles:
            continue
        usd, calls, _, done = expected_task_cost(
            [profiles[tier]], max_attempts_at_top=max_attempts_at_top)
        rows.append(PolicyCost(
            f"always {tier}", usd, calls, 0.0, done,
            f"{profiles[tier].model.display}, success {profiles[tier].success_rate:.0%} per attempt, "
            f"retries decay at {profiles[tier].retry_recovery:.0%}",
        ))

    # Bottom-up chain: try cheap, escalate on failure. No router at all.
    if len(ordered) > 1:
        usd, calls, esc, done = expected_task_cost(ordered, max_attempts_at_top=max_attempts_at_top)
        rows.append(PolicyCost(
            "escalate from low", usd, calls, esc, done,
            "no router: always start cheap and climb on failure",
        ))

    # Routed: the router sends each task to its tier, and a misroute falls through
    # the remaining chain from wherever it landed.
    routed_usd = 0.0
    routed_calls = 0.0
    routed_esc = 0.0
    routed_done = 0.0
    for tier, share in mix.items():
        correct_chain = [profiles[t] for t in TIER_ORDER[TIER_ORDER.index(tier):] if t in profiles]
        good_usd, good_calls, good_esc, good_done = expected_task_cost(
            correct_chain, decision_usd=decision_usd, max_attempts_at_top=max_attempts_at_top)

        # A misroute: assume it lands one tier below where it belonged, which is
        # the expensive direction, then climbs.
        i = TIER_ORDER.index(tier)
        low_i = max(0, i - 1)
        bad_chain = [profiles[t] for t in TIER_ORDER[low_i:] if t in profiles]
        bad_usd, bad_calls, bad_esc, bad_done = expected_task_cost(
            bad_chain, decision_usd=decision_usd, max_attempts_at_top=max_attempts_at_top)

        routed_usd += share * (router_accuracy * good_usd + (1 - router_accuracy) * bad_usd)
        routed_calls += share * (router_accuracy * good_calls + (1 - router_accuracy) * bad_calls)
        routed_esc += share * (router_accuracy * good_esc + (1 - router_accuracy) * bad_esc)
        routed_done += share * (router_accuracy * good_done + (1 - router_accuracy) * bad_done)

    rows.append(PolicyCost(
        f"routed ({router_accuracy:.0%} accurate)", routed_usd, routed_calls, routed_esc, routed_done,
        f"mix {', '.join(f'{k} {v:.0%}' for k, v in mix.items())}; "
        f"router adds ${decision_usd:.6f}/task",
    ))

    return sorted(rows, key=lambda r: r.usd_per_completed_task)


@dataclass(frozen=True)
class BreakEven:
    """Where a router starts beating a named policy.

    `status` distinguishes the three outcomes that a bare float cannot:
      "always"    -- cheaper than the target even at zero router accuracy
      "never"     -- more expensive than the target even at perfect accuracy
      "threshold" -- `accuracy` is the point where it crosses over
    """

    status: str
    accuracy: Optional[float]
    target: str
    target_usd: float
    routed_usd_at_best: float

    def __bool__(self) -> bool:
        return self.status != "never"

    def __str__(self) -> str:
        if self.status == "always":
            return f"beats '{self.target}' at any router accuracy"
        if self.status == "never":
            return (f"never beats '{self.target}': ${self.routed_usd_at_best:.5f}/task even at "
                    f"100% accuracy vs ${self.target_usd:.5f}/task")
        return f"beats '{self.target}' once the router is {self.accuracy:.1%} accurate"


def router_breakeven_accuracy(
    profiles: Mapping[str, TierProfile],
    *,
    routed_tier_mix: Mapping[str, float],
    beat: str = "always high",
    tolerance: float = 1e-4,
) -> BreakEven:
    """How accurate the router must be before it beats a named policy.

    The number to quote when someone asks whether routing is worth building. Two
    readings worth knowing in advance:

      * a break-even near 0.97 means routing will not pay here -- a router that
        must be near-perfect to break even is a liability, not an optimisation;
      * `beat="escalate from low"` is the comparison that actually matters. Beating
        "always high" is easy and proves little; the trivial policy of starting
        cheap and climbing on failure needs no router at all, and a router that
        cannot beat THAT is pure added complexity.
    """
    rows_at_best = compare_policies(profiles, routed_tier_mix=routed_tier_mix, router_accuracy=1.0)
    target = next((r for r in rows_at_best if r.name == beat), None)
    if target is None:
        raise ValueError(
            f"No policy named {beat!r}. Available: "
            f"{', '.join(r.name for r in rows_at_best if not r.name.startswith('routed'))}."
        )

    def routed_at(acc: float) -> float:
        rows = compare_policies(profiles, routed_tier_mix=routed_tier_mix, router_accuracy=acc)
        return next(r.usd_per_completed_task for r in rows if r.name.startswith("routed"))

    lo, hi = 0.0, 1.0
    at_lo, at_hi = routed_at(lo), routed_at(hi)
    best = min(at_lo, at_hi)

    if at_lo <= target.usd_per_completed_task:
        return BreakEven("always", 0.0, beat, target.usd_per_completed_task, best)
    if at_hi > target.usd_per_completed_task:
        return BreakEven("never", None, beat, target.usd_per_completed_task, best)

    while hi - lo > tolerance:
        mid = (lo + hi) / 2
        if routed_at(mid) <= target.usd_per_completed_task:
            hi = mid
        else:
            lo = mid
    return BreakEven("threshold", hi, beat, target.usd_per_completed_task, best)


@dataclass(frozen=True)
class CascadeEconomics:
    escalation_rate: float
    fee_ratio_vs_fallback: float
    usd_per_1k: float
    fallback_usd_per_1k: float
    breakeven_escalation_rate: float

    def __str__(self) -> str:
        return (f"escalating {self.escalation_rate*100:.1f}%: ${self.usd_per_1k:.3f}/1k vs "
                f"${self.fallback_usd_per_1k:.3f}/1k = {self.fee_ratio_vs_fallback*100:.1f}% of the fee "
                f"(stops paying above {self.breakeven_escalation_rate*100:.1f}% escalation)")


def cascade_economics(
    *,
    escalation_rate: float,
    cheap_usd_per_judgment: float = DECISION_USD_PER_MTOK * 0.001,
    fallback_usd_per_judgment: float,
) -> CascadeEconomics:
    """Fee ratio for an accept-when-confident cascade, plus where it stops paying.

    The break-even escalation rate is the useful half. Above it you are paying the
    cheap layer on every item AND the expensive one on most of them -- at which
    point running the expensive model alone is cheaper and simpler. The published
    tau=0.90 cascade escalated 34% and reached 47% of the fee; on harder traffic
    the same threshold escalated 61%, which is much closer to the cliff.
    """
    cheap_total = cheap_usd_per_judgment * 1000
    fallback_total = fallback_usd_per_judgment * 1000
    cascade_total = cheap_total + fallback_total * escalation_rate

    # cheap + fallback*r == fallback  ->  r == 1 - cheap/fallback
    breakeven = 1.0 - (cheap_total / fallback_total) if fallback_total else 0.0

    return CascadeEconomics(
        escalation_rate=escalation_rate,
        fee_ratio_vs_fallback=cascade_total / fallback_total if fallback_total else 0.0,
        usd_per_1k=cascade_total,
        fallback_usd_per_1k=fallback_total,
        breakeven_escalation_rate=max(0.0, breakeven),
    )


def loop_overhead(
    *,
    model: Model,
    turns_per_night: int = 200,
    decisions_per_turn: int = 3,
    state_mtok_per_decision: float = 0.004,
    output_mtok_per_decision: float = 0.00005,
    nights: int = 30,
    batch_into_one_call: bool = True,
) -> dict[str, float]:
    """What a decision layer removes from an overnight loop.

    `batch_into_one_call` is rule 5 priced: asking three questions in one call
    sends the state once instead of three times, which is roughly a 3x difference
    on the decision-layer line and nothing at all on the generation line.
    """
    decisions = turns_per_night * decisions_per_turn

    on_model = model.cost_usd(
        input_mtok=state_mtok_per_decision * decisions,
        output_mtok=output_mtok_per_decision * decisions,
    )

    sends = turns_per_night if batch_into_one_call else decisions
    on_decision_layer = sends * state_mtok_per_decision * DECISION_USD_PER_MTOK

    return {
        "decisions_per_night": float(decisions),
        "model_usd_per_night": on_model,
        "model_usd_per_month": on_model * nights,
        "decision_layer_usd_per_night": on_decision_layer,
        "decision_layer_usd_per_month": on_decision_layer * nights,
        "saving_usd_per_month": (on_model - on_decision_layer) * nights,
        "ratio": on_model / on_decision_layer if on_decision_layer else float("inf"),
    }


def tier_cost_table(
    registry: Registry | None = None,
    *,
    input_mtok: float = 0.02,
    output_mtok: float = 0.004,
) -> str:
    """Cost per call for every model in the registry, grouped by tier."""
    reg = registry or Registry.load()
    lines = [f"{'tier':<8} {'model':<28} {'platform':<10} {'$/call':>10}  {'x cheapest':>10}"]

    cheapest = None
    for tier in TIER_ORDER:
        for m in reg.candidates(tier):
            try:
                c = m.cost_usd(input_mtok=input_mtok, output_mtok=output_mtok)
            except RegistryError:
                continue
            cheapest = c if cheapest is None else min(cheapest, c)

    for tier in reversed(TIER_ORDER):
        for m in sorted(reg.candidates(tier), key=lambda x: x.platform):
            try:
                c = m.cost_usd(input_mtok=input_mtok, output_mtok=output_mtok)
                cost, mult = f"${c:.5f}", f"{c / cheapest:.1f}x" if cheapest else "-"
            except RegistryError:
                cost, mult = "unpriced", "-"
            lines.append(f"{tier:<8} {m.display:<28} {m.platform:<10} {cost:>10}  {mult:>10}")
    return "\n".join(lines)
