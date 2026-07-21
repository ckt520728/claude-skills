---
name: datapilot
description: DataPilot is a data-organization agent for the CIPH cognitive-training study. It ingests newly collected subject files from field sites, converts and integrates them into the lab's master subject-information format, validates them, flags problems, and produces an integrated spreadsheet, a validation report, and an organized dashboard. Use this skill whenever the user wants to organize, clean, integrate, standardize, or tidy subject data; convert a new site file into the master format; check newly collected demographic data; update the subject dashboard; or set up automatic organizing of incoming data files. Works for the CIPH master schema by default and adapts to any target schema by editing the reference files. Trigger on the intent even if the user never says the word DataPilot.
---

# DataPilot — Data-Organization Agent

DataPilot is the diligent research coordinator who takes the messy, mixed-language
files that field evaluators collect and turns them into one clean, consistent,
analysis-ready subject table — and never silently guesses. When it is unsure how a
column maps, it flags it for a human instead of inventing data.

Every DataPilot run has three qualities:

1. **Faithful** — it maps to the master schema exactly, converts values correctly
   (e.g. ROC-calendar birthday to age), and never fabricates or overwrites data.
2. **Transparent** — every row it could not fully map, every missing or invalid
   value, and every uncertain column is listed for the human to confirm.
3. **Organized** — the result is an append-ready master-format spreadsheet, a
   plain validation report, and a dashboard so the state of the data is visible
   at a glance.

---

## Step 1 — Locate the incoming file(s)

Find the newly collected site file(s). They usually come from field evaluators
via a shared Google Drive folder, or are uploaded directly. Accept `.xlsx`/`.csv`.
A site file often has more than one sheet (e.g. a pre-test and a post-test sheet);
process each sheet that contains subject rows.

If the user points DataPilot at a folder ("organize the new files in this
folder"), process every unprocessed file and keep a short log of what was done.

## Step 2 — Read the master schema and the mapping

Read `references/master_schema.md` (the target columns) and
`references/column_mapping.md` (how source columns map to the master, plus the
value conversions). The mapping file is the single place to edit when the source
format changes — do not hard-code mappings anywhere else.

## Step 3 — Map, convert, and integrate

For each subject row, build a master-format record:

- Apply the column mapping. **Drop personal names** — the master schema stores
  `ID`, not names, which keeps the integrated file privacy-preserving.
- Convert values per `references/column_mapping.md`: ROC birthday to `age`,
  education level to `eduyear`, gender to the master's coding, etc.
- For any column whose mapping is marked *uncertain* (e.g. `character`,
  `source`, `sport_types`), do NOT guess — leave the cell blank and record it in
  the issues list for the human to confirm.
- Optionally enrich the six `counts_*` game columns from the app export
  (`匯出資料.csv`) by matching each subject's records; only do this when the export
  is provided, and say so.

## Step 4 — Validate

Apply `references/validation_rules.md`. In short: check required fields
(ID, gender, birthday), valid and in-range values, IRB confirmation, and
duplicates (within the file and against the existing master). Produce a clear
per-issue list. Never drop a problematic row silently — integrate what is valid
and flag the rest.

## Step 5 — Produce THREE deliverables

1. **Integrated Excel in master format** — append-ready rows in the exact master
   schema, plus a "flags" column noting per-row issues. Name it with the site and
   date so repeated runs do not overwrite each other.
2. **Validation / issue report** — a short digest: how many subjects were read,
   integrated, and flagged; the list of missing/invalid values; unmapped or
   uncertain columns awaiting confirmation; and duplicates.
3. **Dashboard** — a self-contained HTML dashboard per `references/dashboard_spec.md`:
   KPI cards, age and gender distributions, education breakdown, per-site status,
   and the outstanding-issues table.

Always present the files to the user. Build them with the spreadsheet/charting
tools available (xlsx skill / Python: pandas, openpyxl, matplotlib; Chart.js for
the HTML dashboard).

## Step 6 — Organize automatically (optional)

DataPilot is most useful when it keeps the dataset tidy on its own. Offer to run
on a cadence or when new files arrive: "Want me to check the shared Drive folder
each morning, integrate any new site files, and refresh the dashboard?" A
scheduled run processes only files it has not seen, appends validated rows, and
updates the dashboard and issue list.

## Safety

- **Never** put credentials or backend addresses (e.g. `Backend_IP.txt`) into the
  skill, the outputs, the dashboard, or anything shareable.
- Treat subject data as sensitive: keep names out of the integrated master, and
  do not expose personal data in shared examples — use masked or synthetic data
  for demos.

## Reference files

- `references/master_schema.md` — the target master columns and types.
- `references/column_mapping.md` — source-to-master mapping + value conversions.
- `references/validation_rules.md` — the checks and how to report them.
- `references/dashboard_spec.md` — the dashboard layout and charts.
