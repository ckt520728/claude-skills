# JEV Engineering

A portable agent skill that moves an agent's **non-generative decisions** off the frontier
model onto a cheap calibrated decision layer, and gates them on confidence.

```
[G] generation   -> the frontier LLM, unchanged
[D] decision     -> a System One decision model (Jev), typed answer + calibrated probability
[C] exact rule   -> code: loop caps, spend caps, file existence, blocklists, math, dates
```

Subtraction, not migration. Your planning model stays. Your writing model stays. What leaves
is the class of call that returns a label — *which worker next, is this safe, is this done,
how relevant is this* — that was never worth a frontier token or a second of latency.

## What it covers

| | |
|---|---|
| Model routing | send each step to the cheapest tier that can finish it — across platforms |
| Self-switching | decide whether changing model mid-task actually pays. Usually it does not |
| Input guardrails | injection, abuse and off-policy screening before the LLM sees the input |
| Tool-call gating | 8 capability classes, batched screening, a verdict cache, hard rules first |
| Inbox / ticket triage | the item is the state, the destinations are the criteria |
| Reranking | be the similarity metric on a small corpus, the reranker on a large one |
| LLM evals | judge every run instead of sampling, and escalate when unsure |
| Bulk labelling | map-reduce a decision over a huge table, resumably |
| Real-time control | games, bots, robots, trading — policy at 1-10 Hz, code in the inner loop |
| Composite decisions | DAGs, speculation, funnels and ensembles for what one call cannot express |
| Economics | cost per *completed* task, and what a router actually has to beat |
| The confidence gate | four exits, and a policy that outranks the classifier |

## The tiers

Routing is driven by `skills/jev-engineering/assets/jev/models.json` — data you own, not constants in code. A tier is a **(model, effort)** pair, which is why the same Gemini model appears in two rows.

| Tier | Anthropic | OpenAI | Google |
|---|---|---|---|
| **high** | Claude Opus 5.5 | GPT-6 Astra · Sol-high | — |
| **medium** | Claude Sonnet 5.5 | GPT-5 Terra-high | Gemini 3.6 Flash-high |
| **low** | Claude Haiku 4.5 | GPT-5 Luna-high | Gemini 3.6 Flash-medium |

Three platforms per tier buys cost arbitrage inside a tier, a one-flag fallback when a platform degrades, and data-class policy — `customer_data` can be confined to one vendor, and `secrets` reaches no model at all.

**Prices and model ids ship mostly unset, on purpose.** An unpriced model is never treated as free: `select()` falls back to platform preference order and `Registry.audit()` lists what is missing. Fill them from the providers' live pages before trusting any cost figure.

## Install

**Any agent** — copy the skill folder and point your host's instruction mechanism at it:

```
skills/jev-engineering/SKILL.md        the skill (portable markdown)
skills/jev-engineering/references/     nine playbooks, loaded on demand
```

**Claude Code** — from this directory:

```bash
claude plugin marketplace add "D:/2026 JEV Engineering"
claude plugin install jev-engineering@jev-engineering-local
```

**The runnable layer** — standard library only, Python 3.9+, no `pip install`:

```bash
export TYPESAFE_API_KEY=...        # PowerShell: $env:TYPESAFE_API_KEY = "..."
export JEV_MODEL=jev-1.13.0        # pin it, do not use an alias in production
```

```python
import sys; sys.path.insert(0, "skills/jev-engineering/assets")
from jev import decide, Choice, gate

r = decide(
    state={"command": cmd, "cwd": cwd},
    questions={"risk": Choice(
        instructions="What happens if `command` runs inside `cwd`?",
        criteria={
            "read_only":   "Only reads, lists, searches files or runs tests",
            "local_edit":  "Changes files inside the project that git can restore",
            "destructive": "Deletes data, rewrites git history or touches files outside the project",
            "external":    "Sends data out, pushes, deploys, installs or spends money",
            "other":       "None of the above fits",
        },
    )},
)
decision = gate(r.answers["risk"], tau_act=0.90)   # act / escalate / human / abstain
```

No key? `export JEV_PROVIDER=llm` runs the same calls against any chat model — that is also
how you get the frontier baseline the threshold sweep needs.

## Try it without touching your agent

```bash
cd skills/jev-engineering/assets
python examples/route_models.py                # registry, switch economics, policy comparison
python examples/router.py                      # a standalone dispatcher writing JSON handoffs
python examples/triage_inbox.py inbox.jsonl    # triage with per-destination thresholds
python examples/rerank.py --query "..." --docs docs.jsonl
python examples/tune_threshold.py labelled.jsonl
```

`route_models.py` needs no API key — it reports the registry, the audit, and the arithmetic. Start there.

Run `router.py` twenty times on real goals from your backlog and read the saved files. You
will find bad criteria text before it costs you anything — which is the point of building the
dispatcher as its own script first.

## Claude Code hooks

Two hooks ship ready but **inert**: `.claude/hooks/jev_gate.py` (a ~100 ms PreToolUse gate)
and `.claude/hooks/jev_done.py` (an evidence-gated Stop hook). The wiring is in
`.claude/settings.json.example`.

They are off by default because without a key the gate correctly falls back to `ask` — a
permission prompt on every Bash call, which is a broken install rather than a safe one.
Enable `PreToolUse` first, measure for a week, then add `Stop`.

## Where to start

Do not refactor your agent. Pick the fork it hits most often — usually the tool gate or the
worker dispatch — move that one, and measure three things for a week:

1. **cost per completed task**, not per call
2. **wall-clock per completed task**
3. **how often escalation fired, and how often it was right to**

If all three improve, take the next fork. If escalation never fires, `tau` is too loose and
you have quietly built an unsupervised system.

`skills/jev-engineering/references/14-audit-protocol.md` is the full procedure.

### Before building a router, check it can win

```python
from jev import router_breakeven_accuracy
router_breakeven_accuracy(profiles, routed_tier_mix=mix, beat="escalate from low")
# never beats 'escalate from low': $0.13894/task even at 100% accuracy vs $0.12630/task
```

Beating "always use the high tier" proves almost nothing. The policy to beat is **"start cheap
and climb on failure"**, which needs no router, no registry, and no decision call — and on a
shallow capability gradient it wins at any router accuracy. Routing earns its keep when the
gradient is steep *and* a wasted cheap attempt is expensive.

Run that comparison first. It is the one number that says whether the rest is worth building.

## Honesty about the numbers

Every measurement in the references carries the scope its reporter drew, because a figure
without its scope is marketing. The vendor's headline ratios come from the vendor's own
evals. The paper's benchmark results are the paper's.

And read `UNKNOWNS.md` before quoting a bill: the live API has never been called from this
repo, no threshold here has been tuned against real traffic, and the `$0.042/M` input price
that every cost figure inherits could not be confirmed by direct fetch.

## Contents

```
CLAUDE.md / AGENTS.md    standing brief (same content, two audiences)
UNKNOWNS.md              verified vs assumed vs never-exercised, in four quadrants
HANDOFFS.md              session log
skills/jev-engineering/
  SKILL.md               the skill
  references/00-17       primitives, 12 playbooks, tuning, economics, failure modes,
                         portability, audit protocol
  assets/jev/            decide(), gate(), routing, economics, toolgate, control,
                         compose, bulk -- stdlib only, Python 3.9+
  assets/jev/models.json the model registry: tiers x platforms, prices, api ids
  assets/examples/       cross-platform routing, dispatcher, triage, rerank, threshold sweep
  eval/test_smoke.py     108 behavioural checks against a stub backend -- no key, no network
.claude/                 hooks, checks.sh, inert hook wiring
.claude-plugin/          plugin + local marketplace manifests
```

Everything is verifiable without a key:

```bash
bash .claude/checks.sh    # structure, registry integrity, 108 behavioural checks
```
