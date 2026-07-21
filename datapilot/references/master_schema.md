# Master subject-information schema (target format)

Based on `subinfo_valid_data_May-2026.xlsx`. Each integrated subject becomes one
row with these columns, in this order:

| Column | Meaning | Type / values |
|---|---|---|
| age | age in years at collection | integer (0–120) |
| gender | subject gender | "F" / "M" (from 女 / 男) |
| ID | subject identifier | string, unique; NO personal name |
| eduyear | years of education | integer (see mapping) |
| source | how the subject was recruited / batch | string (confirm per site) |
| location | site / 據點 name | string (e.g. 東興里) |
| character | subject character/group label | string — mapping UNCERTAIN, confirm |
| sport_types | assigned game/sport type(s) | string — mapping UNCERTAIN, confirm |
| counts_telepotation | game count: 瞬間移動 (A) | integer (from app export) |
| counts_forwardtap | game count: 順向點擊 (C) | integer (from app export) |
| counts_direction | game count: 方向感 (B) | integer (from app export) |
| counts_pathend | game count: pathend | integer (from app export) |
| counts_cardsort | game count: cardsort | integer (from app export) |
| counts_rivalry | game count: rivalry | integer (from app export) |

Notes:
- The master intentionally has NO name column — drop names on integration.
- The six counts_* come from the app export (匯出資料.csv), not the demographic
  file; leave blank if the export is not provided this run.
- A helper column `flags` may be appended to the integrated file to carry
  per-row issues; it is not part of the analysis schema.
