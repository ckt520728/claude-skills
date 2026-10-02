# AGENTS.md — 2026 JEV Engineering

The same brief as `CLAUDE.md`, for agents that read `AGENTS.md`: GPT-6 Astra and above,
Cursor, Windsurf, Codex, Aider, or anything else pointed at this directory.
If you read `CLAUDE.md`, you have this already — the two are kept in step deliberately.

## What this repo is

It builds **`jev-engineering`**, a portable skill that moves an agent's non-generative
decisions off the frontier model onto a cheap calibrated decision layer, and gates them
on confidence.

```
[G] generation   -> Phase 2：medium/low executor
[D] decision     -> a System One decision model (Jev), typed answer + calibrated probability
[C] exact rule   -> code: loop caps, spend caps, file existence, blocklists, math, dates
```

**v1.2 兩階段政策。** Phase 1 由 high agent 分析、決策與配置，僅回傳結構化任務規格；不得生成文章、程式碼、patch 或其他成品。Phase 2 由 medium/low agent 執行並驗收。Jev 保留為結構化決策層，八類工具能力全部保留。high／不確定的執行需求退回重新規劃，不啟動 high executor。

細節見 `skills/jev-engineering/references/18-two-phase-workflow.md`；`workflow.py` 提供可執行介面，根目錄 `agents/` 提供 Claude Code 的 planner 與兩種 executor。宿主須實際選擇模型並接上工具 gate；提示詞角色不等於強制隔離。模型、價格或省費成效不得虛構。

## Read this first

`skills/jev-engineering/SKILL.md`. It is plain markdown with no host-specific tooling
assumed — frontmatter is `name` and `description` only. Load it into whatever mechanism
your host uses for standing instructions: a system-prompt appendix, a rules file, a
workspace doc. The nine use-case playbooks in `references/` load on demand; the table at
the bottom of `SKILL.md` says which file answers which ask.

## Using the runnable layer

Standard library only, Python 3.9+, no install step:

```python
import sys; sys.path.insert(0, "skills/jev-engineering/assets")
from jev import decide, Choice, Score, Noul, gate, cascade   # the core
from jev import route_task, worth_switching, self_route      # routing across tiers/platforms
from jev import ToolGate, ControlLoop, RiskLimits            # gating and control
from jev import run_plan, speculative, ensemble              # composite decisions
from jev import compare_policies, router_breakeven_accuracy  # economics
```

The model registry is `assets/jev/models.json` — **data you own**. Tiers span Anthropic,
OpenAI and Google; a tier is a `(model, effort)` pair. Prices and `api_id`s ship mostly unset,
and the code refuses to guess: an unpriced model is never cost-ranked, and `Model.callable_id`
raises rather than sending a display name. Run `Registry.load().audit()` to see what is missing.

```bash
export TYPESAFE_API_KEY=...      # or: export JEV_PROVIDER=llm  (any chat model instead)
export JEV_MODEL=jev-1.13.0      # pin it
```

`references/13-portability.md` has the provider contract, the three integration points
for a non-Claude host, and the error table.

## Rules that apply to any change here

1. `assets/jev/` stays dependency-free and stdlib-only — it runs inside hooks.
2. Gates fail to `ask`, never to `allow`.
3. `other` is never auto-approved; `external` always reaches a human, whatever the confidence.
4. Hard rules run in code before any model call.
5. Thresholds are named constants in code, never buried in a prompt or a framework default.
6. The seven rules in `SKILL.md` are the spec for every example. `assets/jev/types.py`
   enforces three of them as validation, so a bad example fails loudly rather than quietly.
7. Never invent a price or a model id to make a demo work. Synthetic prices are labelled
   `SYNTHETIC` in `price_source`; real ones carry a source and a date.
8. Any table reporting dollars per task reports completion rate in the same table.

## Before calling anything done

```bash
bash .claude/checks.sh        # structure, registry, 既有與兩階段行為檢查, compilation
```

Test decision logic against a stub provider rather than the live API — register one with
`@register_provider("stub")` and set `JEV_PROVIDER=stub`. `eval/test_smoke.py` pins the whole
decision matrix that way: which capability at which confidence yields which verdict, which
signal escalates a route, when a switch pays. Add to it whenever you add a threshold.

## Verification standard

The source material is one paper plus four X articles, and the articles contain at least
one API error the official docs contradict. `docs.typesafe.ai` wins every disagreement;
`UNKNOWNS.md` records which claims are verified, which are vendor-reported, and which are
assumptions. When you cannot check something, say it is unverified rather than repeating
the article.

Every measurement cited in the references carries the scope its reporter drew. Keep it
attached — a figure without its scope is marketing.

## Hooks are inert by default

`.claude/settings.json` has no hooks block; the wiring is in `settings.json.example`.
This is Claude-Code-specific machinery and safe to ignore on another host — the skill,
the playbooks, and the Python package do not depend on it.
