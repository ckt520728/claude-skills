---
name: jev-autoresearch-rsi
description: |
  Build and run a custom autoresearch agent on the Jev-Engineering two-phase workflow. A high-tier planner sets the plan, parallel medium-tier executors work it, and a high-tier auditor (ideally from a different provider) reviews the result, with a replan loop between them. The agent collects real evidence from PubMed, arXiv, ClinicalTrials.gov, a Gemini Notebook / NotebookLM notebook and local PDFs, then writes:
    - an English paper with APA 7 citations
    - a 15-slide PowerPoint deck
    - an interactive HTML deck
    - a zh-TW blog post
  An optional Robin layer (Ghareeb et al., 2026, Nature), on by default, adds the following. Finch is not included.
    - a Crow/Falcon split with a code-measured hallucination guard
    - a counterbalanced pairwise (Bradley-Terry-Luce) hypothesis tournament
    - opt-in parallel trajectories with a consensus filter
    - a ReAct cascade guard and a claim ledger
  Each run merges into an Obsidian "Second Brain" wiki, and a knowledge-base RSI step measures and improves that wiki, keeping only changes that measurably help. A local dashboard (port 8090) shows the graph, the sources, the deliverables, the wiki and the RSI ledger.
  Portable:
    - Providers: Claude, OpenAI or Gemini (OpenAI-compatible), with model tiers set in project.json.
    - Tools: these instructions work in Claude Code, Codex, Gemini CLI, Antigravity or OpenCode.
    - OS: Windows, macOS or Linux.
  Use when the user asks for an "autoresearch agent", "Jev planner/executor/auditor research loop", "research a topic and write paper + slides + blog and update my knowledge base", "知識庫 RSI", "自主研究代理", "Robin multi-agent workflow", "BTL tournament", "Crow/Falcon", or "upgrade my RSI knowledge dashboard with a knowledge base".
  Not for a single article (article-writer), a single deck (soil-deck-pipeline), or a metrics dashboard (dashboard-builder).
---

# Jev Autoresearch RSI

> **The model writes. Code decides what counts as verified. The page only shows what actually happened.**

This skill packages a workflow that was built and run end to end on 2026-11-08. A full demo ran Opus as planner, Sonnet as executor and gpt-6-astra as auditor over 2 loops. It cost US$1.46, every source answered LIVE, it had 0 citation problems, and it added 36 wiki pages.

It extends `rsi-knowledge-dashboard` (same engine core and rules) with:
- the Jev graph
- multi-provider model tiers
- a Second Brain wiki with measured self-improvement
- a house-style blog publisher

## The graph

```
plan (high) ─► collect (code: PubMed · arXiv · ClinicalTrials.gov · NotebookLM · PDFs)
   ▲             └─► notes swarm (medium × N, parallel; claims must cite [E#] keys and grounded numbers)
   │                   └─► [Robin] falcon (high × K, hallucination guard) ─► hypotheses ─► BTL tournament (loop 1)
   │                   └─► draft + code checks + repair (medium)
   │                         └─► audit (high, other provider if available)
   └──── replan on FAIL ◄──────────┘         │ PASS (or loop limit)
                                             ▼
        deliverables in parallel (paper APA 7 · PPTX · HTML deck · zh-TW blog) ─► citation lookup ─► [Robin QC + claim ledger] ─► KB merge ─► KB RSI
```

Every run writes `graph.md`, `checks.md` and `progress.md` (Karpathy agent-graph format), plus `evidence.json`, `plan_loop*.json`, `audit_loop*.json` and `run_report.json`, into its own `outputs/runs/<run_id>/` folder.

## Workflow

### 1. Settle the decisions

Ask only what you cannot default.

| Decision | Default | Where |
|---|---|---|
| Topic | ask | `--topic` / `default_topic` |
| Providers | Claude; add OpenAI/Gemini if keys exist | `.env`, `project.json` → `providers`, `tiers` |
| Tier mapping | see `references/providers-and-tiers.md` | `tiers.high`, `tiers.medium` |
| Loops, budget | 2 loops, US$5 hard cap | dashboard or `--loops --budget` |
| Wiki location | `./knowledge_base` | `--kb-root` (point it into the Obsidian vault) |
| Robin layer | on; 6 candidates; 1 trajectory; consensus 0.5 | `project.json` → `robin`, dashboard, `--no-robin --candidates --trajectories --consensus` |
| Notebook | none | `--notebook <NotebookLM id>` |
| Blog site/author | example.org / blank | `--blog-site --blog-author` |
| Publishing | **only after explicit approval** | always |

### 2. Scaffold

```bash
python <skill>/scripts/scaffold.py ./my-autoresearch --topic "..." --kb-root "<vault>/知識庫/<Project>" \
    --notebook <id> --blog-author "..." --blog-site https://...
```

The script refuses to write into a non-empty folder. It also copies `agents/jev-*.md` into `.claude/agents/`. Then:
- create `.env` from `.env.example`
- set up the project instructions: write `CLAUDE.md` for the project, and an `AGENTS.md` that points to it, for non-Claude tools
- start a `handoffs.md`; see `references/project-init.md`

### 3. Providers: read model ids, never guess them

```bash
uv run --no-project --python 3.12 --with-requirements requirements.txt python run_agent.py --models openai
uv run --no-project --python 3.12 --with-requirements requirements.txt python run_agent.py --models gemini
```

- Put the exact ids in `tiers`, and a price for every paid model in `price_per_mtok`. A paid model without a price is refused, because the budget would not be real.
- Use `model@high` / `model@medium` to set the reasoning effort.
- Ping each model once with a tiny prompt before a real run. A key can list a model and still get HTTP 429 on it because of quota.

### 4. Verification ladder (do not skip steps)

1. `python run_agent.py --check` (spends nothing)
2. Offline tests: `python -m pytest tests -q`. Every check has a case that must fail.
3. Start the dashboard with `start_dashboard.ps1` or `.sh`, then run `uv run --with playwright python tests/browser_smoke.py`.
4. Cheap live run: Haiku or Flash in all roles, 1 loop, under US$0.50.
5. Full run with the confirmed budget.
6. **Read the outputs yourself.** Turn each problem you find into a new check or test before calling the run done. See `references/reading-outputs.md`.

### 5. Run

Either use the dashboard (Start button), or run headless:

```bash
python run_agent.py --topic "..." --loops 2 --budget 5 --planner claude:claude-opus-5-5 \
    --executor claude:claude-sonnet-5-5 --auditor openai:gpt-6-astra
```

**Interactive mode** (to steer each phase from a coding agent):
1. Spawn `jev-planner`.
2. Spawn one `jev-executor` per independent TaskSpec, all in one message.
3. Spawn `jev-auditor`. On FAIL, send its findings back to the planner (at most 3 loops).

On tools without subagents, see `AGENTS.md`.

### 6. Robin layer (optional, on by default)

- Falcon may cite only the code-built citation library.
- Code accepts a claim only if it cites an on-topic, identifier-verified entry and its figures are grounded. The hallucination rate is logged; above 2 % there is one respawn.
- Hypotheses are ranked by a pairwise BTL tournament, with each pairing judged in both orders to cancel position bias. The top 3 go into the paper as hypotheses, never as findings.
- Artifacts, the claim ledger and the QC checklist are in `outputs/runs/<id>/robin/`. A QC FAIL means NEEDS_REVIEW.
- Finch (data analysis) is not implemented and shows as N/A.

See `references/robin-layer.md`.

### 7. Knowledge base and RSI

- `--kb-fitness` measures the wiki: broken links, orphans, unsourced claims, duplicates, single-source concepts and open gaps. Each is a share of its own denominator (`normalised-v2`), so growth alone does not lower the score.
- `--kb-improve` proposes changes (repair link, merge concepts, link orphan), tests each on a scratch copy, and promotes it only if:
  - the targeted metric falls,
  - the overall score rises,
  - and no other metric gets worse.
- Every decision is appended to a SHA-256 ledger.
- Open gaps close automatically when a later run's auditor proposes an answer and code verifies it: PASS audit, at least 2 sources with one primary, and grounded figures.
- The engine edits only inside `<!-- autoresearch:begin/end -->` blocks.

See `references/knowledge-base-rsi.md`.

### 8. Publish (gated)

The run writes `blog_publish/`: the post, a homepage teach-card and a sitemap entry.
1. Stage them in a **fresh clone**, fix anything you found when reading the outputs, check the post in a real browser, and commit locally.
2. **Stop and ask.** Push only after the user approves, then confirm the deployment with curl.

See `references/publishing.md`.

## Hard rules

1. Code decides verified. No static PASS; every status comes from a run or a measurement.
2. No fake success. A failing source contributes nothing and says so: `LIVE / FALLBACK / SAVED / UNAVAILABLE`.
3. Models cite `[E#]`, and code builds the APA references. A DOI must match the registered title, year and first author.
4. Every number in the text must appear in the source cited beside it.
5. The auditor never edits deliverables. A high finding forces FAIL even if the auditor said PASS.
6. Spending limits are real: a paid model needs a price, and parallel jobs share the remaining budget.
7. Never overwrite earlier runs. Wiki pages are merged inside managed markers.
8. A wiki change is kept only on measured improvement; otherwise the rejection is logged.
9. Secrets stay in `.env`. Never commit `.env`, `.phi_blocklist.txt`, or run outputs that contain case material.
10. Paid or destructive endpoints accept only same-origin JSON on localhost. Never open CORS.
11. `VERIFIED` means traceable, not clinically correct. A qualified person reviews before use.
12. No git push without the user's explicit approval.

## References

| File | Read when |
|---|---|
| `references/providers-and-tiers.md` | choosing models, effort suffix, prices, auditor on another provider |
| `references/robin-layer.md` | Robin mapping, guard, BTL, consensus, cascade guard, settings, cost, lessons |
| `references/knowledge-base-rsi.md` | wiki layout, fitness formula, promotion rule, Obsidian rules |
| `references/publishing.md` | blog house style, staging, approval gate, deployment check |
| `references/reading-outputs.md` | the checklist for step 6 of the ladder |
| `references/project-init.md` | CLAUDE.md / AGENTS.md / handoffs.md for a new project |
| `references/pitfalls.md` | before starting, and whenever something looks successful too easily |
| `AGENTS.md` | running this in Codex, Gemini CLI, Antigravity or OpenCode |
