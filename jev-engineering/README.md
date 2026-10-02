# JEV Engineering v1.2

**兩階段處理：high agent 規劃與決策，medium/low agent 負責實際寫作與執行。** Jev 原有決策 primitive、八類工具能力與信心 gate 全部保留。

```text
Phase 1：high planner → 任務規格 → Jev 分配 low/medium → 交接
Phase 2：指定 executor → 工具 gate → 產出 → 獨立驗收
失敗／high 需求／不確定 → 重新規劃，不啟動 high executor
```

第一階段只輸出任務目的、來源、成品參照、驗收條件、依賴與預算；不得生成文章、程式碼或 patch。第二階段使用精簡的任務 context，避免把所有 worker 全文送回高階模型。

入口：[SKILL.md](skills/jev-engineering/SKILL.md)。完整用法：[兩階段工作流](skills/jev-engineering/references/18-two-phase-workflow.md)。

```powershell
python -X utf8 skills/jev-engineering/assets/examples/two_phase.py
```

這個離線示範會驗證 Phase 1 沒有成品、Phase 2 實際寫入後獨立讀回；模型為 stub，不代表真實節省率。

Claude Code plugin 附帶 `jev-planner`（opus、唯讀）、`jev-executor-medium`（sonnet）、`jev-executor-low`（haiku）。載入 plugin 後，可要求「先用 jev-planner 規劃，再依分配交給 medium/low executor」。Python host 使用 `plan_phase()` 與 `execute_phase()` 接入模型及工具 adapter。

角色檔不會自動呼叫 Python。原有 hooks 保持停用；強制 Jev gate 需宿主 middleware。未設定／未驗證的 API ID 回 ask，未定價不宣稱最便宜。實際用量／成本節省尚未量測。

既有底層 API 與以下參考資料保留；其中 high fallback 在新流程中解讀為重新規劃。單獨呼叫決策 primitive 不需要啟動整套兩階段流程。

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

也可直接載入本工作資料夾，啟動新的 session：

```powershell
claude --plugin-dir "D:/2026 JEV Engineering"
```

可攜交付檔位於 `dist/jev-engineering-1.2.0.plugin.zip` 與 `dist/jev-engineering-1.2.0.skill`，由 `python -X utf8 scripts/package.py` 產生；`dist/SHA256.json` 記錄雜湊。plugin ZIP 解壓後可交給 `claude --plugin-dir`；skill ZIP 解壓得到 `jev-engineering/`，放入宿主支援的 skills 目錄。

交付套件只包含可攜 skill、角色及必要說明，工作區專用的 `CLAUDE.md`／hooks 不會自動安裝。完整 `.claude/checks.sh` 在原工作資料夾執行；套件內可直接跑 `skills/jev-engineering/eval/test_smoke.py` 與 `test_workflow.py`。載入新模型角色不會自動接上宿主的 Jev middleware，接線方式見兩階段工作流。

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
