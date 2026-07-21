# VCL NeuroPilot — Day 3 workshop prompt sheet (REAL pipeline)

These prompts drive the **actual** VCL NeuroPilot code in `code/`. Each stage has an
UNDERSTAND prompt (read the real script) and a RUN prompt (execute it). Type them into
Claude desktop with the project folder open; Claude reads/runs the real files.

Dataset: `108_VGH_D/` (pre/post BrainVision `.vhdr` + `108_D_subject info.xlsx`).
De-identified subject IDs only (S001, S002 …). Shared separately by the instructor.

---

## Stage 0 — Setup (once)
Terminal:
```
pip install -r requirements.txt
cp .env.example .env           # set TASK3_ALLOW_RAW=1 to allow reading raw .vhdr
# place the dataset at ./108_VGH_D/  (raw .vhdr + 108_D_subject info.xlsx)
```
Prompt:
> Open README.md and requirements.txt and give me a 5-line overview of how VCL
> NeuroPilot is structured (backend, scripts/task3_v2, mcp_server, dashboard, skill)
> and what I need installed to run the v2 pipeline.

## Stage 1 — Preprocessing engine  (`scripts/task3_v2/stage01_preprocessing.py`)
UNDERSTAND:
> Open scripts/task3_v2/stage01_preprocessing.py and walk me through the preprocessing
> engine in order: Zapline line-noise removal, 1–90 Hz filter + resample to 500 Hz,
> LOF bad-channel detection + spherical-spline interpolation, ASR, robust-median
> reference, Extended-Infomax ICA + ICLabel artifact rejection, then 5 s epoching.
> Explain why ASR runs BEFORE ICA, and what happens if meegkit/mne-icalabel are missing.
RUN (a couple of subjects for the demo):
> Run scripts/task3_v2/stage01_preprocessing.py on subjects S001 and S002
> (TASK3_ALLOW_RAW=1). Then read processed/task3_v2_logs/task3_v2_preprocessing_log.csv
> and summarize per session: line-noise method, bad channels, ASR, reference, ICA
> components excluded, and epochs kept.
Terminal equivalent: `python scripts/task3_v2/stage01_preprocessing.py S001 S002`

## Stage 2 — Non-EMD features  (`stage02_non_emd_features.py`)
> Run stage 02 to extract non-EMD features from processed/task3_v2_npz and show me the
> columns of task3_features_pre_nonEMD.csv (band powers, FAA, etc.).

## Stage 3 — EMD / IMF features  (`stage03_emd_features.py`)  [SLOW]
> Explain what stage 03 computes (EMD via complete_ensemble_sift → IMF instantaneous
> frequency/amplitude features) and why it's slow (~5–15 min/subject). For the workshop
> we'll SKIP it and use the non-EMD path — but show me one subject's EMD output if time.

## Stages 4–10 — the ML pipeline  (`run_v2_pipeline.py`)
RUN (fast path — skips the slow EMD stage):
> Run: python scripts/task3_v2/run_v2_pipeline.py --skip-emd
> Then summarize from processed/task3_v2_results: the L1-LR PRE/POST/DELTA AUCs
> (stage 06), the 18-model feature comparison top-5 (stage 07), and the multi-model
> biomarker table with the permutation / bootstrap / FAA-only / HDRS baselines (stage 09).
Individual stages:
> Run only stages 6 and 7:  python scripts/task3_v2/run_v2_pipeline.py --stages 6 7
Key questions to ask Claude after the run:
> Does baseline (PRE) EEG predict response, or only DELTA? Is the DELTA signal
> arm-specific (stage 08) or arm-agnostic? How does the EEG model compare to the
> FAA-only and HDRS-only baselines (stage 09)?

## Dashboard  (`dashboard/app.py`)
Terminal: `streamlit run dashboard/app.py`   (task-3 view: `dashboard/task3_app.py`)
> Explain what the Streamlit dashboard shows and how it reads the task3_v2_results files.

## The agent — MCP server + Skill
Terminal: `python -m mcp_server.server`  then install `skill/vcl-neuropilot/` into Claude.
> Open skill/vcl-neuropilot/SKILL.md and mcp_server/server.py and explain how the Skill
> + MCP server turn this pipeline into an agent Claude can drive with safety rails.

---

### Safety (built into the real code — keep it)
De-identified IDs only · raw EEG gated by TASK3_ALLOW_RAW · leakage-safe CV · Holm
correction + effect sizes · permutation/bootstrap benchmarks · exploratory, not clinical.
