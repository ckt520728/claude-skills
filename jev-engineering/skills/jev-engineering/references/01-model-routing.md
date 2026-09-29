# 01 — Model routing

Send each step to the cheapest model that can complete it.

## Why this fork is different

Every other playbook here saves money because a decision is cheaper than a generation. Routing saves money for a second, larger reason: **the router must not enter the conversation.**

Two models, list prices per million tokens: a big one at 5 in / 25 out, a smaller one at 3 in / 15 out. Let `X` be millions of context tokens, `Y` millions of generated output, `Z` millions of tokens generated *inside* that output (shell commands, file reads).

```
big only:              25Y + 5Z
big -> small -> big:   3X + 20Y + 8Z
```

The second path pays `3X` for the small model to load the context and then `5(Y+Z)` for the big model to re-read everything the small one produced. With a realistic split (`X=0.65, Y=0.12, Z=0.23`) the routed path costs about 1.5x the unrouted one. **Routing down and back up cost more than not routing.** That is why two years of model-routing work quietly failed, and none of it shows on a pricing page.

A decision model that never joins the conversation deletes `3X` and the re-read. It reads a small state snippet beside the loop and returns a label.

## The call

```python
from jev import decide, Choice, Score

TIERS = {
    "fast":     "Direct lookups, extraction, a rename, a single localized edit, a formatting pass.",
    "standard": "Multi-file changes with a clear specification and no design decision to make.",
    "powerful": "Architecture, an unfamiliar subsystem, a decision that is expensive to reverse.",
    "other":    "None of the above fits.",
}

r = decide(
    state={
        "request": user_request,
        "files_in_scope": file_list,          # counted in code
        "repo_area": area,
        "prior_attempts": attempts,           # counted in code
    },
    questions={
        "tier": Choice(instructions="Choose the least costly tier that can complete this request.",
                       criteria=TIERS),
        "reversibility": Score(
            instructions="How hard would this change be to undo if it were wrong?",
            criteria=["Trivial to revert", "Recoverable with effort", "Irreversible or public"],
        ),
    },
)

t = r.answers["tier"]
tier = t.choice if (t.confidence >= 0.85 and t.choice != "other") else "powerful"
if r.answers["reversibility"].score >= 1.5:
    tier = "powerful"
```

Note the default direction: **uncertainty routes up, not down.** A misroute to the cheap tier costs a failed attempt plus a retry on the expensive tier — strictly worse than having started expensive. A misroute upward costs only money.

## What stays in code

- Retry escalation: second attempt on the same request goes up a tier, unconditionally.
- Hard pins: anything touching auth, payments, migrations, or CI config starts at `powerful` regardless of the label.
- Spend caps per request and per day.
- Counting files, lines, and prior attempts.

## LangChain, if you already use it

```python
from langchain.agents import create_agent
from langchain_typesafe.experimental.middleware import ModelChoice, ModelRouterMiddleware

router = ModelRouterMiddleware(
    choices={
        "fast":     ModelChoice(model="openai:luna", criteria="Direct lookups, extraction, localized changes."),
        "powerful": ModelChoice(model="openai:sol",  criteria="Architecture and high-stakes decisions."),
    },
    instructions="Choose the least costly model that can complete the task.",
)
agent = create_agent("openai:gpt-5.6-luna", middleware=[router])
```

Middleware hides the threshold. Read what it defaults to before trusting it in production, and prefer the explicit call above when the routing decision has money behind it.

## Across platforms, with a real registry

The hand-written `TIERS` dict above is the teaching version. In practice a tier spans platforms, and a tier is a **(model, effort)** pair rather than a model — so the tier table lives in `assets/jev/models.json` and `route_task()` reads it:

```python
from jev import route_task
d = route_task("Add pagination to the orders endpoint",
               files_in_scope=["api/orders.py", "api/schema.py"])
d.model.callable_id     # the id to send
d.reason                # why this tier
```

That buys cost arbitrage inside a tier, a one-flag fallback when a platform degrades, and data-class policy per platform. Full registry, the escalation table, and the `secrets` policy stop: **`15-model-registry.md`**.

## Mid-task switching is a different question

Routing once, at the start, is cheap and usually right. Changing model *while* a task runs is where the KV-cache arithmetic above turns from a warning into a calculation — and the answer is usually "stay put", with one exception (a one-way handoff of the remaining work).

```python
from jev import worth_switching, self_route
worth_switching(high, medium, context_mtok=0.65, output_mtok=0.12, inner_mtok=0.23)
# costs $2.04 more; $1.75 of that is High re-reading the output
```

Full treatment, including de-escalation and the break-even context size: **`16-self-switching.md`**.

## Tuning

Label 100-200 real requests from your own traffic with the tier that *actually* completed them (not the tier you would have guessed). Then follow `10-threshold-tuning.md`. The metric is **cost per completed request including retries** — a router that looks cheap per call and doubles your retry rate is a loss.

### Beat the trivial policy, not the obvious one

A router that beats "always use the high tier" has proved almost nothing. The policy to beat is **"start at the cheap tier and climb on failure"**, which needs no router, no registry, and no decision call at all.

```python
from jev import router_breakeven_accuracy
router_breakeven_accuracy(profiles, routed_tier_mix=mix, beat="escalate from low")
# never beats 'escalate from low': $0.13894/task even at 100% accuracy vs $0.12630/task
```

On a shallow capability gradient — where the cheap tier already finishes most tasks — that is a common result, and the honest conclusion is to skip the router and just climb. Routing earns its keep when **the gradient is steep and a wasted cheap attempt is expensive**: long tasks, tasks with side effects, tasks where a failed attempt costs a human's attention rather than four cents.

Run the comparison before building the router, not after. `11-economics.md` has the table.

## Security-aware routing

Cost is not the only reason to route. The `data_class` question already returns `public`, `internal`, `customer_data`, `secrets`, `other` — let the label pick the *platform*, not just the tier. Keeping a class of file away from a given vendor entirely is a policy your code can now enforce per step, cheaply, and in the registry it is expressed as data rather than as a branch.
