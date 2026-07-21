---
name: mortality-analysis
description: >-
  End-to-end method for a hospital mortality (M&M) audit and in-hospital-mortality
  predictor study built from discharge summaries or EHR extracts. Use when the task
  is: computing monthly/overall in-hospital mortality RATE, listing/among deaths,
  building a de-identified survivors-vs-deaths COHORT, or determining admission-time
  PREDICTORS / risk factors of death via logistic regression (OR, AUC, calibration).
  Triggers: "mortality conference", "M&M audit", "in-hospital mortality rate",
  "predictors/risk factors of mortality", "death cohort", "discharge summary
  analysis", "cause of death distribution". Covers de-identification, admission-time
  feature extraction, cohort construction (readmissions), the regression, and the
  bias caveats.
---

# Mortality analysis & predictor determination

A repeatable pipeline for turning a folder of discharge records into (a) a
descriptive mortality audit and (b) a defensible predictors-of-death analysis.
Adapt the specifics; keep the **design rules and guardrails** below intact.

## 0. Frame the study before touching data

- **Numerator (deaths)** and **denominator (all discharges)** are different
  populations. A *rate* needs the denominator; a *predictor* analysis needs the
  survivors inside it as the comparison group. A deaths-only folder can do
  neither — get the full discharge set first.
- Decide the **outcome source** explicitly (a status field, not the filename) and
  the **cohort adjudication** for ambiguous records — those are clinician
  decisions, encode them as overrides, never infer them.
- State up front: this is **retrospective and observational → association, not
  causation.** Put that line in every report.

## 1. Acquire & de-identify

- Copy source records locally if they live on a share the analysis runtime can't
  reach. Enumerate with a real path API, never shell globs (CJK/space filenames).
- **De-identify at extraction.** Analytic dataset carries surrogate IDs, age in
  years (not DOB), month (not full dates) — never name/national-ID/chart/address.
  Keep the `study_id → chart_no` linking key in a **gitignored** `private/` dir.
- Never paste record content into commits, issues, artifacts, or external services.

## 2. Build the analytic cohort (the part people get wrong)

- **Outcome per admission**, keyed `(chart_no, month)` — NOT chart alone, or a
  readmitted decedent's earlier *surviving* admission gets mislabelled a death,
  and same-month duplicate files double-count deaths.
- **Death is a patient-terminal event** → mark it on each patient's **last
  admission** (`is_last_adm`). Flag readmissions (`n_adm`) and same-month
  duplicates (`dup_flag`).
- Extract the chart number from the **document body**, not the filename
  (filenames carry months/beds/dates). Normalise leading zeros (`int()`).
- Two analysis units fall out: **patient-level** (`is_last_adm==1`, primary) and
  **admission-level** (all rows, secondary, with cluster-robust SEs on patient).

## 3. Extract ADMISSION-TIME features only

- Predictors must be knowable **at admission**: demographics, baseline
  comorbidities (from the *admission* diagnosis + history, NOT the discharge
  diagnosis, which carries hospital-acquired conditions), and **admission/ER
  labs** (first values).
- **Exclude care-process variables** (DNR/comfort-care, ICU, ventilation, CPR)
  from predictor models — they sit on the severity→death causal path (a DNR order
  is a decision correlated with expected death). Keep them descriptive only.
- Regexes for clinical terms must be **case-insensitive**; guard ambiguous
  abbreviations (e.g. `Cr` vs `CRP`). Sanity-check coverage against known counts —
  suspiciously low coverage of a routine value is a pattern bug, not missing data.
- Emit a **QC report**: N, events, per-variable coverage, outcome-linkage
  cross-check, readmission/duplicate counts, and the recommended analysis subset.

## 4. Analyse

- **Descriptive:** monthly death counts and rate = deaths ÷ discharges (confirm
  the denominator's scope matches the numerator). Small monthly denominators →
  unstable rates; report the caveat. Cause of death is **dual-axis** (underlying
  cause + terminal mechanism) — single-axis collapses to "everyone died of
  respiratory failure."
- **Predictors (logistic regression):**
  - **EPV:** keep predictors ≤ events/10. If complete-case drops events, use a
    **parsimonious pre-specified** set as primary and **multiple imputation
    (MICE)** to retain all events.
  - Report **adjusted OR (95% CI)**, a **forest plot**, **AUC** (bootstrap CI),
    and **calibration** (Hosmer–Lemeshow, plot). Continuous per-SD, age per-10y.
  - **Sensitivity:** full model, LASSO selection, admission-level clustered —
    check the leading signals are concordant.
- **Interpret with the bias direction stated:** death records are usually
  documented more fully than survivor records (**differential misclassification**)
  → *comorbidity* ORs may be inflated; trust **objective admission labs** more.

## 5. Report & package

- Write both the numbers and an **interpretation/inference** section: what each
  predictor means clinically, what the AUC does and does not license (moderate
  AUC = not a bedside tool without external validation), and the limitations.
- Render CJK-safe PDFs via headless Chrome (Markdown → self-contained HTML →
  `--print-to-pdf`); embed figures as base64; merge multi-part packets with
  `pypdf`. Mixed orientation via a named `@page landscape` rule.

## Guardrails (hard-won — violate at your peril)

- Outcome from the status field, never the filename; chart from the body cell.
- `(chart, month)` linkage; death on last admission; flag dups/readmissions.
- Admission-time predictors only; care-process variables excluded.
- EPV ≤ events/10; parsimonious + MICE when complete-case bleeds events.
- Case-insensitive clinical regexes; verify coverage vs known counts.
- Association, not causation; name the differential-documentation bias.
- De-identify at extraction; keep linking keys gitignored and local.
- **QC/reconcile every count** — cross-checks catch the silent errors (a
  chart-only linkage once inflated deaths ~2×; a case-sensitive regex zeroed the
  biggest category). In pandas, use `row['var']` not `row.var` (`.var()` clash).

## Example pipeline (adapt names to your data)

A reference build implements the method as these stages:

```
extract_cohort   # discharge records -> de-identified cohort.csv + QC + data dictionary
analyze          # Table 1, univariable, multivariable (parsimonious), MICE, LASSO,
                 #   admission-clustered, AUC/calibration, forest/ROC/calibration figures
make_reports     # descriptive audit: monthly rates, cause-of-death, (masked) case listings
make_pdf         # meeting PDFs (portrait summary + landscape listings), figures embedded
make_final       # cover + descriptive + analysis -> one merged packet (pypdf)
```

Environment recipes (adapt to your machine): legacy `.doc` via
`antiword -m UTF-8.txt`; SMB shares that the runtime can't see via PowerShell
`robocopy` into a local working copy; stats stack via
`pip install --only-binary=:all: numpy pandas scipy statsmodels scikit-learn matplotlib pypdf`;
CJK PDFs via headless Chrome (`--print-to-pdf`). Keep a per-project `CLAUDE.md`
and a running pitfalls log, and **never commit patient data or linking keys** —
publish only the method and aggregate, de-identified results.
