#!/usr/bin/env python3
"""Cross-platform routing, self-switching economics, and the policy comparison.

Runs against the real registry for the parts that need no prices, and against
clearly-labelled SYNTHETIC prices for the arithmetic, because most prices in
models.json ship unset on purpose.

    python examples/route_models.py                # registry + switch economics
    python examples/route_models.py --route "Add pagination to the orders endpoint"
    python examples/route_models.py --economics    # policy comparison table
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jev import (  # noqa: E402
    JevError,
    Model,
    Registry,
    TierProfile,
    cascade_economics,
    compare_policies,
    loop_overhead,
    route_task,
    router_breakeven_accuracy,
    tier_cost_table,
    worth_switching,
)
from jev.routing import PolicyStop  # noqa: E402

# Synthetic prices, used ONLY for the arithmetic demos below. They are not a claim
# about any vendor's pricing -- fill models.json from the live pricing pages.
SYNTH_HIGH = Model(key="synthetic-high", display="High tier (synthetic)", platform="x",
                   tier="high", input_usd_per_mtok=10.0, output_usd_per_mtok=50.0,
                   price_source="SYNTHETIC -- illustrative only")
SYNTH_MED = Model(key="synthetic-medium", display="Medium tier (synthetic)", platform="x",
                  tier="medium", input_usd_per_mtok=3.0, output_usd_per_mtok=15.0,
                  price_source="SYNTHETIC -- illustrative only")
SYNTH_LOW = Model(key="synthetic-low", display="Low tier (synthetic)", platform="x",
                  tier="low", input_usd_per_mtok=0.8, output_usd_per_mtok=4.0,
                  price_source="SYNTHETIC -- illustrative only")

# The switching demo uses the narrower price gap from 16-self-switching.md, because
# that is the regime where the cache rebuild dominates and the lesson is visible.
# The wide-gap pair below shows the opposite regime -- the rule is conditional.
REF_HIGH = Model(key="ref-high", display="High (5/25)", platform="x", tier="high",
                 input_usd_per_mtok=5.0, output_usd_per_mtok=25.0,
                 price_source="SYNTHETIC -- matches references/16")
REF_MED = Model(key="ref-medium", display="Medium (3/15)", platform="x", tier="medium",
                input_usd_per_mtok=3.0, output_usd_per_mtok=15.0,
                price_source="SYNTHETIC -- matches references/16")


def show_registry() -> None:
    reg = Registry.load()
    print("=" * 78)
    print("REGISTRY: tier x platform")
    print("=" * 78)
    print(reg.table())

    report = reg.audit()
    print("\nAudit -- what must be filled before this drives real, cost-ranked calls:")
    for field, keys in report.items():
        print(f"  {field:<20} {', '.join(keys) if keys else '(none)'}")

    print("\nSelection within a tier (cheapest priced candidate, else platform preference):")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for tier in ("high", "medium", "low"):
            print(f"  {tier:<7} -> {reg.select(tier)}")
        print(f"  high, no openai -> {reg.select('high', exclude_platforms=['openai'])}")

    print("\nData-class policy narrows the candidate set, as data not as a branch:")
    for data_class in ("public", "internal", "customer_data", "secrets"):
        keys = [m.key for m in reg.candidates("high", data_class=data_class)]
        print(f"  high + {data_class:<14} -> {keys or 'NONE -- policy stop, route to a human'}")


def show_switching() -> None:
    print("\n" + "=" * 78)
    print("SELF-SWITCHING: the KV-cache rebuild is the term nobody prices")
    print("=" * 78)
    print("Synthetic prices: high 5/25, medium 3/15 per Mtok (a 1.7x output gap).\n")

    output_mtok, inner_mtok = 0.12, 0.23

    print("Borrowing the cheaper model for ONE step, then returning:")
    print(f"  {'context':>9}  {'stay':>9}  {'switch':>9}  {'verdict':>8}")
    for context in (0.02, 0.10, 0.25, 0.50, 0.65, 1.00):
        v = worth_switching(REF_HIGH, REF_MED, context_mtok=context,
                            output_mtok=output_mtok, inner_mtok=inner_mtok)
        print(f"  {context:>9.2f}  ${v.stay_usd:>8.4f}  ${v.switch_usd:>8.4f}  "
              f"{'SWITCH' if v else 'stay':>8}")

    v = worth_switching(REF_HIGH, REF_MED, context_mtok=0.65,
                        output_mtok=output_mtok, inner_mtok=inner_mtok)
    print(f"\n  At a realistic 0.65 Mtok: {v.reason}")

    print("\nHanding the REST of the task over (one-way, so no cache rebuild):")
    print(f"  {'context':>9}  {'stay':>9}  {'switch':>9}  {'verdict':>8}")
    for context in (0.10, 0.25, 0.50, 0.55, 0.65, 1.00):
        v = worth_switching(REF_HIGH, REF_MED, context_mtok=context,
                            output_mtok=output_mtok, inner_mtok=inner_mtok,
                            return_to_current=False)
        print(f"  {context:>9.2f}  ${v.stay_usd:>8.4f}  ${v.switch_usd:>8.4f}  "
              f"{'SWITCH' if v else 'stay':>8}")
    print(f"\n  Break-even context for a one-way handoff: "
          f"{v.breakeven_context_mtok:.3f} Mtok")

    print("\n  The rule is CONDITIONAL, not absolute. A round trip pays iff")
    print("      Y * (A_out - B_out - A_in)  >  B_in * (X + Z)")
    print("  where the bracket is the output saving NET of the re-read price:\n")
    print(f"  {'high':>10} {'medium':>10} {'margin':>8}  verdict")
    for hi, md in [((5, 25), (3, 15)), ((2, 10), (1, 5)), ((3, 15), (0.8, 4)),
                   ((10, 50), (3, 15)), ((10, 50), (0.8, 4))]:
        a = Model(key="a", display="a", platform="x", tier="high",
                  input_usd_per_mtok=hi[0], output_usd_per_mtok=hi[1])
        b = Model(key="b", display="b", platform="x", tier="medium",
                  input_usd_per_mtok=md[0], output_usd_per_mtok=md[1])
        v2 = worth_switching(a, b, context_mtok=0.65, output_mtok=output_mtok,
                             inner_mtok=inner_mtok)
        print(f"  {f'{hi[0]}/{hi[1]}':>10} {f'{md[0]}/{md[1]}':>10} "
              f"{hi[1] - md[1] - hi[0]:>8.1f}  {'SWITCH' if v2 else 'stay'}")
    print("\n  Narrow output gap between tiers -> the rebuild dominates, borrow nothing.")
    print("  Wide gap -> borrowing pays. Either way a one-way handoff pays sooner.")
    print("  Put your real prices in models.json and ask worth_switching().")


def show_economics() -> None:
    print("\n" + "=" * 78)
    print("ECONOMICS: cost per COMPLETED task")
    print("=" * 78)
    print(tier_cost_table())

    profiles = {
        "low": TierProfile("low", SYNTH_LOW, success_rate=0.55),
        "medium": TierProfile("medium", SYNTH_MED, success_rate=0.80),
        "high": TierProfile("high", SYNTH_HIGH, success_rate=0.94),
    }
    mix = {"low": 0.55, "medium": 0.30, "high": 0.15}

    print("\nPer-attempt success 55/80/94%, traffic mix 55/30/15, router 90% accurate:\n")
    for row in compare_policies(profiles, routed_tier_mix=mix, router_accuracy=0.90):
        print("  ", row)
    print("\n  Read both columns: 'always low' is cheapest per completed task and")
    print("  finishes 62% of them. Completion rate is not a footnote.")

    print("\nWhat does the router have to beat?")
    for beat in ("always high", "always medium", "escalate from low"):
        print("  ", router_breakeven_accuracy(profiles, routed_tier_mix=mix, beat=beat))
    print("\n  Beating 'always high' proves little. 'escalate from low' needs no router")
    print("  at all -- that is the comparison that decides whether to build one.")

    print("\nA steeper capability gradient (30/70/96%) changes the answer:")
    steep = {
        "low": TierProfile("low", SYNTH_LOW, success_rate=0.30),
        "medium": TierProfile("medium", SYNTH_MED, success_rate=0.70),
        "high": TierProfile("high", SYNTH_HIGH, success_rate=0.96),
    }
    for row in compare_policies(steep, routed_tier_mix=mix, router_accuracy=0.95):
        print("  ", row)

    print("\nJudge cascade: where it stops paying")
    for rate in (0.10, 0.34, 0.61, 0.90):
        print("  ", cascade_economics(escalation_rate=rate, fallback_usd_per_judgment=0.01218))

    print("\nOvernight loop overhead (200 turns x 3 decisions over 4k state, 30 nights):")
    split = loop_overhead(model=SYNTH_HIGH, batch_into_one_call=False)
    batched = loop_overhead(model=SYNTH_HIGH, batch_into_one_call=True)
    print(f"  decisions on the high tier : ${split['model_usd_per_month']:>8.2f}/month")
    print(f"  decision layer, 3 calls    : ${split['decision_layer_usd_per_month']:>8.2f}/month")
    print(f"  decision layer, batched    : ${batched['decision_layer_usd_per_month']:>8.2f}/month")
    print(f"  batched is {batched['ratio']:.0f}x cheaper; rule 5 alone is "
          f"{split['decision_layer_usd_per_month'] / batched['decision_layer_usd_per_month']:.0f}x of it")


def do_route(request: str, attempts: int) -> None:
    print("=" * 78)
    print(f"ROUTING: {request!r}")
    print("=" * 78)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            d = route_task(request, prior_attempts=attempts)
    except PolicyStop as stop:
        print(f"  POLICY STOP -- no model may serve this:\n    {stop}")
        return
    except JevError as exc:
        print(f"  No decision backend available: {exc}")
        print("\n  Routing needs a backend to read the request. The registry, the switch")
        print("  economics and the policy comparison do not -- run without --route.")
        return
    print(f"  model        {d.model}")
    print(f"  api id       {d.model.api_id or '(UNSET in models.json -- fill before a real call)'}")
    print(f"  tier         {d.tier} (confidence {d.tier_confidence:.2f})")
    print(f"  data class   {d.data_class}")
    print(f"  escalated    {d.escalated}")
    print(f"  reason       {d.reason}")
    if d.cost_usd_estimate is not None:
        print(f"  est. cost    ${d.cost_usd_estimate:.5f}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--route", metavar="REQUEST", help="route one request (needs a backend)")
    ap.add_argument("--attempts", type=int, default=0, help="prior failed attempts")
    ap.add_argument("--economics", action="store_true", help="policy comparison only")
    args = ap.parse_args()

    if args.route:
        do_route(args.route, args.attempts)
        return 0
    if args.economics:
        show_economics()
        return 0

    show_registry()
    show_switching()
    show_economics()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
