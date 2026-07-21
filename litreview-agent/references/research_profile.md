# Research Profile — edit this to retarget the agent

This block defines what the agent screens for. Everything below is meant to be
edited by the researcher. Keep it short and specific — vague criteria produce
vague digests. The default profile below targets the lab that commissioned it;
replace the Topic/Keywords/Criteria/Benchmarks for any other field.

## Topic
Closed-loop neuromodulation for Major Depressive Disorder (MDD) — including
deep brain stimulation (DBS), transcranial alternating current stimulation
(tACS), transcranial direct current stimulation (tDCS), and EEG-biomarker-driven
adaptive/responsive stimulation.

## Keywords (search seeds)
- closed-loop / adaptive / responsive stimulation
- deep brain stimulation depression
- tACS depression ; tDCS depression
- EEG biomarker depression ; neural biomarker symptom state
- treatment-resistant depression stimulation

## Must-have criteria (a paper must clear ALL of these to be ranked High/Medium)
- Human subjects (not purely animal or in-silico), OR a methods paper directly
  enabling human closed-loop work
- Depression / MDD as the target condition (comorbid OCD acceptable if MDD is reported)
- Involves a stimulation or neuromodulation intervention OR a biomarker used to
  drive one

## Nice-to-have (boosts relevance score)
- Reports a quantitative clinical outcome (response, remission, HAM-D/MADRS change)
- Personalized / patient-specific biomarker
- Novel closed-loop control policy or decoding method
- Sham-controlled or randomized design

## Exclusions (drop these)
- Pharmacology-only studies with no stimulation/biomarker component
- Reviews with no new data — unless they set or update a benchmark
- Non-depression indications unless the method clearly transfers

## Standard benchmarks for comparison
Use these as the "field standard" line against which new findings are judged.
Sources: DBS-for-TRD meta-analysis (Reddy et al., 2024) and landmark closed-loop
work (Scangos et al., 2021).

| Metric | Field-standard value | Source / context |
|---|---|---|
| Response rate (long-term, 12–60 mo), DBS for TRD | ~48% | Reddy et al. 2024 meta-analysis (7 RCTs + 8 open-label, n=275) |
| Remission rate (long-term), DBS for TRD | ~35% | Reddy et al. 2024 |
| Symptom-scale improvement (HAM-D/MADRS), long-term | ~47% | Reddy et al. 2024 |
| Sham vs active (blinded RCTs) | active NOT reliably > sham | Reddy et al. 2024 — key open problem |
| Time to 50% improvement | ~23 months | Reddy et al. 2024 |
| Open-label vs RCT effect | open-label significantly > RCT | Reddy et al. 2024 — beware optimism bias |

Interpretation rule of thumb: a new result that beats ~48% response in a
*sham-controlled* design is genuinely notable; a high open-label number is
expected and should be read cautiously.

## Output preferences
- Length: fits on one screen; tables do the heavy lifting
- Tone: plain, PI-facing, no hype
- Always include the benchmark comparison table
- Always end with concrete follow-up actions
- Also produce the Excel comparison workbook and a benchmark chart (see comparison_outputs.md)
- Export sources to NotebookLM; optionally file the digest into the Obsidian vault
- Default cadence: run every Monday at 18:00 (6 PM) with a 7-day window and share the update
