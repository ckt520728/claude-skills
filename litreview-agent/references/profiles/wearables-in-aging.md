# Research Profile — Wearable devices in aging neuroscience

A named profile for `litreview-agent`. To use it: "run litreview-agent with the
wearables-in-aging profile". It overrides the default MDD profile.

## Topic
Wearable and passive-sensing devices (accelerometers/IMUs, smartwatches, fitness
trackers, wearable EEG, PPG/ECG, insole/pressure sensors) used to measure, screen
for, or monitor brain, cognitive, and neurodegenerative outcomes in older adults —
i.e. digital biomarkers of neuro-aging (cognition, gait as a brain readout, sleep,
falls, prodromal neurodegeneration).

## Search queries (per source — the CLI supports overrides)

**PubMed (MeSH-tagged, high precision)** — pass via `--pubmed-query`:

```
("Wearable Electronic Devices"[MeSH] OR "Fitness Trackers"[MeSH] OR "Accelerometry"[MeSH]
 OR wearable*[tiab] OR smartwatch*[tiab] OR actigraph*[tiab] OR "inertial measurement unit"[tiab])
AND ("Aged"[MeSH] OR "Aging"[MeSH] OR "older adult*"[tiab] OR elderly[tiab] OR geriatric*[tiab])
AND ("Cognition"[MeSH] OR "Cognitive Dysfunction"[MeSH] OR "Neurodegenerative Diseases"[MeSH]
 OR "Gait"[MeSH] OR "Brain"[MeSH] OR cognit*[tiab] OR dementia[tiab] OR neurodegener*[tiab]
 OR Parkinson*[tiab] OR Alzheimer*[tiab] OR gait[tiab])
```

**arXiv / Semantic Scholar (plain terms — MeSH breaks them)** — pass via `--arxiv-query`:

```
wearable sensor older adults cognition brain gait neurodegenerative EEG accelerometer
```

**Obsidian** — leave as the natural-language topic (keyword scoring).

## Keywords (seeds, if editing the queries)
wearable · IMU / accelerometer · smartwatch · actigraphy · wearable EEG · PPG ·
older adults / aging · cognition / MCI / dementia · Alzheimer's · Parkinson's /
prodromal · gait as digital biomarker · falls · sleep · digital biomarker

## Must-have criteria (ALL, to rank High/Medium)
- Human participants, older adults or an explicitly aging-relevant population
- A wearable / passive-sensing device is the measurement modality
- Outcome is neuro: cognition, brain structure/function, neurodegeneration, or
  gait/balance/sleep used as a nervous-system readout

## Nice-to-have (boost score)
- Reports a quantitative performance metric (AUC/AUROC, RMSE, correlation, effect size)
- External / multi-cohort validation (not single-sample)
- Longitudinal or prospective design (not just cross-sectional)
- Explainable / fairness-audited models; open-source tools
- Links a molecular/imaging biomarker to a wearable metric (mechanistic bridge)

## Exclusions (drop)
- Pediatric / infant / non-aging populations (unless the method clearly transfers)
- Pure activity/fitness tracking with no brain/cognition/neuro outcome
- Device-engineering papers with no human aging-neuro validation
- Reviews with no new data — unless they set/update a benchmark

## Standard benchmarks for comparison
Approximate field reference points from the wider literature (NOT from any single
search); use to interpret new numbers, and always state above/at/below.

| Metric | Field reference | Context |
|---|---|---|
| Digital/wearable MCI or dementia classification | ~0.75–0.85 AUC | common range across digital-biomarker reviews |
| Prodromal-neurodegeneration screening (e.g. RBD→PD) | ~0.80 AUROC = good | strong tools clear this and generalize across cohorts |
| Clinically meaningful gait-speed change (MCID) | ~0.10 m/s | older-adult mobility threshold |
| Gait speed as adverse-outcome marker | <0.8–1.0 m/s | "gait speed as a vital sign" literature |
| Research actigraphy vs PSG | sleep sensitivity ~0.90+, wake specificity ~0.3–0.5 | known actigraphy limitation |
| Fall-prediction (single-sensor/clinical) | ~0.70–0.80 AUC | typical before multimodal fusion |

Interpretation rules of thumb:
- A high AUC/AUROC only counts if it holds on an **external** cohort — single-cohort
  results overstate.
- Under class imbalance (rare events like falls), **AUC is misleading** — demand
  PPV / sensitivity at the operating point.
- **Cross-sectional ≠ predictive.** Associative gait/biomarker findings need
  longitudinal validation before "predicts decline" claims.

## Output preferences
- Ranked table first, colour-coded by tier; benchmark comparison never skipped
- Pull the actual metric (AUC, RMSE, r, effect size); mark "not reported" honestly
- Deliverables: digest + Excel workbook + benchmark chart; export sources to NotebookLM
- Flag off-topic PubMed hits filtered out (the MeSH query keeps these low)
