# Clip-and-paste HIS ingress (paste → CSV → existing import)

## The problem

Clinicians can open the hospital HIS; the care-network server and the desktop
agent cannot, and an HL7/FHIR interface takes months. Typing labs by hand is
slow and error-prone. A clinician needs to copy a lab report, a vitals line or
a problem list from the HIS and get it into the network safely.

## Decision: paste becomes import CSV, not a new form

Two designs were considered; the user chose the second:

| | Calculator form | **Paste → CSV → existing import** |
|---|---|---|
| New write path | yes (form save) | **no**: reuses import preview → commit |
| Validation, audit | must be rebuilt | **already exist** |
| Batch / bulk later | no | yes (same CSV schema as files) |
| Review | per field | per field (source lines) **and** the raw CSV |

Lesson: before building an ingress UI, ask which existing write path it should
feed. A second write path doubles validation and audit work.

Flow:

```
HIS screen ──Ctrl+C──► paste box (Import page)
   POST /api/admin/import/paste {text, chart_number?, encounter_date?}
      → deterministic parser → CSV per record type (patients/labs/ecg/conditions/screenings)
   editable CSV textareas → become the import file list
   existing 預覽 Preview → validation errors? → Commit → audit (actor, role, counts)
```

The paste endpoint writes nothing and never stores or logs the text.

## Parser rules (deterministic, no LLM)

An LLM must not read the text: it would break "no LLM arithmetic", invent or
misplace numbers, and send identifiers to a cloud model. Use fixed rules and
show their evidence.

1. **Normalise**: `unicodedata.normalize("NFKC", text)` folds full-width
   digits, letters and colons common in HIS exports (`２２.５` → `22.5`). NFKC
   turns the micro sign `µ` into Greek `μ`; map it back before unit matching.
2. **Compile every pattern with `re.IGNORECASE | re.ASCII`.** Without
   `re.ASCII`, Python's `\b` treats CJK characters as word characters, so
   `腎功能eGFR 55` never matches `\beGFR\b`.
3. **Label table in priority order** (Chinese and English synonyms):
   UACR (`ACR`, `Alb/Cre`, `Microalbumin/Creatinine`, `白蛋白/肌酸酐`) before
   creatinine; HDL/LDL (`(?<!non[-\s])HDL`) before total cholesterol; eGFR,
   HbA1c (`糖化血色素`), FPG (`AC`, `Glucose AC`, `空腹血糖`; plain "Glucose" is
   ambiguous, skip it), AST (`GOT`), ALT (`GPT`), PLT (`血小板`), TG, K, SBP/DBP,
   weight (`BW`), height (`BH`), BMI, QRS.
4. **Claim spans**: walk the patterns in priority order; drop a match that
   overlaps an already-claimed span ("Creatinine" inside "Alb/Creatinine").
   Skip serum creatinine on lines mentioning urine (`urine`, `U-CRE`, `尿`).
5. **Several values per line**: sort the claims by position; each label's value
   is the first number between it and the next label. `BP 138/82  BW 76 kg
   BH 170 cm` gives four values. Handle `BP 138/82` with its own regex.
6. **Skip reference ranges and flags**: remove `a-b` / `a~b` ranges and
   `[...]` before taking the first number; H/L flags have no digits.
7. **Units → canonical units**, always with a visible note:

   | Field | From | Conversion |
   |---|---|---|
   | creatinine | µmol/L | ÷ 88.4 → mg/dL |
   | FPG | mmol/L | × 18 → mg/dL |
   | TC / LDL / HDL | mmol/L | × 38.67 → mg/dL |
   | TG | mmol/L | × 88.57 → mg/dL |
   | UACR | mg/mmol | × 8.84 → mg/g |
   | HbA1c | mmol/mol (or value > 20) | ÷ 10.929 + 2.15 → % |
   | platelets | ×10⁴/µL (萬) / per µL | × 10 / ÷ 1000 → ×10³/µL |
   | QRS | s (< 1) | × 1000 → ms |
   | height | m (< 3) | × 100 → cm |

8. **Dates**: ISO, `YYYY/MM/DD`, and ROC (民國) years (`057/03/15` → 1968).
   Report date only from date-labelled lines (`報告日期`, `採檢日期`, `Date`),
   never from birth-date lines.
9. **Identity**: chart number (`病歷號`, `Chart No`, `MRN`), name (`姓名`),
   sex (`性別：男`, `52/M`, `Sex: F`), DOB, age (`52歲`, `52 y/o`), diagnosis
   year or duration (`DM since 2012`, `病程 10 年`), diabetes type.
10. **Yes/no history** (smoking, MI, CABG, ASCVD): detect the term, then look
    for negation within ~20 characters before / 12 after (`no`, `denies`,
    `never`, `無`, `否`, `否認`, `未`, `(-)`); `ex-smoker`/`quit`/`戒` → not a
    current smoker. Always mark "please confirm".
11. **Evidence for review**: every field returns `value, unit, unit_in, note,
    source line, line number, warnings`:
    - out of a plausible range (e.g. HbA1c 3–20, creatinine 0.1–20, eGFR 1–200) → warning ("check the unit");
    - found more than once with different values → first one used, warning lists all;
    - **lines containing numbers that no rule used** are listed, so nothing is
      dropped silently (the urine-creatinine line shows up there).

`scripts/his_paste_parser.py` is a standalone copy with `--selftest`.

## CSV generation rules

- Use the importer's own column lists (`RECORD_TYPES`) so the CSV always
  matches the import schema.
- **`patients` row only for a chart number that does not exist yet.** An
  imported patients row overwrites name, birth date and sex; a paste must never
  do that. For existing patients emit clinical rows only and say so.
- Notes for missing essentials: no chart number, no report date, age without
  DOB for a new patient, fundus result without a date.
- Booleans become `conditions` rows (`code=current_smoker|prior_mi|...`,
  `active=0/1`); QRS becomes an `ecg` row; a DR grade becomes a
  `screenings` row (`fundus_photo`, `result_code`).

## Importer and bundle fixes that pasting exposes

Pasted reports are **partial** and **incremental**; three latent bugs surfaced:

1. **Import without `patients.csv` crashed** (`KeyError: 'patients'` from an
   `ordered_keys = ["patients"] + ...` that assumed it). Follow-up labs for
   existing patients are the normal case. Build the order from what is present.
2. **The newest lab row was used as a whole**, so a later paste with only HbA1c
   turned an older eGFR into "missing". Use the most recent *non-null value per
   field* and keep each value's date (`latest_lab_dates`).
3. **The oldest condition row won**, so a later "no longer smoking" was
   ignored. Iterate conditions newest-first.

## Who may paste

- Import was admin-only; the user opened the paste box to physicians.
- Enforce it **on the server**, not only by hiding UI: for a physician,
  preview and commit accept only the paste record types (patients, labs, ecg,
  conditions, screenings), and `patients` rows only for new chart numbers.
  File upload, templates, medications and CGM stay admin-only. The physician
  gets a paste-only Import page.
- Every commit is audited with the person and role.

## Tests worth copying

- a synthetic mixed Chinese/English HIS report → every field, unit conversion,
  ROC date, negated MI, multi-value vitals line, urine creatinine unmatched;
- conversion and warning cases (mmol/mol, mmol/L, mg/mmol, /µL, no unit →
  range warning, duplicate values, label glued to Chinese text);
- existing patient → no `patients` CSV;
- end to end: paste → preview (no errors) → commit → bundle values; then a
  partial paste keeps the older eGFR and updates smoking;
- the pasted text never appears in `audit_log`;
- physician scope: paste/preview/commit OK for a new patient; medications or an
  identity change for an existing patient → 403; educator/dietitian → 403.
