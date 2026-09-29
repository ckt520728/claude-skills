---
name: jev-engineering
description: Move an agent's non-generative decisions off the frontier model onto a cheap calibrated decision layer, and gate them on confidence. Use when routing a prompt to a model tier or across platforms (Claude Opus/Sonnet/Haiku, GPT Astra/Sol/Terra/Luna, Gemini Flash), deciding whether to switch model mid-task, screening input for injection/abuse/off-policy content, gating or approving a tool call, triaging an inbox or issue queue, reranking retrieved passages, judging an answer as an eval, labelling a large table row-by-row, driving a real-time control loop (game, bot, robot, trading), deciding whether the agent is confident enough to answer at all, composing a decision that one call cannot express, pricing cost per completed task, or auditing an agent loop for token waste. Also use when the user says "jev", "System One", "decision layer", "confidence gate", "cascade", "escalate when unsure", "model routing", "KV cache tax", or asks why an agent loop costs so much.
---

# JEV Engineering

An agent loop asks two kinds of question. **Generation** questions need words back: write the code, draft the reply, make the plan. **Decision** questions need a label back: which worker next, is this safe, is this done, how relevant is this. Only the first kind needs a frontier model.

The work is **subtraction**, not migration. Nothing moves *off* the LLM that the LLM was built for. You are removing from it a class of call it was never built for.

```
[G] generation   -> the frontier LLM, unchanged
[D] decision     -> a System One decision model (Jev), typed answer + calibrated probability
[C] exact rule   -> code: loop caps, spend caps, file existence, blocklists, math, dates
```

Get the split wrong in the [C] direction and you pay a model to do arithmetic. Get it wrong in the [D] direction and you pay frontier prices for a boolean.

## Why the decision layer must stay outside the context

Routing to a cheaper model failed as a technique for two years, and the reason is not a pricing table. When control returns to the large model it re-reads everything the small model produced: the KV cache is rebuilt, and that term dominates. Route down and back up and you often pay *more* than never routing at all.

A decision model that never enters the conversation deletes the term. It loads no history, generates no tokens, leaves no cache to rebuild. The decision happens *beside* the loop and returns a typed value your code branches on. That is the architectural difference between a decision layer and a cheaper model — and why routing works now when it did not before.

Corollary worth holding: an agent's up-front tool declarations, its compaction strategy, and its reluctance to spawn subagents are all scar tissue from the same tax. Once a decision costs ~100 ms and a few hundredths of a cent, designs that were uneconomic open up. See `references/11-economics.md`.

## The three primitives

Every call is one **state** plus a map of named **questions**, evaluated in parallel against that state.

| Primitive | Use for | Returns |
|---|---|---|
| `Choice` (up to 255 options) | dispatch, routing, action selection, classification | `choice`, `probabilities` per option, `confidence` |
| `Score` (2-10 ordered levels) | relevance, urgency, risk, progress | `score` (fractional, `0`..`n-1`), `probabilities`, `confidence` |
| `Noul` (yes/no) | gates and guards | `noul`, a probability in `[0,1]` — **no `confidence` field** |

Your code owns the thresholds. The model reports belief and certainty; turning belief into an action is business logic, and keeping that split is what makes the system auditable six months later.

A `Noul` near 0.5 is not a bad coin flip. It is the model reporting that your state does not separate the two cases — which in an automation pipeline is worth more than the answer, because it is your escalation trigger.

Wire format, SDK accessors, and state design: `references/00-primitives.md`. Read it before writing a call.

## The seven rules

1. **Meaning lives in the instructions.** The question ID never reaches the model. A key named `is_safe` teaches it nothing; the requirement goes in `instructions` and in each option's criteria text.
2. **One judgment per question.** "Is this destructive and outside the repo" is two questions. Ask both, combine in code.
3. **Describe situations, not moods.** "Deletes data or rewrites git history" is checkable. "Very risky" is not; bare numeric levels are worse.
4. **Give every `Choice` an exit.** An `other` option catches what does not fit and keeps uncertainty honest. `other` is never auto-approved.
5. **Ask everything in one call.** Questions in one request share the state, so adding questions barely moves latency and costs only their own tokens. Speculative branches are nearly free: ask about several possible next actions, then use only the answer for the branch you take.
6. **Keep math, dates and hard rules in code.** The model reads dates as text and miscounts at scale. Compute, then pass the result in as state.
7. **Pin the version and shadow first.** Use `jev-1.13.0`, not `jev-latest`, once thresholds are tuned. Run a period where the decision layer labels and the old path still decides; switch on the confidence bands that matched.

The single hard limit behind rule 5: questions cannot read each other's answers. If a decision depends on a fresh search result, do the search, then send a second request.

## The confidence gate

Confidence is the whole mechanism. It is a statistic of the probability distribution — concentrated means confident, spread means uncertain — and it is *calibrated*: across many calls, higher confidence means higher accuracy. It certifies nothing about any single answer.

That makes it an **escalation signal, not a certificate**. The policy:

```
q >= tau   -> accept the cheap verdict, act
q <  tau   -> escalate: frontier LLM, or a human, or a safe default
irreversible / costs money / externally visible
           -> human, regardless of q
```

One published measurement, to calibrate expectations rather than to copy: at `tau = 0.90` a pooled cascade escalated 34% of items and scored 91.3% against the frontier judge's 91.7% — 99.6% retained — at 47% of its fee. On style-adversarial pairs the same threshold retained only 96.5%. **Thresholds do not transfer.** Pick yours on a local selection set and re-check on held-out items: `references/10-threshold-tuning.md`.

Escalation rate is the health metric. If it never fires, `tau` is too loose and you have quietly built an unsupervised system.

## Where the decisions hide

Audit a loop by counting the model calls in one iteration that produce **no text you keep**. Each one is a **fork**. A generic iteration hides eleven:

```
[D] in scope, or needs a human?          [D] which model tier?
[G] plan the task                         -- LLM
    loop:
[D] which worker acts next?              [C] action limit exceeded?
[D] rebuild the action menu, pick one    [G] generate arguments  -- small LLM
[D] is this tool call safe?              ---- tool executes ----
[D] score the output: keep / summarise / drop
[D] did that move us forward, or are we stuck?
[D] is the goal satisfied?               [C] spend cap hit?
    end loop
[D] did the work actually happen, or does the model just think so?
[D] publish, or hold for approval?
```

Two generation calls. Eleven decisions. Two hard rules. In a default stack all thirteen model-shaped lines run on the same frontier model.

## Working a request

**When asked to audit or refactor an existing loop**, follow `references/14-audit-protocol.md`. Do not refactor the whole loop: take the fork it hits most often — usually the tool gate or the worker dispatch — move that one, measure it, then take the next.

**When asked to build one of the nine decision layers**, open its playbook. Each is self-contained: the state shape, the questions, the gate, the threshold note, and what stays in code.

| Ask | Playbook |
|---|---|
| Route the prompt to a proper model | `references/01-model-routing.md` |
| Screen for injection, abuse, off-policy input | `references/02-guardrails.md` |
| Classify and gate tool calls cheaply | `references/03-tool-gating.md` |
| Triage an inbox, ticket or issue queue | `references/04-inbox-triage.md` |
| Rerank passages by relevance | `references/05-reranking.md` |
| Judge an answer fast and cheap (evals) | `references/06-llm-eval.md` |
| Map-reduce a decision over a huge table | `references/07-bulk-labelling.md` |
| Real-time control: games, bots, robots, trading | `references/08-realtime-control.md` |
| Decide whether to answer at all | `references/09-confidence-gate.md` |
| Route across platforms and tiers (Opus/GPT/Gemini) | `references/15-model-registry.md` |
| Switch model mid-task, or decide not to | `references/16-self-switching.md` |
| A decision one call cannot express | `references/17-composite-decisions.md` |

Cross-cutting: `10-threshold-tuning.md` (calibration protocol) · `11-economics.md` (cost per completed task, and what a router must beat) · `12-failure-modes.md` (read before shipping) · `13-portability.md` (install into Claude Code, GPT-6 Astra, LangChain, or a bare loop).

## Runnable layer

`assets/jev/` is a dependency-free Python package (stdlib only, Python 3.9+). Import it rather than re-deriving any of it.

| Module | What it gives you |
|---|---|
| `client`, `types` | `decide(state, questions)` over a pluggable provider; `Choice` / `Score` / `Noul` with the seven rules enforced as validation |
| `gate` | `gate()` with four exits, `cascade()`, per-action thresholds |
| `routing` | `models.json` registry, `route_task()`, `worth_switching()`, `self_route()` |
| `economics` | `compare_policies()`, `router_breakeven_accuracy()`, `cascade_economics()` |
| `toolgate` | `ToolGate` — per-capability policy, batched gating, verdict cache, health stats |
| `control` | `ControlLoop` with a null action, tick deadline, stuck detection; `RiskLimits` |
| `compose` | `run_plan()`, `speculative()`, `two_stage_choice()`, `ensemble()`, `debiased_pairwise()` |
| `bulk` | resumable map-reduce labelling with rate limiting and a tail policy |

```python
from jev import decide, Choice

r = decide(
    state={"command": cmd, "cwd": cwd},
    questions={"risk": Choice(
        instructions="What happens if `command` runs inside `cwd`?",
        criteria={
            "read_only":   "Only reads, lists, searches files or runs tests",
            "local_edit":  "Changes files inside the project that git can restore",
            "destructive": "Deletes data, rewrites git history or touches files outside the project",
            "external":    "Sends data out, pushes, deploys, installs from the internet or spends money",
            "other":       "None of the above fits",
        },
    )},
)
a = r.answers["risk"]          # .choice   .confidence   .probabilities
```

Setup, the provider contract, and the `llm` fallback: `references/13-portability.md`.

Test decision logic against a stub provider rather than the live API — `@register_provider("stub")` plus `JEV_PROVIDER=stub` exercises every gate, route and cascade path with no key and no network.

## Before you ship

Three numbers, measured for a week, decide whether the fork was worth moving.

1. **Cost per completed task** — not per call. A cheap decision that sends a worker down the wrong branch costs more than the decision did.
2. **Wall-clock per completed task.**
3. **How often escalation fired, and how often it was right to.**

If all three improve, take the next fork.
