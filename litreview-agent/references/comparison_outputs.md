# Comparison outputs — Excel workbook + visualization

Beyond the written digest, a full run produces a shareable spreadsheet and a
visual. Keep both clean and self-explanatory — a PI should understand them without
reading the chat. When the `litreview` CLI is used, `litreview synthesize` writes a
`review.md` with an evidence table + reference list; build the workbook and chart
below on top of that run's `papers.json`.

## A. Excel comparison workbook (.xlsx)

Create a workbook named like `litreview_<topic-short>_<YYYY-MM-DD>.xlsx` with these
sheets:

### Sheet 1 — "Ranked papers"
One row per screened paper that cleared the criteria, sorted by relevance (high to
low). Columns: Rank · Relevance (0–100) · Tier (High/Medium/Low) · Title · First
author (+year) · Type (RCT/open-label/case/preprint/review) · N · Headline result ·
Why relevant · Link.

Formatting: freeze the header row; enable autofilter; colour the Tier cells (High =
green, Medium = amber, Low = grey); widen Title/Headline columns.

### Sheet 2 — "Benchmark comparison"
One row per quantitative finding. Columns: Finding · Paper (first author, year) ·
New value · Field benchmark · Delta (new − benchmark, or "n/a") · Read (▲/≈/▼ +
one-line caveat).

Formatting: colour the Delta cells on a red-white-green scale; bold the "Read"
column. Do not invent numbers — leave "not reported" where a value is missing.

### Sheet 3 — "Benchmarks (reference)"
Copy the benchmark table from the profile, so the sheet is self-documenting.

Build it with openpyxl or pandas + openpyxl. Keep number formats sensible
(percentages as %), and add a title cell with the topic, date range, and source
count at the top of Sheet 1.

## B. Visualization

Produce ONE of the following (chart is the default; dashboard if the user wants
something richer):

- **Benchmark comparison chart (default).** A grouped bar chart: for each metric
  (response, remission, improvement), one bar for the field benchmark and one for
  the new finding(s), with the benchmark drawn as a clear reference. Save as PNG
  (matplotlib). Title it with the topic and date range; label axes; keep a clean
  palette (benchmark in teal, new findings in gold).

- **Mini HTML dashboard (optional).** A single self-contained `.html` file with the
  ranked table, the benchmark chart, and coloured relevance tags. Inline styles; no
  external dependencies. (This can also be published as an Artifact.)

Always present the generated files to the user (the `.xlsx` and the chart/HTML) in
addition to the in-chat digest.

## Naming & delivery
- Name files with the topic and date so weekly runs don't overwrite each other.
- On scheduled weekly runs (Mondays 18:00), attach/share these files as the
  "update", not just the chat text — and push the sources to NotebookLM.
