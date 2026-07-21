# Source -> master mapping & value conversions

Edit THIS file when the incoming format changes. DataPilot reads it as the single
source of truth for mapping.

## Column mapping (new site file -> master)

| Source column (site file) | Master column | Confidence |
|---|---|---|
| ID | ID | confident |
| 姓名 (name) | — (dropped) | intentional — privacy |
| 性別 | gender | confident |
| 生日(民國年/月/日) | age (computed) | confident |
| 教育程度 | eduyear | confident |
| (from filename / 據點) | location | confident |
| 慣用手 (dominant hand) | character? | UNCERTAIN — confirm with owner |
| (batch / evaluator) | source | UNCERTAIN — confirm |
| — | sport_types | UNCERTAIN — confirm (may come from assignment) |
| 瞬間移動(A) / 方向感(B) / 順向點擊(C) / 闖關卡 | counts_* | prefer app export; site marks are unreliable |

Any source column not in this table is "unmapped" — list it in the issues report
for confirmation; never silently drop or guess it.

## Value conversions

### Gender
- 女 -> "F"   |   男 -> "M"   |   anything else -> blank + flag.

### Education -> eduyear (years)
- 無 -> 0
- 國小 -> 6
- 國中 -> 9
- 高中/高職 -> 12
- 專科 -> 14
- 大學/科大 -> 16
- (研究所 / graduate -> 18)
- unrecognized -> blank + flag.

### ROC birthday -> age
- Birthday is Taiwan ROC calendar: format like "民國 YY/MM/DD" (e.g. 70/01/01).
- Gregorian year = ROC year + 1911.  (民國70 -> 1981.)
- age = collection_year − birth_year, minus 1 if the birthday has not occurred
  yet by the collection date. Use the file's collection date if known, else today.
- If birthday is missing or unparseable -> leave age blank + flag.
- Sanity check: 0 <= age <= 120, else flag.

### location / source
- location: derive from the file name or the 據點 label (e.g. "東興里據點…" -> 東興里).
- source: confirm the convention with the data owner (e.g. site batch id).

### IRB Check
- Carry through; must be TRUE/confirmed. FALSE or blank -> flag "IRB not confirmed"
  (do not exclude the row automatically — flag it).
