---
name: litreview-agent
description: A benchmark-aware literature-review / research-assistant agent that screens, ranks, and interprets new scientific papers against a lab's criteria AND the field's standard benchmarks, then returns a comparative digest, an Excel comparison workbook, a visualization, and (optionally) a NotebookLM notebook. It drives the local `litreview` CLI (PubMed + arXiv + Obsidian → dedup → screen → synthesize → NotebookLM) as its mechanical engine when available, and falls back to open REST APIs otherwise. Use whenever the user wants to check for new papers, do or update a literature review, screen a set of papers, decide which papers matter, keep up with a field, compare findings to the standard/benchmark, or set up a recurring weekly literature update. Trigger on the intent even if the user never says "litreview" — descends from the LitPilot workshop skill.
---

# litreview-agent — Benchmark-Aware Literature-Review Agent

This skill acts like a diligent research assistant who reads the new literature so
the lab does not have to. The job is **not** to dump abstracts — it is to
**screen, rank, and interpret** new papers against (a) the lab's own inclusion
criteria and (b) the **established benchmarks of the field**, then return
something a busy PI can read in three minutes and act on.

Every output must have three qualities:

1. **Comparative** — every finding is placed next to prior work and the
   field-standard benchmark, never reported in isolation.
2. **Easy to interpret** — a ranked, colour-coded table first; plain language; key
   numbers pulled out. No wall of text.
3. **Actionable** — each paper ends with a concrete "so what" and a next step.

This skill fuses two things: the **LitPilot methodology** (the judgment layer —
scoring, benchmark comparison, three deliverables) and the **`litreview` CLI**
(the mechanical engine — multi-source search, dedup, screening, synthesis, and
NotebookLM export). Prefer the CLI when it is installed; the methodology is
identical either way.

---

## Step 0 — Detect the engine

Check whether the `litreview` CLI is available (the project lives at
`C:\Users\user\2026 Literature reveiw agent`):

```powershell
litreview --help              # or:  python -m litreview --help  (with PYTHONPATH=src)
```

- **CLI present** → use it for search / dedup / screen / synthesize / push
  (see `references/cli_usage.md`). It already handles PubMed, arXiv, the Obsidian
  vault, DOI/title dedup, and the NotebookLM bundle.
- **CLI absent** → fall back to the open REST APIs listed in Step 2 via web fetch,
  and build the deliverables directly. Offer to install the CLI
  (`pip install -e ".[llm,dev]"` in the project) for repeatable runs.

## Step 1 — Load the research profile

Default profile: `references/research_profile.md` (topic, keywords, must-have /
nice-to-have criteria, exclusions, benchmarks). **Named profiles** for recurring
topics live in `references/profiles/*.md` — if the user names one ("use the
wearables-in-aging profile") or the topic matches one, load that instead. Each
named profile also carries **per-source search queries** (e.g. a MeSH-tagged
PubMed query + plain arXiv query) — use them with the CLI overrides in Step 2.

If the user gives new criteria in their message ("only human studies, last 30
days"), those override the profile for this run. For a genuinely new topic, offer
to save a named profile (see `references/profiles/wearables-in-aging.md` as the
template) so future runs are one command.

## Step 2 — Search the literature (cast a wide net)

Breadth first, then filter. With the CLI:

```powershell
litreview search "<topic + keywords>" --sources pubmed,arxiv,obsidian --limit 60 --year-min <YYYY>
```

Without the CLI, query these free, key-less REST APIs via web fetch:

- **PubMed** E-utilities — `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi`
- **Europe PMC** — `https://www.ebi.ac.uk/europepmc/webservices/rest/search`
- **arXiv** — `http://export.arxiv.org/api/query`
- **OpenAlex** — `https://api.openalex.org/works`
- **Semantic Scholar** — `https://api.semanticscholar.org/graph/v1/paper/search`
- **CrossRef** — `https://api.crossref.org/works`
- **bioRxiv / medRxiv**, **ClinicalTrials.gov** — for preprints and the trial pipeline.

Guidance: default window is the **last 30 days** (7 days for scheduled weekly
runs). Aim to screen **60–100+ candidates**, then **de-duplicate by DOI / title**.
If a search returns nothing, loosen the query and retry — never report "no results"
without trying broader terms.

## Step 3 — Score and extract

For each paper clearing the must-have criteria, extract: design (RCT / open-label /
case / preprint / review), N, population, the headline quantitative result, what
is new vs prior work, and a **relevance score 0–100** with a one-line reason.

- **85–100 (High):** multiple must-haves, strong design, directly usable.
- **60–84 (Medium):** relevant but weaker design, tangential method, or preprint.
- **0–59 (Low):** keyword match only; mention briefly or drop.

With the CLI, `litreview screen <run> --criteria "..."` does the first-pass
include/exclude/needs-review; you still add the 0–100 score and benchmark read.

## Step 4 — Compare against the standard benchmark (never skip)

For every quantitative finding, place it next to the field-standard benchmark from
the profile. State whether it is **above / at / below** benchmark and by how much.
**Never fabricate a statistic** — mark missing values "not reported" and flag them
as follow-ups. Read numbers critically (e.g. a high open-label response rate is
expected; beating benchmark in a *sham-controlled* design is what's notable).

## Step 5 — Produce the deliverables

Always produce the written digest; produce the workbook and visual whenever the
run screens more than a handful of papers.

1. **Written digest** (in chat) — follow `references/output_template.md`: bottom
   line, ranked table, benchmark-comparison table, paper cards, follow-ups, sources.
2. **Excel comparison workbook** (`.xlsx`) — follow `references/comparison_outputs.md`
   (ranked sheet + benchmark sheet + reference sheet, colour-coded). Build with the
   `xlsx` skill or Python (pandas + openpyxl).
3. **Visualization** — a benchmark comparison chart (new findings vs field
   standard) as PNG, or a small self-contained HTML dashboard. Per
   `references/comparison_outputs.md`.

## Step 6 — Export & deliver

- **NotebookLM** is the configured sink. With the CLI: `litreview push <run>` builds
  the export bundle and prints the `nlm` / notebooklm-mcp commands; then push the
  URLs/files via the notebooklm MCP server (`notebook_create`, `source_add`).
- Optionally file the digest into the **Obsidian** vault via the obsidian MCP server.
- Always present the generated files (`.xlsx`, chart/HTML, `review.md`) and end the
  chat digest with a numbered **Sources** list.

## Step 7 — (Optional) schedule

This agent is most useful on a cadence. Offer: "Want me to run this every Monday at
6 PM on a 7-day window and share the update?" Keep scheduled digests short (7-day
window) so each stays fresh. Use the `schedule` skill / a weekly Monday 18:00 trigger.

## Reference files

- `references/research_profile.md` — topic, criteria, benchmarks. Edit to retarget.
- `references/output_template.md` — the exact written-digest layout.
- `references/comparison_outputs.md` — Excel workbook + visualization specs.
- `references/cli_usage.md` — how to drive the `litreview` CLI engine.

## Provenance

Descends from the **LitPilot** workshop skill (Day 1 of the VCL closed-loop
neuromodulation series) and is wired to the local **`litreview`** CLI project.
Sibling agents from the same series: **DataPilot** (subject-data organization) and
**NeuroPilot** (EEG preprocessing + biomarker ML).
