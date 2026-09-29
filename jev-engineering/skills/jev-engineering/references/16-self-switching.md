# 16 — Self-routing and mid-task switching

Routing at the start of a task is `15-model-registry.md`. This is the harder question: **should a task change model while it is running?**

The answer is "less often than you think", and the reason is arithmetic you can run.

## The cache rebuild is the dominant term

When control returns to the larger model, it re-reads everything the smaller one produced. Let `X` be the context the target must load, `Y` the output it generates, `Z` the tokens generated *inside* that output (shell commands, file reads it triggers):

```
stay   = current.out * Y + current.in * Z
switch = target.in * X + target.out * Y + target.in * Z
         + current.in * (Y + Z)            <-- the cache rebuild
```

With a high tier at 5/25 and a medium at 3/15 that is `25Y + 5Z` versus `3X + 20Y + 8Z`. At a realistic `X=0.65, Y=0.12, Z=0.23`:

```python
from jev import worth_switching
worth_switching(high, medium, context_mtok=0.65, output_mtok=0.12, inner_mtok=0.23)
# costs $2.0400 more ($4.1500 -> $6.1900); $1.7500 of that is High re-reading the
# output. No context size makes it pay -- the fixed cost alone exceeds staying put
```

The switch costs about **1.5x staying put**, and $1.75 of the $2.04 penalty is purely the re-read. None of it appears on a pricing page. This is why two years of model-routing work quietly failed.

## The one switch that pays: a one-way handoff

Drop the return leg and the rebuild term disappears:

```python
worth_switching(high, medium, context_mtok=0.25, output_mtok=0.12, inner_mtok=0.23,
                return_to_current=False)
# saves $0.9100 ($4.1500 -> $3.2400), one-way handoff so no cache rebuild
```

| Context `X` | Round trip (borrow for one step) | One-way (hand over the rest) |
|---|---|---|
| 0.25 Mtok | costs 1.20x | **saves 22%** |
| 0.65 Mtok | costs 1.49x | costs 1.07x |
| 1.00 Mtok | costs 1.74x | costs 1.32x |

The break-even sits around **0.55 Mtok of context** for a one-way handoff at these prices. `worth_switching()` reports that number, which is more useful than the yes/no: it tells you *when* the switch would start to make sense.

### When does a round trip pay? One inequality

At the prices above it never does — but that is a property of *these* prices, not a law. Rearranging `stay > switch`:

```
a round trip pays  iff  Y * (A_out - B_out - A_in)  >  B_in * (X + Z)
                            \_______margin_______/
```

The **margin** — the output saving net of the larger model's own input price — decides it. `A_in` appears as a subtraction because that is the price of re-reading, and it is charged against the same `Y` the saving comes from.

| high tier | medium tier | margin | verdict at `X=0.65, Y=0.12, Z=0.23` |
|---|---|---|---|
| 5 / 25 | 3 / 15 | 5 | stay — the re-read eats the gain |
| 2 / 10 | 1 / 5 | 3 | stay |
| 3 / 15 | 0.8 / 4 | 8 | switch |
| 10 / 50 | 3 / 15 | 25 | switch |
| 10 / 50 | 0.8 / 4 | 36 | switch |

So the honest rule is conditional, and it is the useful kind of conditional because you can evaluate it:

- **Narrow output gap between adjacent tiers** (the 5/25 → 3/15 case, a 1.7x output ratio): the rebuild dominates. Borrow nothing.
- **Wide output gap** (10/50 → 0.8/4, a 12x ratio): borrowing pays even with the rebuild.
- **Either way, a one-way handoff pays sooner** than a round trip, because the rebuild term is simply absent.

Do not carry a rule of thumb here. Put your real prices in `models.json` and call `worth_switching()` — that is precisely the question it answers, and the answer moves every time anyone reprices.

## Self-routing in the loop

```python
from jev import self_route

model, why = self_route(
    goal=goal, progress=notes_so_far, current=current_model,
    context_mtok=measure_context(),      # measured in code, not estimated by the model
    output_mtok=0.05, inner_mtok=0.02,
)
```

Two gates in series, and both must agree:

1. **Capability** — the decision layer says the *remaining* work needs a different tier, confidently.
2. **Economics** — `worth_switching()` says the move pays for itself.

Gate 2 is why this returns the current model far more often than expected. A capability argument for switching up is not a cost argument, and the rebuild is charged whether or not the switch helped.

Three refusals worth knowing:

- **Wants a higher tier but is not stuck** (`stuck < 0.50`) → stay. A preference for a better model is not a reason to pay the rebuild. Escalate when the work has actually stalled.
- **Tier read is uncertain** → stay. Mid-task churn on a low-confidence signal is how a loop spends its budget changing its mind.
- **Prices unknown** → stay, and say so. The one exception: genuinely stuck *and* wanting to escalate, where it switches and records that the economics were unavailable. Correctness beats a cost estimate you do not have.

Escalating is a **correctness** spend, not a saving. When `self_route` moves up it reports what it cost, not what it saved — because nothing was saved:

```
switch up to high: stuck at 0.78; costs $0.0412
```

## Measuring the context, in code

`context_mtok` must be measured, not guessed — the whole calculation turns on it.

```python
context_mtok = total_prompt_tokens / 1_000_000     # from the provider's usage field
```

Use the provider's reported `input_tokens` from the previous turn. Do not ask the model how big its context is (rule 6: counting is not a model's job), and do not estimate from character counts across a mixed codebase.

## What this buys beyond money

Once a tier change is cheap to *evaluate*, two things become practical that were not:

**De-escalation.** Most routing only ever climbs. A long task that has passed its hard part can hand the remainder down a tier — and that is the switch direction where the arithmetic actually favours you, because the cheaper model's lower input price applies to the whole remaining context.

**Security-driven switching.** The same machinery routes on data class, not just tier. When a task moves from public code into a file class that a platform may not see, `self_route`'s registry filter moves it — a switch that has nothing to do with capability and everything to do with policy. See `15-model-registry.md`.

## Failure modes specific to this fork

- **Churn.** Re-evaluating every turn costs a decision call per turn and invites oscillation. Check every N turns, or only at natural boundaries (a phase completing, a test suite going red).
- **Switching mid-edit.** A model that has half-written a change and hands over leaves the successor to infer intent from a partial diff. Switch at boundaries, never mid-artifact.
- **Assuming the rebuild is free because of caching.** A cache read is cheaper, not free — `cache_read_multiplier` in the registry is why `Model.cost_usd()` takes a `cached_mtok` argument. A 0.1 multiplier shrinks the penalty; it does not remove it, and it only applies if the cache is actually warm on that provider for that prefix.
- **Trusting a tier label as a capability guarantee.** The tiers in the registry are *your* assignment of models to bands. They are a claim about your workload that `references/10-threshold-tuning.md` tells you how to check.
