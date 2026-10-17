---
name: research-3d-publication-pack
description: |
  End-to-end "research publication pack" from one research topic:
  (1) a 3-D interactive website (Blender-built models + three.js explorer of a 3-D spectrum such as HHSA H(t, f_c, f_AM), with linked 2-D projections),
  (2) an English review paper with BibTeX and a rendered DOCX,
  (3) a SOIL-structured English HTML slide deck and PPTX deck,
  (4) a Traditional Chinese (Taiwan) homepage blog post in the author's homepage style,
  then staging into the author's GitHub Pages repo.
  The orchestrator runs it as a Jev-engineering two-phase workflow: jev-planner on the high tier plans; every Phase 2 production task (PubMed review, analysis, site, paper, decks, blog, staging) goes to jev-executor-medium subagents; all audit / QA goes to an independent high-tier auditor subagent. Never low.
  Use when the user asks to "build a 3D interactive website plus paper, slides and blog", "做 3D 互動網站＋論文＋簡報＋部落格", "HHSA 3D 網站", "研究成果一條龍發表", "review paper + SOIL deck + 中文部落格", or to redo or extend the HHSA 3-D project for another dataset or topic.
  Not for a single deck (use soil-html-deck or soil-teaching-deck) or a single article (use article-writer).
---

# Research → 3-D site + paper + SOIL decks + 中文部落格

This skill orchestrates the pack. It does not replace the deck skills: it calls `soil-html-deck` and `soil-teaching-deck` for slide design, and adds the data contract, the 3-D explorer, the paper pipeline and the verification gates that the 2026-10 HHSA run proved necessary.

Read before starting:
- `references/deliverable_specs.md`: what each artifact must contain.
- `references/pitfalls.md`: 17 failures from the first run, each with its gate.
- `references/jev_tasks_template.json`: the Phase 1 work queue with the tier assignments.

## Orchestration: Jev-engineering two-phase workflow

The main session is the **orchestrator**. It never writes the deliverables itself. It dispatches, enforces budgets, and runs the verification gates. The roles follow the jev-engineering skill (`references/18-two-phase-workflow.md` in https://github.com/ckt520728/2026-Antigravity/tree/main/.agents/skills/jev-engineering).

| Role | Tier | Claude Code agent | Model / effort | Tools | Produces |
|---|---|---|---|---|---|
| Orchestrator | — | main session | current session | all | dispatch, handoffs, gate results |
| **Planner** (Phase 1) | **high** | `jev-planner` | `opus`, effort `high` | Read, Glob, Grep only | `tasks.json`, `writing_plan.md`, `handoffs.md`; control data only, no drafts or code |
| **Executor** (Phase 2) | **medium** | `jev-executor-medium` | `sonnet` | Read, Glob, Grep, Write, Edit, Bash | one TaskSpec's outputs |
| **Auditor** (after each wave, T15, pre-publish) | **high** | Agent tool, `model: "opus"`, effort `high` | `opus`, effort `high` | Read, Glob, Grep, Bash (runs checks; never edits deliverables) | `qa/audit_wave<N>.md`: command, output and verdict per gate |

Dispatch rules:
1. **Phase 1:** spawn one `jev-planner` subagent at high effort with the user's request, the source paths and `references/deliverable_specs.md`. If the plugin agent is not installed, use the Agent tool with `model: "opus"`, `effort: "high"` and a read-only instruction. The planner does not write files; the orchestrator saves its JSON and Markdown verbatim and runs the plan checks (required fields, dependency order, budgets).
2. **Phase 2:** for each wave, spawn one `jev-executor-medium` subagent per TaskSpec, in parallel inside a wave. If the plugin agent is missing, use the Agent tool with `model: "sonnet"`.
   - Each executor gets only its own TaskSpec and the artifact paths of its direct dependencies, not the whole conversation.
   - Do not use `jev-executor-low` for any task in this skill, including repo staging.
3. **Confirm the actual model** of each subagent before trusting its output. Hosts can override aliases; do not silently accept a different tier.
4. **Acceptance is audited on the high tier.** After each wave, spawn a fresh **high-tier auditor** subagent (`model: "opus"`, effort `high`) that is independent of the executors:
   - It gets only the TaskSpecs, the specs in `references/` and the artifact paths. It never sees the workers' reasoning or self-reports, and it is never the agent that produced the work.
   - It runs that wave's checks from `tasks.json` and the verification gates below on the real files, and saves the evidence to `qa/audit_wave<N>.md`.
   - It does not fix anything. A FAIL goes back to the planner for a replan, and the next wave waits.
   - A worker's "PASS" is not evidence. The orchestrator re-runs at least one of the auditor's gates before moving on.
5. **On failure, replan; never escalate to high generation.** Return the task ID, artifact paths and a short error to the planner. It splits or clarifies the spec, and a medium executor reruns it. There is no high executor. Record side effects already done, so a rerun does not repeat them blindly.
6. If the user runs Phase 2 on another platform, stop after Phase 1 and hand over `handoffs.md`, which states the same tiers.

## Non-negotiable rules

1. **Tiers.** Planner: high. Every production task, whether PubMed or literature review, analysis code, website, paper and BibTeX, HTML deck, PPTX, blog or repo staging, runs on **jev-executor-medium**. **All audit work runs on the high tier**: between-wave acceptance, T15 integration QA, and the pre-publish audit of the staged repo. Never low. (User rulings after the 2026-10 run: low-tier workers fabricated data, broke the explorer and invented author metadata, and the QA pass reported "100% PASS" over all of it.)
2. **No number without a producer.** Every quantitative claim about the demos, in any artifact, comes from a facts file written by code (`templates/demo_facts.py` pattern). The orchestrator reruns the pipeline and diffs the results. Worker self-reports are not evidence.
3. **Targets that are missed are reported, not hidden.** Record FAIL with details, and never `assert` a validation target into a crash. Write the paper to the real result, e.g. "25/30 windows (83.3%), below the 90% target".
4. **Author metadata comes only from the user's homepage or the user.** Do not guess affiliations, emails, funding or IRB numbers; insert visible placeholders `[...]`, which `md_to_docx` highlights yellow. The generative-AI disclosure must describe what the agents actually did.
5. **Privacy.**
   - Real data appears de-identified, under neutral labels ("HRV session A") and relative time.
   - No raw files go in public folders.
   - Scan for file stems, participant codes and calendar dates.
   - Confidential manuscripts under review are excluded entirely.
6. **Publishing gates.**
   - Ask before each `git push`, PR, merge or share.
   - Ask whether the full paper may go into a public repo; that counts as a preprint. The default is a summary only on the site.

## Workflow

### Phase 1: plan (`jev-planner`, high; control data only)
1. Read the user's manuscripts, method code, data, prior artifacts and homepage. Build a source manifest (path, sha256, public policy).
2. Ask only what blocks the plan, in one batch:
   - excluded material;
   - consent and IRB for each dataset;
   - target journal;
   - hosting repo and folder;
   - whether the paper is public.
3. Write `writing_plan.md` by adapting `references/deliverable_specs.md`: topic framing, paper outline with word budgets, 20-slide SOIL outline, site information architecture, cube contract, blog style contract copied from the homepage's latest post.
4. Write `tasks.json` from `references/jev_tasks_template.json`: TaskSpecs, waves, budgets, and acceptance criteria phrased as **checks the orchestrator can run**. Every task has `proposed_tier: "medium"` and `agent: "jev-executor-medium"`.
5. Write `handoffs.md`. Stop here if the user runs Phase 2 elsewhere.

### Phase 2: execute (`jev-executor-medium`), then audit (high-tier auditor)
Waves (one medium executor per task, parallel inside a wave):
1. Literature shards and analysis cubes.
2. Evidence merge and Blender scene.
3. Explorer and paper.
4. Site content, HTML deck and blog.
5. PPTX.
6. Integration QA (high-tier auditor, T15).
7. Repo staging.

Build notes:
- **Analysis**: put the pipeline in `phase2/cube/` (templates: `hhsa_cube.py`, `garmin_preprocess.py`, `demo_facts.py`). Use relative paths only. Write the dense cube under key `H`. Ship the web copies as compact JSON.
- **Blender**: run `blender -b -P templates/blender_build_scene.py` from the Output root. Keep at most about 400 lobes per GLB, plus a hero render and a turntable video.
- **Site**: start from `templates/site/` (`explorer.html`, `assets/js/explorer.js`, `assets/css/site.css`). Edit `DATASET_CONFIGS` (names, badges, guide text written from the facts file). Keep the import map and the `file://` notice.
- **Paper**: write Markdown with `[@key]` citations, then run:
  `python scripts/md_to_docx.py paper/review.md paper/review.docx paper/references.bib`
  It must exit 0. Then convert the DOCX to PDF (Word COM) and read the pages.
- **Decks**: follow `soil-html-deck` and `soil-teaching-deck`. `templates/generate_pptx_example.py` is a working python-pptx example. Render through PowerPoint COM with **absolute paths** and inspect every PNG for overflow.
- **Blog**: copy the homepage's newest post's `:root` tokens and class skeleton. Write Traditional Chinese, 3,500–4,500 characters, ending in an honest ledger.

### Verification gates (the high-tier auditor runs them after each wave; all must pass)
```
npm i playwright-core                       # once, in a scratch folder <pw>
python -m http.server 8000                  # from the Output root
NODE_PATH=<pw>/node_modules node scripts/smoke_test.cjs http://127.0.0.1:8000 site/index.html,site/explorer.html,site/explorer.html?dataset=<id>,...,deck/<Deck>.html,blog/<post>.html shots
python scripts/audit_deliverables.py site blog deck paper/<review>.docx deck/<Deck>.pptx \
    --forbid <confidential IDs> <raw file stems> <calendar dates> --forbid-regex "\bS1\d\d\b" --stale <known-wrong numbers> \
    --link-ignore ../slides/ ../<site_dir>/ ../index.html --class-ignore notes-content
# Links that exist only in the repo layout are skipped here. Run the audit again on the staged
# clone without --link-ignore; there every link must resolve. Both scripts exit 1 on any finding.
```
Then **look at the screenshots** (explorer, every dataset, deck slide 8, the blog) and at the paper PDF pages. Rerun the analysis and diff `demo_facts.json`. Grep the scripts for `C:\\Users\\`.

The auditor also checks what the scripts cannot:
- Does the paper's methods text match the code's actual parameters?
- Are the author, affiliation, funding, IRB and AI-disclosure statements taken from the user's homepage, or left as placeholders?
- Does each cited source support its claim? Does each BibTeX year match its key? Are guidelines cited to the guideline paper?
- Are the demo claims descriptive and paired with a "cannot claim" statement?

### Staging and publishing
```
python scripts/stage_to_repo.py <Output> <repo clone> --site-dir <folder> --blog blog/<post>.html \
    --deck deck/<Deck>.html --pptx deck/<Deck>.pptx --slug <deck-slug>
```
- `paper/` is never copied.
- Then a **high-tier auditor** runs the pre-publish audit on the clone: `git diff --stat` shows only the expected paths, the repo tests pass, and the audit and smoke test pass on the clone served at its root. Commit with the host's attribution lines only after its PASS.
- **Ask** before pushing. Fix the PR description if earlier text overclaims. **Ask** before merging.
- After merging, wait for the Pages build (`gh api repos/<o>/<r>/pages/builds/latest`) and run the smoke test against the live URL.

## Wrap-up
Write a lessons note (symptom → cause → fix) to the user's Obsidian folder when asked, and add any new pitfall to `references/pitfalls.md`.
