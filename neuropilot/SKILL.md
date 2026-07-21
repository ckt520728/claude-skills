---
name: neuropilot
description: NeuroPilot drives the VCL closed-loop EEG / MDD biomarker pipeline — a 10-stage workflow that preprocesses resting-state EEG (Zapline line-noise removal, filtering, bad-channel interpolation, ASR, ICA + ICLabel, epoching), extracts spectral/EMD features, and trains leakage-safe ML models to test whether EEG predicts antidepressant treatment response, benchmarked against permutation, bootstrap, FAA-only and HDRS-only baselines. Use this skill whenever the user wants to preprocess EEG, run or explain the EEG pipeline, extract EEG features (band power, FAA, EMD/IMF), build or evaluate an EEG treatment-response biomarker, compare EEG models to baselines, or drive the pipeline stage-by-stage from Claude. Exploratory research only — never clinical advice. Trigger on the intent even if the user never says "NeuroPilot".
---

# NeuroPilot — EEG / MDD Biomarker Pipeline Agent

NeuroPilot lets Claude drive the lab's **real** closed-loop EEG pipeline for major
depressive disorder: read each stage, run it, and interpret the results. The
scientific question is narrow and honest — **does resting-state EEG predict who
responds to treatment**, and does it beat trivial baselines. The job is not to
claim a biomarker; it is to test one rigorously and report what actually holds up.

Three qualities every NeuroPilot run must have:

1. **Rigorous** — leakage-safe cross-validation, Holm multiple-comparison
   correction with effect sizes, and permutation/bootstrap significance testing.
   A result that doesn't beat its baselines is reported as such.
2. **Reproducible** — every stage logs what it did (line-noise method, bad
   channels, ICA components removed, epochs kept); the runner re-runs deterministically.
3. **Safe** — de-identified subject IDs only; raw EEG access gated behind
   `TASK3_ALLOW_RAW=1`; outputs are exploratory, never clinical guidance.

---

## Step 0 — Locate the project (WIRING) and the data

The pipeline is the real VCL NeuroPilot code (the project root is the folder that
contains `scripts/task3_v2/`). It is **not** bundled in this skill — the workshop
ships it as `Day3_VCL_NeuroPilot_RealKit.zip` (the `code/` folder), separately
from the docs kit and from the de-identified `108_VGH_D/` dataset.

**Resolve the project root in this order (first hit wins):**

1. `$env:TASK3_PROJECT_ROOT` — the pipeline's own root hook (also set by the Colab
   notebook). If set and it contains `scripts/task3_v2/`, use it.
2. Default drop-in location: `C:\Users\user\2026 Literature reveiw agent\neuropilot-code`
   (unzip the RealKit so this folder contains `scripts/task3_v2/`).

Detect it before doing anything else:

```powershell
$root = if ($env:TASK3_PROJECT_ROOT) { $env:TASK3_PROJECT_ROOT } `
        else { "C:\Users\user\2026 Literature reveiw agent\neuropilot-code" }
if (Test-Path "$root\scripts\task3_v2") { "project root: $root" }
else { "NeuroPilot code not found at $root — see references/setup.md to install it." }
```

If the code is **not present**, do NOT invent scripts or fabricate results. Tell
the user the code is missing and point them to `references/setup.md` (how to get
the RealKit + dataset and where to put them). Full wiring details, env vars, and
the drop-in checklist live in `references/setup.md`.

**Once the code is present**, set up the environment (from the project root):

```powershell
cd $root
conda env create -f environment.yml   # or: pip install -r requirements.txt
conda activate neuropilot
Copy-Item .env.example .env           # then set TASK3_ALLOW_RAW=1 to allow reading raw .vhdr
$env:TASK3_PROJECT_ROOT = $root       # make the wiring explicit for this session
# place the dataset at $root\108_VGH_D\
```

See `references/environment.yml` for the exact dependency set (MNE, meegkit,
pyprep, mne-icalabel, python-picard, emd, scikit-learn, shap, mcp/fastmcp…).
If the v2 preprocessing extras are missing, stage 01 falls back to the v1 path.

## Step 1 — Understand before running

For any stage, read the actual script first and explain it in order, then run it.
`references/workshop_prompts.md` holds the paired UNDERSTAND + RUN prompts mapped
to each real script. Never run a stage you cannot explain.

## Step 2 — The 10-stage pipeline (`scripts/task3_v2`)

| Stage | Script | What it does |
|-------|--------|--------------|
| 01 | `stage01_preprocessing.py` | Zapline line-noise → 1–90 Hz filter + resample to 500 Hz → LOF bad-channel detect + spherical-spline interpolation → **ASR** → robust-median reference → Extended-Infomax **ICA + ICLabel** artifact rejection → 5 s epochs. (ASR runs *before* ICA.) |
| 02 | `stage02_non_emd_features.py` | Non-EMD features: band powers, frontal alpha asymmetry (FAA), etc. |
| 03 | `stage03_emd_features.py` | EMD/IMF features via complete ensemble sift — instantaneous frequency/amplitude. **Slow (~5–15 min/subject); skip for demos.** |
| 04 | merge | Combine feature tables. |
| 05 | EOG clean | Ocular-artifact cleanup on features. |
| 06 | L1-LR | L1-logistic-regression on PRE / POST / DELTA feature sets → AUCs. |
| 07 | 18-model comparison | Compare 18 model/feature combinations; report top-5. |
| 08 | treatment-stratified | Is the DELTA signal arm-specific or arm-agnostic? |
| 09 | multi-model biomarkers | Biomarker table vs **permutation / bootstrap / FAA-only / HDRS-only** baselines. |
| 10 | IMF distributions | Distribution diagnostics for the EMD features. |

## Step 3 — Run it

Run every stage from the project root with the wiring env vars set:

```powershell
cd $root
$env:TASK3_PROJECT_ROOT = $root
$env:TASK3_ALLOW_RAW = "1"

# preprocess a couple of subjects for a demo
python scripts/task3_v2/stage01_preprocessing.py S001 S002

# full feature + model pipeline, fast path (skips the slow EMD stage 03)
python scripts/task3_v2/run_v2_pipeline.py --skip-emd

# or only specific stages
python scripts/task3_v2/run_v2_pipeline.py --stages 6 7
```

After stage 01, read `processed/task3_v2_logs/task3_v2_preprocessing_log.csv` and
summarize per session: line-noise method, bad channels, ASR, reference, ICA
components excluded, epochs kept.

## Step 4 — Interpret (the questions that matter)

From `processed/task3_v2_results`, always answer:

- Does **baseline (PRE)** EEG predict response, or only **DELTA** (post − pre)?
- Is the DELTA signal **arm-specific** (stage 08) or arm-agnostic?
- How does the EEG model compare to the **FAA-only** and **HDRS-only** baselines
  (stage 09), and does it survive **permutation/bootstrap** testing with Holm
  correction? If it doesn't beat baselines, say so plainly.

## Step 5 — Surfaces: dashboard & agent

```powershell
streamlit run dashboard/app.py         # task-3 view: dashboard/task3_app.py
python -m mcp_server.server            # exposes the pipeline as MCP tools
```

The `skill/vcl-neuropilot/` + `mcp_server/server.py` turn the pipeline into an
agent Claude can drive with the safety rails wired in.

## Safety rails (built into the code — keep them)

De-identified IDs only · raw EEG gated by `TASK3_ALLOW_RAW` · leakage-safe CV ·
Holm correction + effect sizes · permutation/bootstrap benchmarks · FAA-only and
HDRS-only baselines · **exploratory, not clinical advice**. Never put backend
addresses, API keys, or subject data into outputs or anything shareable.

## Reference files

- `references/setup.md` — how to install the RealKit code + dataset and wire the skill (read this if the code isn't found).
- `references/workshop_prompts.md` — paired UNDERSTAND + RUN prompts per stage.
- `references/environment.yml` — the exact conda/pip dependency set.

## Provenance

Day 3 of the VCL closed-loop-neuromodulation (MDD) workshop series. Sibling
agents: **litreview-agent / LitPilot** (literature review) and **DataPilot**
(subject-data organization). The full pipeline code and dataset are shipped
separately from this skill.
