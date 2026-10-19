---
name: medicloud-word-capture
description: "Use this skill when a clinician wants to document patient data from the Taiwan NHI MediCloud (健保醫療資訊雲端查詢系統) or a similar web/HIS page into Word: sharper screenshots, a ready-made Word template, batch-placing screenshots at full page width, or converting a pasted web-page table (e.g. 西醫用藥紀錄) into a clean table-free summary. Trigger on: 'MediCloud', '健保雲端', '雲端藥歷', 'screenshots too small/blurry in Word', 'paste patient data into Word', 'reorganize the Word file without a table', '整理成沒有表格的 Word'. Do NOT use to automate or scrape the MediCloud/HIS session itself, and not for research cohort extraction (that needs an IRB-approved data request)."
---

# MediCloud → Word capture toolkit

Turn MediCloud (or any card-authenticated web page) views into readable, searchable Word documents for history writing. Built from a real workflow: the clinician screenshots whole screens and pastes them into Word, which gives tiny, blurry text.

## Hard rules (read first)

1. **Never automate the session.** MediCloud needs the clinician's own 醫事人員卡 + PIN. Do not drive the browser/HIS with scripts or automation, do not look for "API keys" (there are none for individual doctors), and do not store or echo credentials the user may type in chat. The *user* logs in; this skill only processes what they capture afterwards.
2. **Clinical use ≠ research use.** Cloud data is for treating the patient in front of the clinician. For a study cohort, point them to an IRB-approved data request (NHIRD / institutional data warehouse), not to MediCloud.
3. **Source files are read-only.** Every script writes a NEW file and refuses to overwrite. Never edit the clinician's original document.
4. **Patient data stays local.** Outputs contain identifiers. Never commit them to git, never put them in a public repo or wrap-up note. Test with synthetic or de-identified images first.
5. **Do not dump config files** from a HIS install to "look around" — they can hold clinical text or credentials. List names; grep for keys with values masked.

## Why captures look bad (diagnose before fixing)

Inspect the clinician's example `.docx` first (image pixel sizes and on-page size; no need to read patient text):
- Whole-screen 1920×1080 shots shrunk to ~15 cm wide → the data text is ~5 pt on the page.
- No cropping, so browser chrome uses most of the pixels.
- Nothing is real text, so nothing is searchable.

## Capture hygiene (tell the clinician)

1. Zoom the browser to 150–200 % (`Ctrl` `+`), then `Win+Shift+S` and drag a **tight box around the table only**.
2. Prefer text over pictures: click the table, `Ctrl+A`, `Ctrl+C`, paste into Word with *Keep Text Only* (searchable and editable). If the page won't copy: `Ctrl+P` → Save as PDF with *Background graphics*.
3. Word margins **Narrow** (1.27 cm): usable width 18.4 cm portrait / 27.1 cm landscape. Wide tables → landscape section.

## Tools in this skill

### 1. Word template — `assets/MediCloud-健保雲端摘要範本.docx`
Portrait cover page (patient/chart/date/author/purpose fields written as plain labels, five 重點摘要 lines) followed by landscape capture pages with narrow margins, a per-page header (病人／病歷號／查詢日期) and a source/confidentiality footer. Contains **no patient data**.
To make a `.dotx` (double-click opens a fresh copy) use Word COM `SaveAs2(path, 14)` — **14 = .dotx, 15 = macro-enabled .dotm** (a wrong code gives a file Word refuses to reopen). Keep the `.docx` for tooling: `python-docx` cannot open `.dotx`.

### 2. Screenshot batch tool — `scripts/medicloud_batch.py`
```
python scripts/medicloud_batch.py FOLDER --name <patient> --chart <no> [--by <name>] \
       [--top N] [--bottom N] [--left N] [--right N] [--scale 2] [--dry-run] [--out PATH] [--force]
```
Sorts images naturally (`1 …`, `2 …`), strips fixed pixel margins (browser toolbar `--top`, window frame `--left/--right`), auto-trims a plain border, optionally upscales copies, places each image full-width on its own landscape page (headings come from the file names), fills the header and cover. Originals untouched; cropped copies go to `FOLDER/_cropped`; prints effective px/inch per image — **below ~200 px/inch means the capture itself was too small; re-capture at higher browser zoom rather than tweaking options**. Auto-trim keys on the top-left pixel colour, so a coloured page background or a 1 px leftover line defeats it: use the explicit strip options.

### 3. Pasted-table reorganizer — `scripts/medicloud_med_reorganize.py`
```
python scripts/medicloud_med_reorganize.py SOURCE.docx [OUT.docx]
```
For a Word file made by pasting a MediCloud **西醫用藥紀錄** page. Rebuilds a table-free document: banner → **A. by visit date** (site, diagnosis + ICD, one bullet per drug with 用法/用量/給藥日數/餘藥試算/ATC class) → **B. by drug** (dispensing dates). Identical rows are shown once as `×N` with their original 項次, never dropped. It aborts if the table header differs from the expected 12 columns — other tabs (labs, imaging, discharge summaries) need their own column mapping; adapt `COLS`/`parse()`.

Gotchas the script already handles (reuse them when adapting):
- A web paste puts the real data in a **table with merged cells**, and *also* as loose tab-separated paragraphs. Parse the table, not the paragraphs.
- `python-docx` returns the same cell object for every grid position a merged cell spans → de-duplicate by `id(cell._tc)`.
- ROC years: show both forms (115/10/01 → 2026-10-01).
- Drop web-button text from the banner ("請換卡再按我…").

## Verification checklist

- Count by **identifier coverage**, not by bullet count: every source 項次 (1…N) must appear in the output. (A bullet total that happens to equal N can be a coincidence once rows are collapsed.)
- Output has `0` tables and the source file's modified time is unchanged.
- Re-open outputs in Word (COM) to confirm page count/sections — but do not render pages of real patient data into the transcript unless the user asks.
- Re-run the batch tool on synthetic images after any change (a dark 1 px line or coloured background is the usual failure).

## Environment notes (Windows)

- PowerShell 5.1 has no `&&`; nested `foreach` with a trailing `| Format-Table` can raise "empty pipe element" — collect into a variable first.
- Bash heredocs mangle backslashes and CJK paths: write Python to a `.py` file, and pass CJK paths from PowerShell.
- Console is cp950: a CJK file name can *print* as garbage while the file is fine; verify by listing the directory.
- Files the user saves on their desktop session may not be visible to a background Claude session (`Pictures`, `Downloads`, `G:`); ask them to place test files under `Documents`, which is shared, or paste an image into the chat and confirm the `[Image #N]` marker appeared.
