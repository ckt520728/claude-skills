# Profile: signal-analysis

EEG / HRV 等生理訊號分析方法的開發：下載公開資料、以該分析法做模擬測試、
並進一步精進方法本身。

Public sources worth knowing: PhysioNet (MIT-BIH, Fantasia, CHB-MIT), OpenNeuro,
Temple University EEG Corpus. Record the exact dataset version and licence in the
playbook — reproducibility depends on it and it is trivially forgotten.

## Deliverables

| Name | Target | Split |
|---|---|---|
| `pipeline` | `src/pipeline.py` | held_in |
| `results_dev` | `results/dev_metrics.json` | held_in |
| `repro` | reproducibility check | held_in |
| `results_holdout` | `results/holdout_metrics.json` | held_out |
| `report` | `draft/analysis_report.md` | held_in |

## Contracts

```bash
$K contract --name pipeline --target src/pipeline.py --split held_in \
  --checks "exists,python_compiles,no_placeholder,cmd:pytest -q tests/"
$K contract --name results_dev --target results/dev_metrics.json --split held_in \
  --checks "exists,valid_json,json_keys:n_subjects;metric;ci_low;ci_high;seed"
$K contract --name repro --target results/dev_metrics.json --split held_in \
  --checks "cmd:python $V/check_reproducible.py --results results/dev_metrics.json"
$K contract --name results_holdout --target results/holdout_metrics.json --split held_out \
  --checks "exists,valid_json,json_keys:n_subjects;metric"
```

> `$V` = `<plugin>/scripts/verifiers/`. These scripts ship with the plugin and are tested (`python scripts/verifiers/test_verifiers.py`). Run any of them with `--help` for the full option list.

## The split matters more here than anywhere else

Partition **by subject, before any analysis runs**, and never look at the holdout
while developing. A method tuned against the same data that reports its
performance is the classic result that does not replicate. The held-out contract
exists precisely so the repair loop cannot aim at it.

## Known failure mechanisms

| Mechanism | Symptom | Component to fix |
|---|---|---|
| `leakage_via_subject_overlap` | Suspiciously high accuracy | tool — split by subject id, assert disjoint sets |
| `artifact_not_rejected` | HRV metrics wild on a few subjects | middleware — ectopic-beat / motion rejection before metrics |
| `unseeded_randomness` | Numbers differ every run | middleware — seed everything, record the seed in the output |
| `resample_before_filter` | Aliasing in the band of interest | tool — fixed preprocessing order |
| `threshold_chosen_after_seeing_results` | Suspiciously clean cut-off | contract — threshold recorded before the holdout run |
| `nonstationary_window_assumption` | Results swing with window length | not a bug — report it as a sensitivity analysis |

That last row matters: some findings are properties of the signal, not defects to
patch. A repair loop that treats every unstable result as a bug will tune away a
real phenomenon. [[harness-mine]] calls this `addressable: false`.

## Domain cautions

- HRV metrics (SDNN, RMSSD, LF/HF) are sensitive to recording length, breathing
  rate, and artifact handling. State those explicitly; do not compare across
  studies that differ on them.
- LF/HF as a "sympathovagal balance" index is contested. If the analysis leans on
  that interpretation, flag it rather than assuming it.
- Physiological recordings attached to identifiable people are sensitive data
  even when public. Follow the dataset licence; do not re-publish raw records.
