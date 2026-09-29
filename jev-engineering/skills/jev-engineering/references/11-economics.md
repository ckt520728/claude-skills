# 11 — Economics: the cost model and what to measure

## The unit cost

$0.042 per million input tokens, output free (vendor-listed). At 1,000 billed input tokens per decision, 10,000 decisions cost $0.42.

Zero output-token billing matters more than the headline rate. A routing call on a frontier model pays for a short generation on every decision; here that term is absent entirely, which is why the ratio widens as decisions get more frequent and smaller.

## One overnight loop, priced

200 turns, three decisions per turn — is it safe, which step next, are we done — over ~4,000 tokens of state with 50 tokens out. 600 decisions a night, list prices, 30 nights:

| Who decides | Per night | Per month | Time waiting on decisions |
|---|---|---|---|
| Frontier model ($10 / $50 per M) | $25.50 | $765 | ~52 min at 5.2 s/call |
| Mid model ($3 / $15 per M) | $7.65 | $229.50 | seconds on every call |
| Decision layer ($0.042 per M, output free) | $0.10 | $3.02 | ~2.5 min at ~0.25 s |

Ask the three questions in **one** call per turn and the state is sent once: about $1.08 a month. Rule 5 is worth roughly 3x here, not a rounding error.

Cache reads at a quarter price bring the frontier column to roughly $225 — still about 75x the decision-layer bill.

**What the LLM spends on building does not change.** Everything in that table is overhead the subtraction removes. On a subscription plan the effect shows up as usage headroom rather than dollars: turns that went to judging go back to real work.

## Scaled out

Eleven decision points at a conservative five per iteration, 20 iterations per task, 100 tasks a day:

```
5 * 20 * 100        = 10,000 decisions/day
10,000 * 1,000 tok  = 10M input tokens/day
10M @ $0.042/MTok   = $0.42/day
```

The same 10,000 decisions on a frontier model, even at a cheap $1/M input with a short output, land two to three orders of magnitude higher and add seconds rather than milliseconds each.

## Measure cost per completed task, not per decision

The one metric that matters, and the one that makes the others safe to ignore.

**A cheap decision that sends a worker down the wrong branch costs far more than the decision itself.** A misroute that triggers a retry on the expensive tier has spent the frontier fee *plus* the wasted attempt — the decision saved four cents and lost four dollars. Any evaluation of this architecture that reports per-call savings without per-task cost is measuring the wrong thing.

`assets/jev/economics.py` computes it. Give it what each tier costs and how often it *actually finishes the job*, and it prices the policies against each other:

```python
from jev import TierProfile, compare_policies

profiles = {
    "low":    TierProfile("low",    low_model,    success_rate=0.55),
    "medium": TierProfile("medium", medium_model, success_rate=0.80),
    "high":   TierProfile("high",   high_model,   success_rate=0.94),
}
for row in compare_policies(profiles, routed_tier_mix={"low":.55,"medium":.30,"high":.15},
                            router_accuracy=0.90):
    print(row)
```

```
always low            $0.09408/task  1.84 calls   0.0% escalated   62.5% completed
escalate from low     $0.12630/task  1.55 calls  45.0% escalated   99.6% completed
always medium         $0.19245/task  1.36 calls   0.0% escalated   84.8% completed
routed (90% accurate) $0.19565/task  1.40 calls  31.8% escalated   98.9% completed
always high           $0.46233/task  1.11 calls   0.0% escalated   95.7% completed
```

### Completion rate is a column, not a footnote

"Always low" looks like the cheapest policy and **finishes 62% of tasks**. Any comparison that folds completion into the denominator and reports only dollars makes the weakest tier look best, every time. Read the two columns together or not at all.

### Retries do not rescue a tier that cannot do the job

`TierProfile.retry_recovery` defaults to `0.25`: a retry at the *same* tier succeeds at a quarter of the first attempt's rate, because most failures are capability rather than luck. A model that cannot do a task does not start being able to on the third attempt.

Setting this near 1.0 is the single easiest way to produce a spreadsheet that endorses a weak tier — on paper it eventually succeeds, in practice it eventually gives up.

### Ask what the router has to beat

```python
from jev import router_breakeven_accuracy
router_breakeven_accuracy(profiles, routed_tier_mix=mix, beat="escalate from low")
```

Three possible answers, and they are distinguishable:

```
beats 'always high' at any router accuracy
beats 'always medium' once the router is 71.4% accurate
never beats 'escalate from low': $0.13894/task even at 100% accuracy vs $0.12630/task
```

Beating "always high" proves little. **The policy to beat is "start cheap and climb on failure"** — it needs no router, no registry, and no decision call. A break-even near 0.97 against that means routing is a liability here, not an optimisation.

Routing earns its keep when the capability gradient is steep *and* a wasted cheap attempt is expensive — long tasks, tasks with side effects, tasks where a failed attempt costs a person's attention rather than four cents.

### The cascade has a cliff

```python
from jev import cascade_economics
cascade_economics(escalation_rate=0.34, fallback_usd_per_judgment=0.01218)
# escalating 34.0%: $4.183/1k vs $12.180/1k = 34.3% of the fee
#                   (stops paying above 99.7% escalation)
```

Above the break-even escalation rate you pay the cheap layer on everything *and* the expensive one on nearly everything, at which point running the expensive model alone is cheaper and simpler. The published `tau=0.90` cascade escalated 34%; on harder traffic the same threshold escalated 61%, which is much closer to the cliff than it sounds.

(This is the simple fee model — cheap-on-all plus fallback-on-escalated. The paper reports 47% of the fee at a 34% escalation rate where this gives 34.3%, because its accounting includes judging pairs in both orders and a conservative reservation for missing usage. Use this for a break-even, not to reproduce a published figure.)

Instrument, per completed task:

1. **Total spend**, decision layer plus generation plus retries.
2. **Wall-clock**, end to end.
3. **Escalation rate**, and escalation precision — of items escalated, how many did the expensive path actually change (`09-confidence-gate.md`).
4. **Retry and rework rate**, before and after. This is where a bad decision layer hides.

If 1, 2 and 3 improve and 4 does not worsen, take the next fork.

## Reported reference points, with their scope

Each figure comes with the boundary its reporter drew. Quoted for order of magnitude, not as a benchmark to hit.

| Claim | Scope stated by the reporter |
|---|---|
| Flights found in 7.1 s for $0.0039 | 90,558 recorded decision-layer input tokens plus a text helper's charge. Browser infrastructure excluded; clock starts after the first page observation; it *finds* flights, it does not book them. |
| 1,018 papers classified for $0.08, 256 ms median | A summarisation model produced the abstracts first. |
| 500 emails triaged for 3.5 cents | Classification step only. |
| Session compacted ~1M → 86K tokens in ~1 s | Relevance scoring of tool calls, not summarisation. |
| 5-18x faster safety classification, better accuracy | The classifier step, not a whole agent run. |
| 193.6x faster, 444.6x cheaper | **Vendor's own workflow evals.** Every model gets the same workflow with no harness engineering allowed — better methodology than most — but the workflows were built by the vendor's own capabilities team, and the reference answer is an average of two frontier models, which biases toward them. The vendor calls these the high end of realistic gains. |
| $0.0002 vs $0.032 per desktop-control decision, 0.13-0.38 s vs 5.2 s | Per-decision, single reporter. |

Third-party numbers come from the builders named beside them and have not been independently reproduced. Take a tenth of any of them and a loop that runs overnight still gets a different bill.

## What becomes affordable once a decision is cheap

The KV-cache tax explains more of current agent design than it gets credit for. Once it is visible, several things stop looking like design and start looking like scar tissue:

- **Up-front tool declarations.** Tools must be declared in the system message whether or not they are relevant this turn — a permanent context cost, and models are weak at high-cardinality off-policy tool selection anyway. With cheap relevance scoring you can ship hundreds of tools as one-line hints and load schemas on demand.
- **Compaction as summarisation.** It rests on the assumption that every future turn wants one shared state. Drop the assumption and query-aware filtering beats general compression (`05-reranking.md`).
- **Subagents underperforming.** A large share of their cost is deciding what context to pass in and merge back out, not the work. Make that decision cheap and spawning many becomes practical — and you inherit the interesting problems: shared state, write locks, synchronisation.
- **Restart-on-corruption.** Loading relevant old state on demand is the alternative nobody could previously afford.
- **Conditional AGENTS.md.** Load the style guide only for front-end work, the gotchas file only in that subdirectory. Relevance-scored context does not get summarised away at the next compaction the way a loaded skill does.
- **Background read-only tasks.** Dashboards, generated evals, cross-model review are all read-only functions of current repo state. Finding the relevant information is the expensive part; share that across every background task and running many becomes economic.

## Auditing repeated calls before buying speed

An optimised browser runtime cut median protocol calls from 1,092 to 101 and median task time by 25% **using the same models on both sides**. The wins came from reading page state once and not re-predicting on irrelevant animations.

Latency in agents is usually structural, not model-bound. Check the loop before you check the invoice.
