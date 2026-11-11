---
name: stat-sim-explainer
description: |
  Build a single-file interactive HTML page that teaches statistical or causal-inference concepts through live, seeded Monte Carlo simulations and hand-drawn SVG charts (histograms of sampling distributions, estimator dot-and-interval plots, curves). Each concept becomes an "experiment card": a plain explanation and formula beside a simulation the reader can rerun with sliders.
  Includes a working template (seeded RNG, stats helpers, Gaussian-elimination solver, theme-aware chart helpers), a headless node test harness for the simulation functions, verified simulation recipes (blocking, rerandomization, Lin 2013 regression adjustment, IPW/AIPW, DAG collider/mediator/M-bias, DML, E-value, Rosenbaum Γ) and a pitfalls list.
  Use when the user asks to "visualize a statistics concept", "make an interactive simulation page", "explain X with a simulation", "teach sampling distributions / bias / variance", "interactive explainer for causal inference", "用模擬視覺化統計概念", "互動式統計教學網頁", or to turn study notes or references into an interactive learning page.
---

# Statistical simulation explainer

This skill turns a statistics topic (often a folder of study notes) into one self-contained HTML page. Every claim on the page is backed by a simulation the reader can rerun.

Worked example: `examples/covariate-causal-inference.html`. It covers covariates in causal inference in 8 sections and was published as a claude.ai Artifact.

## Workflow

1. **Scope from the sources.** Read the user's prompt and every reference file. List the concepts to cover, and for each one name:
   - the *claim* the simulation must show (e.g. "ANCOVA is worse than no adjustment when allocation is unequal and slopes differ")
   - the *estimators* to compare
   - the *truth* to draw as a dashed line
2. **Grill the references before trusting them.** Recompute every number they quote (E-values, worked examples, simulation SDs) with node or python. Run their code if you can. Log each mismatch as a known unknown. Never silently correct a source. If the user has `grill-with-docs` or the finding-unknowns skills (`reference-anchor`, `blindspot-pass`), say so and use them; don't improvise a replacement.
3. **Design each data-generating process (DGP) so the claim actually shows.** See `references/sim-recipes.md`. The commonest failure is a DGP whose symmetry hides the effect you want to show (pitfalls #1–#3).
4. **Start from `assets/template.html`.** Keep its two-script structure:
   - **Script 1 holds pure functions only:** RNG, statistics, `simXxx(params, reps)`. No DOM. These are testable headless.
   - **Script 2 holds charts and wiring:** `histChart`, `dotChart`, `lineChart`, `stats()`, and handlers.
5. **Test the simulations headless before any UI work:**
   `node scripts/test_sims.mjs page.html tests.js` (the tests file is evaluated after script 1; use `console.log`). Confirm each claim numerically. Check timing too: each run should take under about 1.5 s.
6. **Write the page copy.** For each concept give:
   - what it is, as a formula in plain Unicode (MathJax is blocked by the Artifact CSP)
   - why it works, as 2–4 bullets
   - when it fails
   - the DGP in one `.note` line, so readers know the numbers are simulated
7. **Publish.** In Claude Code with the Artifact tool, run quickstart, then publish the file with `icon: "chart"`. Otherwise save the file locally.
8. **Wrap up.** Record the verification table and known unknowns in the project's `handoffs.md` (or the user's equivalent).

## Page anatomy (per concept)

```
<section id="slug">
  stage chip (Design / Analysis / Observational)  ·  h2 with English + local-language term
  .exp grid: [ explanation + .formula + ul.tight + .note(DGP) ] [ .lab: controls → legend → chart → .stats ]
</section>
```
Open the page with a "map" table that relates the concepts to each other (for causal inference: design ↔ analysis duality). Close it with a decision guide table: situation → method → watch out for.

## Rules that keep it honest

- **Seed every simulation** (`seed(n)` resets the RNG *and* the Box–Muller spare). The same slider values must always give the same chart.
- **Draw the truth on every chart.** Report SD, bias and coverage as numbers next to the picture, not only visually.
- **Let a slider break the method.** Each concept needs a control that moves the reader from "method works" to "method fails": unequal allocation for ANCOVA, strong confounding for IPW, large λ for DML.
- **Show estimand changes.** Trimming, matching and blocking can change the target population. Say so on the card.
- **Prefer the paper's exact DGP.** Reproduce the primary source's simulation and show its table next to yours. If it uses one fixed finite population that isn't published, pick a seed whose population summaries match the ones the paper reports (e.g. its LS slopes), and say so. If you can't reproduce it, label the page's DGP "inspired by, not identical to".
- **Never hard-code colors in JS.** Read CSS tokens with `getComputedStyle` and redraw on a `prefers-color-scheme` change.
- **Keep the main thread responsive.** Use moderate reps. Run the cheap simulations first and stagger the heavy ones with `setTimeout`. Rerun on slider `change`; update only the label on `input`.

## Files

| Path | Use |
|---|---|
| `assets/template.html` | Copy this to start. It includes one demo concept (sampling distribution of the mean vs median). |
| `scripts/test_sims.mjs` | Headless harness that evaluates script 1 plus your tests |
| `references/sim-recipes.md` | Verified DGPs with the numbers they should produce |
| `references/pitfalls.md` | What went wrong in the first build, and the fixes |
| `examples/covariate-causal-inference.html` | Full 8-section example |
