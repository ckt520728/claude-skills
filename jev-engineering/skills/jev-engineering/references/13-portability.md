# 13 — Portability: installing the layer in any agent

The skill is host-agnostic on purpose. `SKILL.md` is plain markdown with no host-specific frontmatter beyond `name` and `description`, and the runnable layer is stdlib-only Python behind one function.

## Setup

```bash
export TYPESAFE_API_KEY=...          # Windows PowerShell: $env:TYPESAFE_API_KEY = "..."
export JEV_MODEL=jev-1.13.0          # pin it (rule 7)
```

Note the distinction: `JEV_MODEL` is the *decision layer* — the thing answering the questions.
The models it routes *to* live in `assets/jev/models.json` and are never set by an environment
variable, because a routing table is not a single value (`15-model-registry.md`).

No `pip install` is required — `assets/jev/` uses `urllib` from the standard library. The official SDKs (`typesafe-sdk` for Python, `@typesafe-ai/sdk` for JS/TS, both reading `TYPESAFE_API_KEY`) are an alternative, not a prerequisite. The endpoint is also reachable through the Vercel AI Gateway and OpenRouter if you would rather not add a vendor directly.

Put `assets/` on the path, or copy `assets/jev/` next to your agent:

```python
import sys; sys.path.insert(0, "skills/jev-engineering/assets")
from jev import decide, Choice, Score, Noul, gate, cascade
```

## The provider contract

`decide()` dispatches on `JEV_PROVIDER` (or an explicit `provider=` argument). A provider is one callable:

```python
def provider(state, questions, model, timeout) -> dict
    # returns the documented wire shape:
    # {"model": str,
    #  "answers": {qid: {"type": "choice"|"score"|"noul",
    #                    "choice"/"score"/"noul": ...,
    #                    "confidence": float,          # absent for noul
    #                    "probabilities": {...}}},
    #  "usage": {"input_tokens": int, "output_tokens": int}}
```

Three ship:

| `provider` | Backend | Use for |
|---|---|---|
| `jev` (default) | `POST api.typesafe.ai/v1/systemone` | production |
| `llm` | any OpenAI-compatible or Anthropic chat endpoint, strict JSON out | no key, air-gapped, or comparing against a frontier baseline |
| `local` | `providers/local.py` — a calibrated scorer, no key, no network | no key, air-gapped, zero-cost, or the shadow period of rule 7 |

## Running with no key at all

`local` ships working. It is not a stub and not a placeholder.

```bash
export JEV_PROVIDER=local
export JEV_CALIBRATION=~/.jev/calibration.json   # optional, but see below
```

Why this is a real option and not a consolation prize: the argument in `SKILL.md` for a
separate decision layer is about the **KV-cache tax**. What deletes that term is that the
decision happens *beside* the loop and returns a typed value your code branches on. That
property is architectural — it does not name a vendor. A function call satisfies it as
completely as an HTTP call does, and costs less:

| | `jev` | `llm` | `local` |
|---|---|---|---|
| latency | ~100ms | seconds | ~0.1ms |
| cost per decision | fractions of a cent | frontier prices | zero |
| offline | no | no | yes |
| calibrated | by the vendor | **no — self-reported, and known overconfident** | by you, against your labels |

Note the `llm` row. Reaching for a frontier model because you have no decision-layer key
reintroduces exactly the cost the layer exists to remove. Use it as a baseline to measure
against, not as a substitute.

### How `local` scores

Rule 1 says *meaning lives in the instructions* — the question id never reaches the model, and
every option must carry criteria text that genuinely describes it. `local` takes that
literally and scores the state against **each option's own criteria**. A term appearing in one
option's criteria is discriminative and weighs 1.0; a term appearing in every option's criteria
is noise and weighs 1/n. No lexicon is baked in: the vocabulary is the spec you already wrote.

Which means a badly specified `Choice` — bare option names, vague criteria — scores badly here
in a way it would not against `jev`. That is a feature. It fails in the direction of the rule.

### What it is honestly not

It has no world knowledge, no synonymy, and no negation handling. On wording that does not
overlap your criteria it will be wrong.

That is survivable **only because of calibration**. `jev/calibration.py` measures how often
each confidence band is actually right and reports accordingly, so an untuned band escalates
instead of acting. Read `10-threshold-tuning.md` before trusting any number it produces.

A mediocre calibrated layer is safe. A strong uncalibrated one is not.

Register your own:

```python
from jev import register_provider

@register_provider("stub")
def _stub(state, questions, model, timeout):
    return {"model": "stub", "usage": {"input_tokens": 0, "output_tokens": 0},
            "answers": {q: {"type": "choice", "choice": next(iter(spec.criteria)),
                            "confidence": 1.0, "probabilities": {}}
                        for q, spec in questions.items()}}
```

The `llm` provider matters beyond fallback: it is how you run the shadow period of rule 7 with the *old* path as the labeller, and how you compute the frontier baseline the sweep in `10-threshold-tuning.md` needs.

Its confidence is **derived**, not native — `q = max(p)` over probabilities the chat model self-reported. Self-reported probabilities are known to be overconfident, so a threshold tuned on `llm` does not transfer to `jev`. Re-tune when you switch. The provider is a compatibility shim, not an equivalent.

## Claude Code

Wired in this project already:

```
.claude/settings.json      PreToolUse (Bash) -> jev_gate.py ; Stop -> jev_done.py
.claude/hooks/jev_gate.py  100 ms safety gate, hard rules first, ask-on-error
.claude/hooks/jev_done.py  evidence-gated stop, checks.sh first, turn cap in code
.claude/checks.sh          prints the objective evidence the stop hook judges
.claude-plugin/plugin.json so `claude plugin install` picks up the skill
```

The vendor also publishes a skill pack:

```bash
claude plugin marketplace add typesafe-ai/skills
claude plugin install typesafe@typesafe-ai
```

It teaches the API and the batch-questions pattern. It does not replace this skill's audit protocol, playbooks, or tuning discipline — and it does not turn the coding agent into a decision model.

## GPT-6 Astra and other agent frameworks

Nothing host-specific to do. Three integration points, in order of how much they buy:

1. **A tool the agent can call.** Expose `decide()` as a function tool. Cheapest to wire, weakest guarantee — the agent chooses whether to consult the gate, which means the gate is advisory.
2. **A pre-execution middleware.** Run `ToolGate.check()` in your executor before dispatching any tool call, so the agent cannot route around it. This is where `03-tool-gating.md` belongs.
3. **The loop's own control flow.** Worker dispatch, stuck detection, completion, compaction, and tier selection called from your loop rather than from the model. This is where the savings actually are.

The routing layer is deliberately host-agnostic in the same way: `route_task()` returns a `Model` with a `callable_id`, and *your* code makes the call. Nothing here wraps a provider SDK, so the same registry serves a Claude Code hook, a GPT-6 Astra agent loop, and a bare Python script — and a platform outage is one `available: false` away from being routed around everywhere at once.

Copy `SKILL.md` and `references/` into whatever the host's instruction directory is — `AGENTS.md`, a system prompt appendix, a Cursor rule, a Windsurf workspace file. The prose assumes no Claude-specific tooling.

## LangChain

```python
from langchain.agents import create_agent
from langchain_typesafe.experimental.middleware import AutoModeMiddleware
agent = create_agent("openai:gpt-5.6-luna", middleware=[AutoModeMiddleware(tools=["bash"])])
```

`AutoModeMiddleware` is the tool gate; `ModelRouterMiddleware` is the router (`01-model-routing.md`). Both hide their thresholds — read the defaults before trusting either where money is involved, and prefer an explicit `decide()` call when you need the threshold in your own code where you can tune and audit it.

## A bare loop, no framework

The minimum viable install is one call in the place the loop currently asks the LLM a yes/no question:

```python
r = decide(state=loop_state, questions={"done": Noul(
    instructions="Every deliverable named in the goal now exists.")})
if r.answers["done"].noul >= 0.90 and artifacts_exist_on_disk():
    break
```

Start with the fork the loop hits most often. Measure. Take the next.

## Error handling, uniformly

`decide()` raises `JevError` with `.status` on a non-2xx, and retries 429/529 with exponential backoff and jitter. Caller decides the fallback, because the right fallback is fork-specific: `ask` for a gate, the null action for a control loop, `needs-human` for triage, the frontier path for an eval.

| Status | Meaning | Fix |
|---|---|---|
| 401 | bad key | replace `TYPESAFE_API_KEY` |
| 422 | validation failure | check the named request field against your question spec |
| 429 | rate limited | back off; lower concurrency if sustained |
| 529 | overloaded | back off, retry later |
