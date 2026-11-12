# Autonomous Discovery Lab: User Manual

**Page:** `app/discovery_lab.html`, served at `http://127.0.0.1:8090/discovery-lab`
**Version:** 2026-11-12 (the first draft is kept as `app/discovery_lab_r0.html`)
**Audience:** anyone who wants to see how an autonomous AI scientist behaves, and why verification matters

> **Read this first.** Everything on this page is a seeded simulation except the METR time-horizon data, which comes from metr.org (fetched 2026-11-12). The proof panel is Lean-*inspired*. No Lean kernel runs. "Promoted" means a claim passed this simulation's gates. It does not mean the claim is true.

---

## 1. Starting the page

**From the dashboard server (recommended)**

```powershell
cd "<project>pp"
.\start_dashboard.ps1
```

Then open `http://127.0.0.1:8090/discovery-lab`. The main knowledge dashboard stays at `http://127.0.0.1:8090/`.

**Without a server.** Double-click `app\discovery_lab.html`. The page is self-contained, with no external scripts or network calls.

---

## 2. What the simulation is

An AI agent searches a hidden 32 × 32 "landscape" for **target regions**: cells whose true value is ≥ 0.80. Each iteration follows the loop that self-driving labs use:

```
Plan → Execute → Analyze → Verify → Audit → Ledger
  ↑        │                  │        │
  └──── Replan ◄──────────────┴────────┘
```

| Stage | What happens | What can go wrong |
|---|---|---|
| **Plan** | Picks the next cell by UCB: predicted value + κ × uncertainty | *Planning drift*: a random cell is chosen instead (more likely at low capability) |
| **Execute** | Runs the experiment (synthesis, training run, proof attempt, assay) | *Execution failure*: the task is longer than the agent's modeled horizon. Budget is spent and no data comes back |
| **Analyze** | Drafts N interpretations; a verifier picks one | *Misread*: the chosen interpretation is wrong, so the recorded value is shifted by 0.25–0.45 |
| **Verify** | A replicate measurement, or an exact kernel check in the Lean-gated scenario | The replicate disagrees and the claim is *refuted* |
| **Audit** | Promotes the claim when confidence ≥ 1 − risk tolerance | An unverified claim is quarantined at low tolerance |
| **Ledger** | Append-only record of every claim | Nothing is ever deleted or rewritten |

A **random planner** runs beside the agent as a baseline. It uses the same robot, noise and budget, but picks cells at random, never verifies, and promotes every hit.

---

## 3. Screen layout

```
┌───────────────────────── Header: scenario · seed · theme · export ─────────────────────────┐
│ Interpretation boundary                                                                     │
│ KPI tiles: targets · false discoveries · budget · reliability · analysis accuracy · horizon │
├──────────────┬──────────────────────────────────────────┬──────────────────────────────────┤
│ Control      │ Search map (belief / ground truth)       │ Agent graph (last iteration)     │
│ surface      │ Discovery curve + 20-seed batch          │ Event log                        │
├──────────────┴──────────┬──────────────────────────────┬┴──────────────────────────────────┤
│ Test-time scaling       │ METR time horizons (real)    │ Hypothesis tournament (BTL)       │
├─────────────────────────┴──────────────┬───────────────┴───────────────────────────────────┤
│ Claim ledger                           │ Proof gate (Lean-inspired)                        │
├────────────────────────────────────────┴───────────────────────────────────────────────────┤
│ Evidence behind the design (LIVE / SAVED source cards)                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

On narrow screens the columns stack: phone layouts are supported down to 375 px.

---

## 4. Header controls

| Control | Effect |
|---|---|
| **Scenario** | Switches the mission and resets the run (see §6) |
| **Seed** | Any integer from 1 to 99999. The same seed with the same settings gives the same run. Changing it resets |
| **Theme** | Toggles light/dark. The choice is remembered in this browser only |
| **Export run JSON** | Downloads settings, claims, events and both agents' results. Ground truth for each claim is included only after the run completes |

---

## 5. The control surface

Every setting changes something. Settings marked *on Reset* apply to the next run. All others apply from the next step.

| Setting | Range (default) | What it changes |
|---|---|---|
| **Agent capability** | 20–95 (70) | The modeled 50% task horizon: 20 → 1 min, 95 → about 17.4 h, matching the latest METR frontier point. It sets execution reliability, planning-drift probability, single-sample analysis accuracy and the sharpness of the tournament judge |
| **Test-time samples N** | 1–64 (8) | How many interpretations the analysis drafts. Costs 0.01 × N budget units per analysis |
| **Verification rigor** | 0–100% (70) | The probability that a hit is replicated, and the verifier's true- and false-positive rates. A replicate confirms when it reaches 0.80 − noise σ. Disabled in the Lean-gated scenario, where the kernel checks every candidate |
| **Experiment budget** | 30–160 (80) | Units for the whole run: 1 per experiment, 1 per replicate, 0.5 per kernel check. *On Reset* |
| **Risk tolerance** | 2–60% (10) | Promotion rule: promote when confidence ≥ 1 − tolerance. Verified claims have 0.95, unverified 0.60, refuted 0.05. Unverified claims are promoted only at ≥ 40% |
| **Exploration κ** | 0–0.60 (0.24) | Weight on uncertainty in UCB. Low κ exploits known good areas; high κ explores. Cells within 4 of a promoted or refuted claim are down-weighted, so the agent moves on |
| **Literature prior (A-Lab style)** | on | The agent starts from a blurred, noisy map, as literature-trained recipe proposals would give it. The random planner never gets it. *On Reset* |
| **Speed** | slow → max | Interval between iterations while running |

**Buttons**

| Button | Action |
|---|---|
| **Run campaign / Pause** | Starts or pauses the animated run |
| **Step** | One iteration for both agents |
| **Finish** | Runs to the end instantly |
| **Reset** | New run with the current scenario, seed and settings |

The status badge reads **READY → RUNNING → PAUSED → COMPLETE**.

---

## 6. Scenarios

| Scenario | Task length | Noise | Verification | Based on |
|---|---|---|---|---|
| Inorganic synthesis (A-Lab style) | 1 h | 0.09 | replicate | Szymanski et al. (2023): literature recipes, then ARROWS3 active learning |
| Architecture search (NAS style) | 30 min | 0.06 | replicate | Zoph & Le (2017): a controller rewarded by validation accuracy |
| Formal conjecture search (Lean-gated) | 2 h | 0.12 | **exact kernel** | lean-lang.org: a minimal trusted kernel checks every proof |
| Biomedical co-scientist | 4 h | 0.14 | replicate | Wang et al. (2025): long, noisy multimodal experiments |

The missions are fictional. Only the patterns come from the cited systems.

---

## 7. Reading each panel

### KPI tiles
- **Targets realized:** distinct target regions with at least one *promoted, truly correct* claim, shown as found / available. The random planner's figure is underneath.
- **False discoveries promoted:** promoted claims whose cell is not a target. Shown with ✓ none or ✕ present. The simulation can count these only because it knows the truth.
- **Budget left:** with the number of experiments and failures.
- **Execution reliability:** probability that one experiment finishes = 1 / (1 + task length / horizon).
- **Analysis accuracy:** verifier best-of-N accuracy at the current N.
- **Modeled 50% horizon:** from capability. This is a difficulty proxy, not how long the agent can act on its own, as METR stresses.

### Search map
- **Agent belief** (default) shows what the agent's surrogate model predicts. **Ground truth (sim only)** reveals the real landscape and outlines the target cells.
- Markers:
  - ring: agent experiment
  - green diamond: promoted claim
  - red square: quarantined or refuted claim
  - orange dot: random-planner experiment (tick *Show random-planner experiments*)
  - accent circle: the claim selected in the ledger
- Hover any cell to see belief, uncertainty, the measured value, and the truth in ground-truth view.

### Discovery curve and 20-seed batch
- Step lines show targets realized against budget spent, for the agent (blue) and the random planner (orange). The dashed line is the number of targets available. Hover to read both at any budget.
- **Run 20-seed batch** replays seeds 1–20 with the current settings and reports mean targets and false discoveries for both agents, and how often the agent was ahead, level or behind. Use it before drawing any conclusion: one seed is an anecdote.

### Agent graph and event log
- The graph highlights the path the **last iteration** took. Numbers are cumulative visit counts. A busy *Replan* node means many failures.
- The event log is append-only and newest first. Each line records its kind (PLAN, EXEC, ANALYZE, PROMOTE, QUARANTINE, STOP, DONE, BATCH) and the budget spent at that point.

### Test-time scaling
- Three curves against N:
  - **Coverage** (pass@N): at least one sample is right, so an oracle could pick it.
  - **Verifier best-of-N:** what the agent actually gets.
  - **Majority vote.**
- The gap between coverage and verifier best-of-N is the lesson. An imperfect verifier caps accuracy however large N gets. In the Lean-gated scenario the verifier is exact and the two curves meet.

### METR time horizons (real data)
- 18 frontier models from METR Time Horizon 1.1, on a log scale against release date. Toggle 50% / 80% reliability.
- The dashed line is this page's own exponential refit on points from 2023 on. It is shown beside METR's published doubling time of 128.7 days (CI 104–158), and differs because it uses frontier points only.
- The orange line is the **modeled agent** for the current capability. At 80% it assumes a horizon ¼ of the 50% value, which is an assumption of this page.
- The shaded band marks > 16 h, which METR calls unreliable with its current task suite. **Table view** lists every value.

### Hypothesis tournament (Robin-style BTL)
- Six regions the agent currently rates highest become hypotheses H1–H6. Every pair is judged twice, and a Bradley–Terry–Luce model ranks them.
- **Judge position-A bias** makes the judge favour whichever option it sees first.
- **Judge each pair in both orders** (counterbalancing) cancels that bias. Untick it to watch bias leak into the ranking.
- Read **position-A share** (should stay near 50%) and **Kendall τ vs truth** (1 = perfect order). **Re-run** draws a new tournament.

### Claim ledger
- One row per claim: cell, measured value, verification (kernel ✓, replicate value, or none), confidence, decision, and ground truth (hidden until the run completes).
- Click or press Enter on a row to inspect it in the proof gate and highlight it on the map.

### Proof gate (Lean-inspired)
- Shows the selected claim as a theorem skeleton. `sorry` marks a goal this simulation could not close.
- In empirical scenarios the **bridge goal always stays open**: measurement plus replicate gives a traceable claim, not a proof.
- In the Lean-gated scenario a kernel-checked claim closes every goal.

### Evidence behind the design
Source cards marked **LIVE** (fetched in the browser on 2026-11-12) or **SAVED** (read from a local file), each with the panels it informs.

---

## 8. Guided exercises

Run each with **Finish** or the **20-seed batch**, then compare.

1. **Verification is what stops false discoveries.** In materials, set rigor 0% and risk 60%, then batch. Set rigor 90% and risk 10%, then batch again. False discoveries should fall sharply while targets change much less.
2. **Prior knowledge is what finds targets.** Batch with the literature prior on, then off (it resets). In the measured sweep for materials, the agent averaged 3.0 targets with the prior and 1.9 without, against 1.3 for random.
3. **An exact verifier.** Switch to *Formal conjecture search (Lean-gated)*. False promotions stay at 0, and in the test-time scaling chart the verifier curve meets coverage.
4. **Long tasks fail.** Choose *Biomedical co-scientist* at capability 50, then 90. Watch execution reliability and the Replan count.
5. **More samples are not enough.** Set N = 64 at rigor 20%, then rigor 90%. Read the gap at N = 64 under the test-time scaling chart.
6. **Position bias.** Set bias to 40% and untick counterbalancing. Watch the position-A share and Kendall τ, then tick it again.

---

## 9. What is real and what is not

| Element | Status |
|---|---|
| METR horizons and doubling time | **Real**: METR Time Horizon 1.1, values rounded to 0.1 min |
| Paper figures in the source cards | Quoted from local PDFs (A-Lab: 36 of 57 targets in 17 days, per the PDF abstract) |
| Landscapes, experiments, claims, tournament | **Simulated**, seeded and reproducible |
| Proof gate | **Lean-inspired** text. No Lean is executed |
| Capability → horizon mapping, logistic slope 1, prior quality | Modeling choices of this page, not measurements |

"Promoted" is scoped to the simulation's traceability gates. Any real claim still needs review by a qualified person (project hard rule 11).

---

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `http://127.0.0.1:8090/discovery-lab` does not load | The server is not running: start `.\start_dashboard.ps1` and keep its window open |
| Budget slider shows "(on reset)" | Press **Reset** to apply the new budget |
| The literature-prior box reset my run | Expected: the prior changes the starting map, so it starts a new run |
| Rigor slider is greyed out | You are in the Lean-gated scenario, where the kernel replaces replication |
| Two runs differ | Check seed, scenario and every slider. Settings changed mid-run apply from the next step and are stored with each claim |
| The tournament says "needs at least 6 measurements" | Step or run until six experiments have succeeded |

---

## 11. For maintainers

- Single file, no dependencies. Charts are inline SVG; the map is a canvas.
- Honesty labels are tested: `tests/test_agent.py::test_discovery_lab_is_served_and_honestly_labelled` requires "SIMULATED EDUCATIONAL MODEL" and "not a real Lean runtime" on the page.
- To refresh METR data, replace the `METR` array and `METR_DOUBLING` from metr.org/time-horizons (the `benchmarkDataV1_1` object on that page), then update the fetch date in the notice and in the source card.
- After any change to the model, run the 20-seed batch in all four scenarios. Record the numbers in `handoffs.md`.
