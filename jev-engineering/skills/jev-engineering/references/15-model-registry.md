# 15 — The model registry: tiers across platforms

> v1.2 預設採 [兩階段工作流](18-two-phase-workflow.md)。本頁保留底層 API；其中 high 路由／升級在新流程中代表重新規劃，不授權 high 生成。

`assets/jev/models.json` is the registry. It is **data, not code**, because prices and model ids change weekly and a constant buried in a module is a constant nobody re-checks.

## A tier is not a model

A tier is a **(model, reasoning effort)** pair. The same weights buy different capability at different efforts, at different prices — so `Gemini 3.6 Flash` appears twice below, once per tier. Routing that ignores effort routes to "Flash" and gets whichever effort the default is.

| Tier | Anthropic | OpenAI | Google |
|---|---|---|---|
| **high** | Claude Opus 5.5 | GPT-6 Astra · Sol-high | — |
| **medium** | Claude Sonnet 5.5 | GPT-5 Terra-high | Gemini 3.6 Flash-high |
| **low** | Claude Haiku 4.5 | GPT-5 Luna-high | Gemini 3.6 Flash-medium |

Three platforms per tier is not redundancy for its own sake. It buys three things:

1. **Cost arbitrage within a tier.** The cheapest capable model wins, and that changes when anyone reprices.
2. **A fallback when a platform degrades.** Flip `available: false` and every route moves off it with no code change.
3. **Data-class policy.** `platforms.*.data_classes_allowed` keeps a class of content away from a vendor entirely — which is a policy your code can now enforce per step.

## What the registry refuses to do

**An unpriced model is never treated as free.** `select()` cost-ranks only models that have prices and warns when it is ranking a subset; with no prices at all it falls back to the platform preference order. `Registry.audit()` lists exactly what is missing.

**A display name is never sent as an identifier.** `Model.callable_id` raises unless `api_id` is filled. "Claude Opus 5.5" is a name; `claude-opus-5` is an id, and confusing the two is a 404 at 3am.

```python
from jev import Registry
reg = Registry.load()
print(reg.table())        # tier x platform, with prices and their sources
print(reg.audit())        # missing_price, missing_api_id, unverified_api_id, empty_tiers
```

As shipped, most prices and ids are `null` and one price is cited from the paper's frozen panel. **Fill them from the provider's live pricing page. Do not let an agent guess them** — every downstream cost figure inherits whatever is in this file.

## Routing

```python
from jev import route_task

d = route_task(
    "Add pagination to the orders endpoint",
    files_in_scope=["api/orders.py", "api/schema.py"],
    prior_attempts=0,
)
print(d.model)          # Claude Sonnet 5.5 [anthropic/medium]
print(d.reason)         # tier medium at 0.95
print(d.model.callable_id)
```

One call, four questions: tier, reversibility, data class, and whether the task needs a derivation. Then code applies the escalation rules.

**Uncertainty routes up.** Below `tau` the tier becomes `high`. A misroute to a cheap tier costs a failed attempt *plus* the retry on the expensive tier — strictly worse than starting expensive. A misroute upward costs only money.

Escalation triggers, all applied in code after the call:

| Signal | Effect |
|---|---|
| tier confidence `< tau` (0.85) | → `high` |
| reversibility score `>= 1.5` | one tier up |
| `needs_derivation > 0.60` | one tier up — this is the documented weak spot |
| `prior_attempts > 0` | one tier up per attempt, unconditionally |
| data class `secrets` | **`PolicyStop`** — see below |

`prior_attempts` is counted in code, not read by the model (rule 6). A retry escalating is not a judgement call.

## `secrets` is a policy stop, not a route

```python
from jev.routing import PolicyStop
try:
    d = route_task(request)
except PolicyStop as stop:
    hand_to_human(stop)
```

No tier is the right answer to "this contains credentials". `route_task` raises rather than picking a model, because the failure mode being prevented is an agent helpfully retrying with the data-class filter removed. Catch it and route to a person; do not catch it and widen the filter.

Note what the registry does here without any special-casing: `data_classes_allowed` lists no platform for `secrets`, so the candidate set is empty. Policy is expressed as data.

## Security-aware routing, not just cost-aware

Cost is not the only reason to route. The `data_class` question already returns `public`, `internal`, `customer_data`, `secrets`, `other` — let it pick the **platform**, not only the tier:

```python
d = route_task(request)                 # customer_data narrows to anthropic only
d = route_task(request, exclude_platforms=["openai"])   # an incident, a contract, a region
d = route_task(request, platform="google")              # pinned by policy
d = route_task(request, pinned_tier="high")             # skips the model call entirely
```

Pin `high` for anything touching auth, payments, migrations, or CI config regardless of what the classifier says. That is policy, and policy belongs above the classifier.

## Filling the registry

1. Copy each model's real `api_id` from its provider's model list.
2. Copy `input_usd_per_mtok` / `output_usd_per_mtok` from the live pricing page, and put the retrieval date in `price_source`.
3. Set `cache_read_multiplier` to the provider's cached-input discount. It matters more than it looks — see `01-model-routing.md`.
4. Re-run `reg.audit()` until `missing_price` and `missing_api_id` are empty.
5. Only then trust `economics.compare_policies()`; before that it is arithmetic on blanks.

Re-check quarterly, and whenever a provider announces pricing. A registry is the one file in this skill that is *supposed* to change often.
