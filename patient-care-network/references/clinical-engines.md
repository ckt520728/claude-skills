# Clinical engines reference

Every engine is a pure function. It returns `status`, `value`, `level`, `inputs`, `missing`, `citation`, the formula or version, and bilingual interpretation and limitation text. Verify each equation against an independent source and a worked example *before* wiring it into the UI.

| Engine | Output | Key rules | Citation |
|---|---|---|---|
| KFRE 4-variable | 2- and 5-y kidney failure % | non-North-American baseline; **only eGFR < 60**; uses eGFR/5 (not /10 as one source note had) | Tangri 2011/2016; KDIGO 2024 |
| FIB-4 | index | (age×AST)/(PLT×√ALT); <1.30 low, 1.30–3.25 indeterminate, >3.25 high | Sterling 2006 |
| WATCH-DM | integer score → 5-y HF-hospitalisation band | missing QRS/MI/CABG gives `not_calculable` | Segar 2019 |
| Eye | surveillance **priority** (not a %) | DR grade + interval + HbA1c / renal modifiers | ADA retinopathy screening |
| CGM summary | TIR/TBR/TAR/CV/GMI/GRI | GRI = 3.0·TBR2 + 2.4·TBR1 + 1.6·TAR2 + 0.8·TAR1, capped at 100; ≥ 24 readings | Battelino 2019; Klonoff 2023 |
| SCORE2-Diabetes | 10-y CVD % | see below; region shown | EHJ 2023;44:2544 |
| CGM real-time rules | one event per batch | <54 urgent; 54–69; fall > 2 mg/dL/min and <100; >250 for ≥ 120 min | Battelino 2019; ADA §6 |
| AGP | p5/25/50/75/95 per 15-min bin | ≥ 5 days; descriptive patterns only | Johnson 2019 |
| Meal response | baseline, peak, Δ, 2 h | baseline is the last reading ≤ meal time within 30 min; peak within 0–180 min; flag Δ > 60 or 2 h > 180 | ADA §6 |
| Five dimensions | done / not_done / unknown / refused per item | see below | ADA §4–5, §13 |

## SCORE2-Diabetes

Transformations:

| Variable | Transform |
|---|---|
| Age | cage = (age − 60)/5 |
| Systolic BP | csbp = (SBP − 120)/20 |
| Total cholesterol | ctc = TC(mmol/L) − 6 |
| HDL | chdl = (HDL(mmol/L) − 1.3)/0.5 |
| Diabetes | diabetes = 1 |
| Age at diagnosis | (age at diagnosis − 50)/5 |
| HbA1c | (HbA1c(mmol/mol) − 31)/9.34 |
| eGFR | z = (ln eGFR − 4.5)/0.15, with a z² term |

Coefficients (men / women):

| Term | Men | Women |
|---|---|---|
| age | 0.5368 | 0.6624 |
| smoking | 0.4774 | 0.6139 |
| sbp | 0.1322 | 0.1421 |
| diabetes | 0.6457 | 0.8096 |
| tchol | 0.1102 | 0.1127 |
| hdl | −0.1087 | −0.1568 |
| smoking × age | −0.0672 | −0.1122 |
| sbp × age | −0.0268 | −0.0167 |
| diabetes × age | −0.0983 | −0.1272 |
| tchol × age | −0.0181 | −0.0200 |
| hdl × age | 0.0095 | 0.0186 |
| age at diagnosis | −0.0998 | −0.1180 |
| HbA1c | 0.0955 | 0.1173 |
| z | −0.0591 | −0.0640 |
| z² | 0.0058 | 0.0062 |
| HbA1c × age | −0.0134 | −0.0196 |
| z × age | 0.0115 | 0.0169 |
| **baseline survival S0** | **0.9605** | **0.9776** |

Uncalibrated risk = 1 − S0^exp(LP).

Calibrated risk = 1 − exp(−exp(s1 + s2·ln(−ln(1 − p)))), with (s1, s2) by region:

| Region | Men | Women |
|---|---|---|
| low | −0.5699, 0.7476 | −0.7380, 0.7019 |
| moderate | −0.1565, 0.8009 | −0.3143, 0.7701 |
| high | 0.3207, 0.9360 | 0.5710, 0.9369 |
| very high | 0.5836, 0.8294 | 0.9412, 0.8329 |

- **Bands (ESC 2023):** <5 low, 5–<10 moderate, 10–<20 high, ≥20 very high.
- **Applicability:** T2D, age 40–69, no ASCVD/MI/CABG. Unknown smoking status
  gives `not_calculable`.
- **Unit conversions:** TC and HDL mg/dL ÷ 38.67; HbA1c % → mmol/mol =
  (% − 2.15) × 10.929.
- **Test vector:** low region, man 60 y, non-smoker, SBP 140, TC 5.5, HDL 1.3,
  diagnosed at 60, HbA1c 50 mmol/mol, eGFR 90 gives **8.4 %**.
  `scripts/score2_diabetes.py --selftest` checks this.
- **Calibration region:** Taiwan (and most of Asia) is not a SCORE2 region. The
  default is `high`, and the result must say "not validated for <country>".

## Five-dimensional care profile

| Dimension | Items | Cut-offs used |
|---|---|---|
| Organ status | eGFR, UACR, fundus, foot monofilament, FIB-4, ABI, NT-proBNP | ABI ≤ 0.90 or > 1.40; NT-proBNP ≥ 125 pg/mL |
| Comorbidity | simplified aDCSI (0–13) from coded conditions + fundus grade; coded count | aDCSI ≥ 4 high, ≥ 2 moderate |
| Future risk | KFRE, SCORE2-Diabetes, WATCH-DM | from the engines |
| Mind | PHQ-9, GAD-7, PAID, WHO-5 (raw 0–25) | PHQ-9 ≥ 10 positive, ≥ 15 high, **item 9 > 0 is urgent**; GAD-7 ≥ 10; PAID ≥ 40; WHO-5 ≤ 12 poor, ≤ 7 assess for depression |
| Function and life | MoCA (≥ 65 y), Clinical Frailty Scale | MoCA < 26, < 19; CFS ≥ 5 frail, ≥ 7 severe |

Status rules:

| Status | Meaning |
|---|---|
| `done` | within 12 months |
| `not_done` | the last result is older than 12 months |
| `unknown` | there is no record |
| `refused` | the patient declined |

Every non-done item becomes a task.

## Nutrition confidence routing

- Threshold 0.75. Below it the meal goes to the dietitian queue.
- Simulated analyses (a demo vision model or demo STT) are capped at 0.5.
- Text or voice estimates have no portion scale, so they are capped at 0.8.
- Reference: Jamil 2026 (PC2 FoodNet). Conformal routing accepted 76 % and
  sent 24 % to a dietitian. Mass error is largest for high-moisture stews and
  broths.
