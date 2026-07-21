# Dashboard spec — interactive, self-contained HTML

DataPilot generates a single self-contained `.html` dashboard (opens in any
browser, works offline, no server). Use Chart.js and Grid.js from CDN; embed the
organized data as JSON inside the file. Never include names or credentials.

## Global filter bar (updates everything live)
- Site (location), Cohort (group), Gender, Group (character), From-date, To-date, Reset.
- Filters recompute the KPIs, all charts, the subject table, and the per-task views.
- Per-subject game counts are recomputed WITHIN the selected date range.

## KPI cards
Subjects · Game records · Tasks played · Sites · Flagged (highlighted).

## Tabs
1. **Overview** — records-per-task bar, gender donut, activity-over-time line
   (records/month), by-site bar.
2. **By Task** — one clickable card per game (瞬間移動 / 順向點擊 / 路徑終點 /
   方向感 / 圖卡分類 / 對手追緝令). Click a card to drill in: score-distribution
   histogram, plays-over-time line, plays/subjects/avg-score KPIs, and a
   **"Download this task's records (CSV)"** button.
3. **Subjects** — a searchable, sortable, paginated Grid.js table (ID, age,
   gender, eduyear, location, cohort, character, per-game counts, flags) with a
   **"Download current view (CSV)"** button that exports exactly what is filtered.
4. **Data Quality** — issues-by-type bar + a flagged-subjects table (ID + issue).
5. **New Data** — pick a date; see how many records/subjects arrived on/after it,
   a per-subject "new records / latest date" table, and a
   **"Download new records (CSV)"** button. This is the availability-by-date check.

## Rules
- Colour flags amber/red; keep it one screen per tab; tables page/scroll.
- CSV downloads are client-side (Blob) with a UTF-8 BOM so Chinese renders in Excel.
- Regenerate the dashboard each run so it always reflects the latest organized data.
- Optional production upgrade: instead of a static file, publish it as a live
  Cowork artifact wired to the shared Google Drive folder so it refreshes on open
  and can detect newly-arrived files automatically.
