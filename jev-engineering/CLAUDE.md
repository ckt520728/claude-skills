# 2026 JEV Engineering

Builds and maintains **`jev-engineering`**: a portable agent skill that moves an agent's
non-generative decisions off the frontier model onto a cheap calibrated decision layer,
and gates them on confidence.

The skill is the product. This repo is its workshop.

`AGENTS.md` is the same brief for non-Claude agents. Keep the two in step.

## The one idea

```
[G] generation   -> Phase 2：medium/low executor
[D] decision     -> a System One decision model (Jev), typed answer + calibrated probability
[C] exact rule   -> code: loop caps, spend caps, file existence, blocklists, math, dates
```

**v1.2 兩階段政策。** Phase 1 由 high agent 分析、決策與配置，僅回傳結構化任務規格；不得生成文章、程式碼、patch 或其他成品。Phase 2 由 medium/low agent 執行並驗收。Jev 保留為結構化決策層，八類工具能力全部保留。high／不確定的執行需求退回重新規劃，不啟動 high executor。

細節見 `skills/jev-engineering/references/18-two-phase-workflow.md`；`workflow.py` 提供可執行介面，根目錄 `agents/` 提供 Claude Code 的 planner 與兩種 executor。宿主須實際選擇模型並接上工具 gate；提示詞角色不等於強制隔離。模型、價格或省費成效不得虛構。

## Layout

```
skills/jev-engineering/
  SKILL.md              the portable skill. Host-agnostic markdown, frontmatter is name + description only
  references/00-18      progressive disclosure: primitives, 12 use-case playbooks, tuning, economics,
                        failure modes, portability, audit protocol
  assets/jev/           stdlib-only Python (see the module table below)
  assets/jev/models.json  THE MODEL REGISTRY -- data, edited often, prices mostly unset
  assets/examples/      runnable: router, triage, rerank, threshold sweep, cross-platform routing
  eval/test_smoke.py    既有與兩階段行為檢查 against a stub backend -- no key, no network
.claude/
  hooks/jev_gate.py     PreToolUse gate -- hard rules in code, then a ~100ms classification
  hooks/jev_done.py     Stop hook -- turn cap, then checks.sh, then a verdict on printed evidence
  checks.sh             the objective evidence the Stop hook judges; runs test_smoke.py
  settings.json.example the hook wiring, inert by design (see below)
UNKNOWNS.md             what is verified, what is assumed, what would change the design
HANDOFFS.md             session log; one entry per working session
```

| Module | Holds |
|---|---|
| `client`, `types` | `decide()`; `Choice` / `Score` / `Noul` with rules 1, 3, 4 enforced as validation |
| `gate` | four exits, `cascade()`, per-action thresholds |
| `routing` | the registry, `route_task()`, `worth_switching()`, `self_route()` |
| `economics` | `compare_policies()`, `router_breakeven_accuracy()`, `cascade_economics()` |
| `toolgate` | `ToolGate`: per-capability policy, batched gating, verdict cache, health stats |
| `control` | `ControlLoop`, `RiskLimits`, `classify_regime()` |
| `compose` | `run_plan()`, `speculative()`, `two_stage_choice()`, `ensemble()`, `debiased_pairwise()` |
| `bulk` | resumable map-reduce labelling with rate limiting and a tail policy |

## Invariants

These are load-bearing. Changing one is a decision to record in `UNKNOWNS.md`, not a tidy-up.

1. **`assets/jev/` stays dependency-free and stdlib-only.** It runs inside hooks, where adding
   a dependency is a real cost. Verified Python 3.9+ — no runtime `X | Y` unions, no `match`.
2. **Hooks fail to `ask` / `stop`, never to `allow`.** A gate that allows on error is worse than
   no gate; one that denies on error makes the agent unusable when the network blips.
3. **`other` is never auto-approved, and `external` always reaches a human** regardless of
   confidence. Policy outranks classification.
4. **Hard rules run in code before any model call.** The model trusts whatever text is in its
   state, and a command can be written to mislead a classifier.
5. **Thresholds live in named constants in code**, never inside a prompt or a middleware default.
   The model reports belief; turning belief into an action is business logic.
6. **The seven rules in `SKILL.md` are the spec** for any example added here. `assets/jev/types.py`
   enforces rules 1, 3 and 4 as validation, so an example that violates them fails loudly.
7. **`models.json` is data the user owns.** Never invent a price or an `api_id` to make a demo
   work — an unpriced model falls back to platform preference order and `Registry.audit()`
   reports it. Synthetic prices in examples are labelled `SYNTHETIC` in `price_source`.
8. **Completion rate travels with cost.** Any table reporting dollars per task reports what
   share of tasks finished, in the same table. Folding completion into the denominator makes
   the weakest tier look best every time.

## Hooks ship inert, on purpose

`.claude/settings.json` has no `hooks` block. The wiring is in `settings.json.example`.

Two reasons, both learned the hard way in this repo: without `TYPESAFE_API_KEY` the gate
correctly falls back to `ask`, which means a permission prompt on *every* Bash call — a broken
install, not a safe one. And hook commands resolve against the session's working directory, so
a bare relative path breaks the moment the agent `cd`s into a subdirectory; the example uses
`$CLAUDE_PROJECT_DIR`.

Enable one hook at a time and measure it. `PreToolUse` first — higher frequency, cheaper mistake.

## Working here

**Verify against the live docs, not the corpus.** The source material is a paper plus four X
articles, and the articles contain at least one API error the docs contradict (see
`UNKNOWNS.md`). `docs.typesafe.ai` wins every disagreement. When you cannot reach it, say the
claim is unverified rather than repeating the article.

**Run `bash .claude/checks.sh`** before calling any change done. It checks structure, imports,
registry integrity, the 既有與兩階段行為檢查, and that every hook and example compiles.

**Add a behavioural test for anything with a threshold in it.** `eval/test_smoke.py` runs
entirely against a stub provider, so every gate, route, cascade and control path is testable
with no key and no network:

```python
import sys; sys.path.insert(0, "skills/jev-engineering/assets")
from jev import register_provider
@register_provider("stub")
def stub(state, questions, model, timeout): ...   # return the wire shape
# then: JEV_PROVIDER=stub
```

The suite is the reason a threshold change is safe to make: it pins the *decision matrix*
(which capability at which confidence produces which verdict), not just that the code runs.

**Verify a formula against its implementation, not against a memory of it.** The switch
economics in `references/16` are stated as an inequality and `test_smoke.py` checks the
implementation agrees with it on five price pairs. A documented formula that nothing
executes is a comment.

**Cite measurements with their scope.** Every number in the references carries the boundary its
reporter drew (`references/11-economics.md`). A figure without its scope is marketing; strip the
scope and the reference stops being trustworthy.

**Prefer editing a playbook over adding one.** Fifteen reference files is already near the limit
of what stays legible. New material usually belongs inside an existing playbook, co-located with
the concept it qualifies.

## Suggested skills

- `map-vs-territory` / `blindspot-pass` — before a change to the skill's structure or claims.
- `grilling` — when a design decision here is genuinely unresolved. Facts get looked up; decisions
  get put to the user.
- `writing-great-skills` — before editing `SKILL.md`. Watch for **sediment** (stale layers) and
  **duplication** between `SKILL.md` and the playbooks; the ladder is the cure.
- `handoff` — at the end of a session, appended to `HANDOFFS.md`.

## Open questions

Tracked in `UNKNOWNS.md` with what each one would change. The two that matter most: no threshold
in this repo has been tuned against real traffic, and the live API has never been called from
here — every number is either the vendor's, the paper's, or a stub's.
