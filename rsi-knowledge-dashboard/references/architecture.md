# Architecture

## Project layout

```
my-dashboard/
  dashboard.html          The page. No build step and no external resources
  project.json            All project settings
  .env                    Secrets (not committed)
  .phi_blocklist.txt      Known identifiers (not committed)
  references/             Your PDFs, plus saved_answers/
  outputs/runs/<run_id>/  One folder per run: deliverables, evidence.json, run_report.json
  .rsi/                   trace.jsonl, playbook.json, ledger.jsonl
  knowledge_agent/
    config.py    Settings and paths
    llm.py       Providers behind one Conversation interface
    sources.py   Evidence collection and citation lookup
    checks.py    Deterministic checks
    render.py    The deliverables, built from text plus evidence metadata
    pipeline.py  The RSI loop
    app.py       Local web server
  run_ui.py, run_agent.py, start_dashboard.ps1, start_dashboard.sh
  tests/test_agent.py, tests/browser_smoke.py
```

## Data flow

1. **Plan.** The model proposes queries. If its answer is unusable, the topic itself is searched.
2. **Collect.** Each source returns `(items, SourceStatus)`. The status records what happened: `LIVE`, `FALLBACK`, `SAVED` or `UNAVAILABLE`. Items containing a known identifier are dropped and counted, never logged.
3. **Write and check.** A conversation produces the paper. `run_checks` runs. Failures go back in the same conversation with their exact messages, up to the repair limit.
4. **Critique.** In later passes a reviewer lists gaps and new queries, more evidence is collected, and the paper gets a bounded revision: keep what is supported, change what the reviewer asked.
5. **Evolve.** A check that failed in one pass proposes a rule, tested in the next pass. See `_evolve` in `pipeline.py`.
6. **Deliverables.** Slides, blog and infographic each get a fresh conversation with the final paper and only the sources it cited.
7. **Look up.** Every cited DOI and arXiv ID is checked online, by title as well as existence.
8. **Status.** `COMPLETED` needs every deliverable verified and no citation problems. Anything else is `NEEDS_REVIEW`, with visible banners on the affected files.

## Why these choices

- **Evidence keys instead of citations.** The model cannot type a reference it did not receive, so fabricated citations are impossible by construction, not just detected later.
- **Separate conversations per deliverable.** Each is re-checked against the evidence, so an error cannot pass silently from the paper into the slides.
- **JSON for slides and infographics.** The same data drives HTML and PPTX, and checks read values rather than layout.
- **No framework or build step.** The page is one file. It opens from disk with a clear message, and works offline when served.
- **No dependency on an agent framework.** Verify-and-repair is about 30 lines, which keeps the template portable. `agy-harness` can wrap it if you want its loop, hooks and tool gate.

## Extending

- **New provider:** subclass `Conversation` in `llm.py` and add a branch in `open_conversation`.
- **New source:** add a function returning `(List[Evidence], SourceStatus)` and a step in `_collect`.
- **New check:** add a function returning `Check` and include it in `run_checks`. A failure message goes straight to the model, so write it as an instruction.
- **New deliverable:** add a spec in `_specs`, a structure function in `checks.py`, a renderer, and a `_make` call.
- **Domain wording:** use `terms` in `project.json`. Do not edit the prompts for one project's vocabulary.
