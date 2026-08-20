---
name: hhsa-clinical-timeseries
description: >-
  Take a patient's physiological time series — CGM/glucose, heart rate, HRV, blood
  pressure, activity, temperature, weight, sleep, any dense clinical signal — and
  produce a validated two-layer Holo-Hilbert Spectral Analysis delivered as a
  single-file HTML dashboard. Handles the whole chain: ingest a raw CSV (or
  recover the series from a vendor report PDF when no CSV exists), establish the
  EFFECTIVE resolution before decomposing, layer-1 EMD into intrinsic modes with
  instantaneous amplitude/frequency, layer-2 EMD of each envelope into the
  holo-spectrum H(f, ω) with ω < f admissibility, then test everything against
  white-noise, AAFT-surrogate and cycle-rotation nulls before anything is claimed.
  Trigger on the intent even if "HHSA" is never said — "分析這份 CGM 資料的多尺度結構",
  "decompose this glucose time series", "是不是有日夜節律", "find the circadian rhythm in
  this data", "EMD/EEMD on patient data", "what timescales does this variability
  live at", "multiscale analysis of this signal", "把這個時間序列做成一頁報告",
  "turn this wearable data into a dashboard", "empirical mode decomposition report".
  NOT for: real-time/closed-loop or phase-locked stimulation work (use
  hhsa-closed-loop-prototyping), generic EDA on non-time-series tables (use
  data-analyzer), or forecasting.
---

# HHSA for clinical time series

Offline analysis of one patient's recording, ending in a shareable one-page
dashboard. For real-time EEG, phase-locked triggers or closed-loop tACS, use
**`hhsa-closed-loop-prototyping`** instead — different constraints entirely.

## Before anything else

**Validate the implementation, not just the data.** Run the ground-truth test
first, every time you touch the decomposition:

```bash
python scripts/validate_hhsa.py
```

It builds `x(t) = [1 + 0.5·cos(2πt/24h)]·cos(2πt/3h) + 0.7·cos(2πt/12h)` and
asserts the holo-spectrum finds the 24 h modulation of the 3 h carrier. If that
assertion fails, nothing you compute on patient data means anything.

Expected: reconstruction error ~1e-16, envelope SD 0.352 against a true 0.354,
modulation localised at 24.9 h.

## The run

```bash
# no patient data needed to try it
python scripts/make_demo_data.py --days 13 --out demo_cgm.csv

python scripts/hhsa_pipeline.py \
    --input demo_cgm.csv --time-col timestamp --value-col glucose \
    --unit mmol/L --label "13-day CGM" \
    --resample 5 --cycle-h 24 \
    --bands "3.9:10.0:in range,0:3.8:below range,10.1:30:above range" \
    --out out/
```

Writes `out/dashboard.html` (self-contained), plus `results.json`,
`imf_table.csv`, `holo_matrix.csv`, `hhsa_log.txt` and `figs/`. Every number on
the page traces to `results.json`.

Key arguments:

| flag | meaning | how to choose |
|---|---|---|
| `--resample` | analysis cadence, minutes | from the resolution audit, not from the file |
| `--cycle-h` | candidate entrainment period | 24 for anything diurnal |
| `--surrogates` | AAFT count | 199 for p≈0.005 resolution; 99 while iterating |
| `--permutations` | rotation-test count | 4999 |
| `--edge-h` | trimmed at each end | defaults to one `--cycle-h` |
| `--bands` | `lo:hi:name,...` | clinical bands; edges are inclusive |

## Route the task

1. **No CSV, only a vendor report** → see "Recovering data from a report PDF".
2. **CSV in hand** → run the pipeline; read the audit block before the IMF table.
3. **Interpreting output** → read the verdict rules below.
4. **Changing the decomposition** → read `references/pitfalls.md` first.
5. **Changing the page** → read `references/dashboard-spec.md`.

## Non-negotiables

These are not style preferences; each one was a wrong answer before it was a rule.
Full evidence in `references/pitfalls.md`.

- **Plain EMD in both layers.** EEMD noise at the conventional 0.2·SD destroys
  ~75 % of the layer-2 modulation energy (394 → 105 on ground truth) and splits
  an AM carrier into its own sidebands. Use EEMD only as a reported sensitivity
  check.
- **Enforce ω < f** in layer 2 and report the rejected fraction. Without it the
  ground-truth holo-spectrum peaked at carrier 2.79 h / modulation 2.18 h.
- **PCHIP, not cubic spline, for amplitude normalisation.** Cubic undershoot on
  intermittent modes drove instantaneous amplitudes to 3 × 10⁶ on real data.
- **Collapse plateaus when detecting extrema.** Quantised clinical values produce
  flat runs — 34 % of steps were exactly zero in the case record.
- **Settle effective resolution before decomposing.** EMD makes IMFs out of
  interpolation artefacts as readily as out of physiology.
- **Never claim a rhythm from an IMF alone.** EMD is a dyadic filter bank; a 24 h
  mode appears in surrogates that have no rhythm (21.9 ± 1.9 h).

## Reading the output honestly

| Observation | What you may say | What you may NOT say |
|---|---|---|
| An IMF sits near 24 h | "a mode at ~24 h carries X % of variance" | "there is a circadian rhythm" |
| Rotation test p < 0.05 | "the rhythm is entrained to clock time" | — |
| AAFT p > 0.05 | "not distinguishable from a spectrum-matched linear process" | "there is no structure" |
| AAFT p > 0.95 | "**more** regular than a linear null — a finding" | "not significant" |
| IMF below white-noise null | "carries less energy than white noise would place there" | "it is an artefact" |
| A holo cell is large | "energy at carrier f modulated at ω" | "f is coupled to ω" without a null |

Correct for multiple comparisons. On the case record exactly one holo cell reached
p = 0.035 uncorrected across eight statistics tested — which is not a finding.

## Recovering data from a report PDF

When the clinic exports only a rendered report, the series is often still
recoverable: if the PDF is vector, the plotted curve is a polyline whose **anchor
points are the stored samples**.

```python
import fitz
d = fitz.open('report.pdf')
for i, dr in enumerate(d[0].get_drawings()):
    print(i, dr['type'], len(dr['items']), dr['rect'], dr.get('color'))
```

Look for long stroked (`type == 's'`) paths spanning the plot width. Calibrate
page coordinates against the printed axis gridlines, then **validate**:

- reproduce every summary statistic printed elsewhere in the report;
- check the recovered values fall on the vendor's quantisation lattice (they
  should snap to e.g. 0.1 mmol/L — a razor-sharp minimum confirms the scale);
- if days are drawn as separate panels, check continuity at the boundaries before
  concatenating.

Curve indices are vendor-specific and will not transfer between report formats.
This path worked on a 13-day AGP report to ≤0.25 pp on all 12 printed statistics.

## Privacy

The dashboard is built to be shared, so de-identify at ingest, not at publish:
strip name, MRN, device serial and exact calendar dates; keep time-of-day and
relative day index, which is all the analysis needs. Age and sex may stay if the
clinical reading requires them. Never commit the raw export or the source PDF to
a repository.

## Files

```
scripts/hhsa.py             EMD / EEMD / normalised Hilbert / holo-spectrum / nulls
scripts/hhsa_pipeline.py    ingest -> audit -> layer 1 -> nulls -> layer 2 -> tests -> figures
scripts/build_dashboard.py  results.json + figs -> single-file HTML
scripts/validate_hhsa.py    ground-truth test; run before trusting any output
scripts/make_demo_data.py   synthetic CGM-like data with a known answer
references/pitfalls.md      the ten failures, with measurements
references/dashboard-spec.md the page's design contract
assets/                     figures from the worked CGM case
```

Method: Huang et al., *Phil. Trans. R. Soc. A* 374:20150206 (2016).
Surrogates: Theiler et al. (1992). Noise null: Wu & Huang (2004).
