# NeuroPilot — install the code & wire the skill

This skill is a **driver**. It does not contain the pipeline. Before it can run
anything, the real VCL NeuroPilot code and a de-identified dataset must be present
locally, and the skill must know where they are.

## What you need (two items, both from the instructor)

1. **`Day3_VCL_NeuroPilot_RealKit.zip`** — the `code/` project (contains
   `scripts/task3_v2/`, `mcp_server/`, `dashboard/`, `skill/vcl-neuropilot/`,
   `requirements.txt`, `.env.example`, `environment.yml`). This is *separate* from
   the docs-only `Day3_Neuropilot_wt_code.zip`.
2. **A de-identified `108_VGH_D` slice** — raw BrainVision files per subject
   (`S###_pre/post.vhdr` + `.vmrk` + `.eeg`) and `108_D_subject info.xlsx`.
   De-identified IDs only (S001, S002 …); never names or identifiers.

## Where to put the code (the wiring)

The pipeline resolves its project root from the `TASK3_PROJECT_ROOT` environment
variable. The skill checks, in order:

1. `$env:TASK3_PROJECT_ROOT` (if it contains `scripts\task3_v2`).
2. Default drop-in: `C:\Users\user\2026 Literature reveiw agent\neuropilot-code`.

### Option A — default drop-in location (simplest)

Unzip the RealKit so this path contains `scripts\task3_v2\`:

```
C:\Users\user\2026 Literature reveiw agent\neuropilot-code\
    scripts\task3_v2\...
    mcp_server\...
    dashboard\...
    requirements.txt
    environment.yml
    .env.example
```

If the RealKit unzips to a nested `code\` folder, either move its contents up so
`neuropilot-code\scripts\task3_v2` exists, or point `TASK3_PROJECT_ROOT` at the
inner `code\` folder (Option B).

### Option B — keep the code elsewhere

Put the code anywhere, then set the env var so it persists across sessions:

```powershell
# persist for your user account
setx TASK3_PROJECT_ROOT "D:\path\to\vcl-neuropilot\code"
# (open a new terminal afterwards; setx affects future sessions, not the current one)

# or just for the current session
$env:TASK3_PROJECT_ROOT = "D:\path\to\vcl-neuropilot\code"
```

The skill will pick it up automatically.

## Environment

From the project root:

```powershell
cd $env:TASK3_PROJECT_ROOT
conda env create -f environment.yml    # or: pip install -r requirements.txt
conda activate neuropilot
Copy-Item .env.example .env
# in .env (or the session), set:
$env:TASK3_ALLOW_RAW = "1"             # REQUIRED before any stage reads raw .vhdr
```

`references/environment.yml` in this skill is a copy of the workshop environment
for reference (MNE, meegkit, pyprep, mne-icalabel, python-picard, emd,
scikit-learn, shap, mcp/fastmcp …). If the v2 preprocessing extras are missing,
stage 01 falls back to the v1 path.

## Data placement

Put the dataset under the project root:

```
$env:TASK3_PROJECT_ROOT\108_VGH_D\
    S001_pre.vhdr  S001_pre.vmrk  S001_pre.eeg
    S001_post.vhdr ...
    108_D_subject info.xlsx
```

## Verify the wiring

```powershell
$root = if ($env:TASK3_PROJECT_ROOT) { $env:TASK3_PROJECT_ROOT } `
        else { "C:\Users\user\2026 Literature reveiw agent\neuropilot-code" }
Test-Path "$root\scripts\task3_v2\run_v2_pipeline.py"   # -> True when wired
Test-Path "$root\108_VGH_D"                             # -> True when data is placed
```

When both are True, the skill's Step 2/3 run commands will work as written.

## Safety (do not weaken)

De-identified IDs only · raw EEG gated by `TASK3_ALLOW_RAW` · never commit or
output backend addresses / API keys / subject data · exploratory research, not
clinical advice.

## Cloud alternative (no local install)

The docs kit's `env/Day3_Colab_RunPipeline.ipynb` runs the same pipeline in Google
Colab: upload the RealKit zip + a de-identified data slice; it sets
`TASK3_PROJECT_ROOT` and `TASK3_ALLOW_RAW` for you and runs stage 01 +
`run_v2_pipeline.py --skip-emd`.
