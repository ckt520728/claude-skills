# Driving the `litreview` CLI engine

The `litreview` CLI is the mechanical engine for this skill: multi-source search,
DOI/title dedup, screening, synthesis, and the NotebookLM export bundle. The
methodology (scoring, benchmark comparison, three deliverables) is layered on top
of whatever the CLI returns.

## Project location & install

Project root: `C:\Users\user\2026 Literature reveiw agent`

```powershell
cd "C:\Users\user\2026 Literature reveiw agent"
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e ".[llm,dev]"          # [llm] adds Anthropic-assisted screening/synthesis
Copy-Item .env.example .env          # set NCBI_*, OBSIDIAN_VAULT_PATH, ANTHROPIC_API_KEY
```

If not installed as a console script, run it as a module with the src layout:
`$env:PYTHONPATH="src"; python -m litreview --help`

## Configuration (`.env`)

| Variable | Effect |
|----------|--------|
| `NCBI_API_KEY`, `NCBI_EMAIL` | PubMed rate limits |
| `OBSIDIAN_VAULT_PATH` | enables the `obsidian` source (keyword search over the vault) |
| `ANTHROPIC_API_KEY` | enables LLM screening + synthesis (else keyword/template fallback) |
| `LITREVIEW_MODEL` | defaults to `claude-opus-4-8` |
| `LITREVIEW_DATA_DIR` | where run folders are written (default `./runs`) |

## Pipeline: search → dedup → screen → synthesize → push

```powershell
# 1. Search (all three sources by default; dedups by DOI then normalized title)
litreview search "closed-loop DBS depression EEG biomarker" --sources pubmed,arxiv,obsidian --limit 60 --year-min 2024

# 1b. Per-source query overrides (precision): MeSH-tagged for PubMed, plain terms for arXiv.
#     The positional query is the fallback for any source without an override.
litreview search "wearable older adults cognition" `
  --pubmed-query '("Wearable Electronic Devices"[MeSH] OR wearable*[tiab]) AND ("Aged"[MeSH]) AND ("Cognition"[MeSH] OR "Gait"[MeSH])' `
  --arxiv-query  'wearable sensor older adults cognition gait EEG' `
  --sources pubmed,arxiv --limit 60 --year-min 2022

# 2. Screen against inclusion criteria (marks include / exclude / needs-review)
litreview screen runs/<run> --criteria "human subjects; MDD; stimulation or biomarker; quantitative outcome"

# 3. Draft the review (writes review.md with evidence table + reference list)
litreview synthesize runs/<run>

# 4. Export sources to NotebookLM (writes notebooklm_export/ + prints push commands)
litreview push runs/<run>

# ...or the whole chain at once
litreview pipeline "<topic>" --criteria "<criteria>" --push

litreview list                        # list saved runs
```

## Where the data lives

Each `search` creates a **run folder** under `runs/`:

- `meta.json` — the query and stamp
- `papers.json` — every deduped paper (title, authors, year, abstract, doi, url,
  source, and — after screening — `include`/`screen_reason`)
- `review.md` — the synthesized draft (after `synthesize`)
- `notebooklm_export/` — per-paper markdown, `sources.txt` URL manifest, and
  `PUSH_INSTRUCTIONS.txt` (after `push`)

**To add the LitPilot judgment layer:** read `papers.json` from the run, compute
the 0–100 relevance score and the benchmark read per `output_template.md`, then
build the `.xlsx` workbook and the chart per `comparison_outputs.md`. The CLI gives
you clean, deduped, screened inputs; this skill turns them into the comparative,
benchmark-aware deliverables.

## Graceful degradation (matches the CLI's design)

- No `ANTHROPIC_API_KEY` → screening/synthesis fall back to keyword/template mode.
- No `OBSIDIAN_VAULT_PATH` → the obsidian source returns nothing (not an error).
- One source timing out → the others still return; the failure is reported, not fatal.

## Pushing to NotebookLM

`litreview push` prepares the bundle and prints the commands. Two supported paths:

1. **`nlm` CLI** — `nlm login`, then add each URL from `sources.txt`.
2. **notebooklm-mcp** (from Claude Code) — `notebook_create`, then `source_add`
   (`source_type='url'` per line, or `source_type='file'` per `.md` in the bundle).
