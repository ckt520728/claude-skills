---
date: 2026-11-11
tags: [claude-code, statistics, causal-inference, simulation, artifact, skill, pitfalls]
project: 2026 Statistics learning
skill: stat-sim-explainer
---

# Statistical simulation explainer: lessons and pitfalls (2026-11-11)

**Project:** learn how covariates affect causal inference. The goal was to summarize design-stage strategies and analysis-stage methods for controlling covariates, using four Chinese study notes as the guide, and to visualize them with examples.
**Outputs:**
- interactive page: https://claude.ai/artifact/AF33wt5VtoXBwkEDdHxTtj (private)
- `CLAUDE.md` and `handoffs.md` in `D:\2026 Statistics learning`
- the reusable skill `stat-sim-explainer/` in `ckt520728/claude-skills`

**Environment:** Windows 11, Claude Code (Opus 5.5), Git Bash, node 26, Python 3.9. R is not installed.

> Methods and lessons only. No keys, no private data.

## One-line summary

**A statistics explainer is only as honest as its simulation design. Choose the DGP so the claim *can* fail, test the pure simulation functions headless before drawing anything, and recompute every number a reference quotes.**

## What was built

| Item | Result | Evidence |
|---|---|---|
| Interactive page, 8 concept cards + map + decision guide | Blocking, ReM, Lin 2013, PS/IPW/AIPW, DAG pitfalls, DML, E-value, Rosenbaum Γ | Published as an Artifact (v2 includes the seed fix) |
| Headless verification | Every simulation claim confirmed numerically | See the table below |
| Project init | `CLAUDE.md` (conventions, grill-with-doc, finding-unknowns), `handoffs.md` | Files in the project root |
| Skill `stat-sim-explainer` | `SKILL.md`, template, node harness, recipes, pitfalls, full example | Template demo: Var(median)/Var(mean) = 1.57 = π/2 ✔︎ |

## Key verified results (seeded)

| Concept | Result |
|---|---|
| Blocking (δ = 6) | SD 0.736 → 0.248, about 89% less variance |
| ReM (pₐ = 0.05) | SD 0.273 → 0.133 ≈ CRE+Lin 0.126 (design ↔ analysis duality) |
| Lin vs ANCOVA (n₁/n = 0.75, opposite slopes) | unadjusted 0.141, **ANCOVA 0.255 (worse)**, Lin 0.109 |
| Observational (γ = 1.5, true ATE 2) | naive 4.55, OLS 1.90, IPW 1.99, AIPW 1.96 |
| DML (λ = 25) | naive 1.12, DML 1.01, coverage 93.5% |
| E-values in the references | 3.87, 2.55, 7.14, all correct |

## Concept summary (the learning goal)

- **Design stage:**
  - blocking or stratified randomization for discrete covariates
  - rerandomization (Mahalanobis, ReM) for continuous or many covariates
  - matching and overlap trimming for observational data
  - pre-registering the covariate set
- **Analysis stage:**
  - post-stratification
  - Lin (2013) fully interacted OLS with HC2 standard errors
  - covariate-adjusted FRT
  - IPW, and doubly robust AIPW
  - DML for p ≫ n
- **Covariate selection:**
  - back-door criterion
  - never adjust for colliders, mediators or other post-treatment variables
  - M-bias shows that "pre-treatment" alone is not enough
- **Unmeasured confounding:** Rosenbaum Γ and E-value quantify how much hidden bias would overturn a result. They do not prove causation.
- **Best practice for RCTs (Li & Ding 2020):** ReM at design + Lin adjustment + robust SE.

## Pitfalls

### Simulation design
1. **A symmetric DGP hid the bias.** With a quadratic outcome and logit e = γX, misspecified OLS looked unbiased (2.00). An asymmetric eˣ term revealed the bias (1.90).
2. **A 1:1 allocation hid Freedman's ANCOVA problem.** All estimators were equal at 0.5. The failure needs unequal allocation *and* heterogeneous slopes.
3. **DML failed when the learners were bad.** Ridge λ = 300 gave 0% coverage. Coverage was low (85%) even at n = 300 with p = 40. Fixed with n = 500 and λ ≤ 100. Orthogonality forgives moderate nuisance error only.
4. **Extreme IPW weights** at γ = 3 made the chart unreadable. Fixed by capping γ at 2.5 and adding trimming. Trimming changes the estimand.

### References
5. **The Lin note's simulation SDs did not reproduce** with its stated DGP: Var(eᶻ) ≈ 140 implies an SD near 0.4, not 0.093. Logged as a known unknown; the page labels its own DGP.
6. **Bugs in the reference R code:** `which(p >= 0.05)[25]` should be `[1]`, and the claim that `senmw(method="t")` is a Wilcoxon test is doubtful. Neither was run (no R).
7. **Citation numbers** in the NotebookLM exports point to a missing source list.

### Code
8. **`seed()` did not reset the Box–Muller spare,** so reruns were not exactly reproducible. Fixed and republished (v2).
9. **Heavy simulations block the UI.** DML takes about 1.4 s. Stagger initial renders with `setTimeout`; rerun on `change`, not `input`.
10. **Chart colors** come from CSS tokens, so charts must redraw on a theme change. The Artifact CSP blocks MathJax, so formulas are Unicode.

### Tooling and process
11. **An unset shell variable hung a command:** `cat > "$TMP/t.js"` waited on stdin until the 120 s timeout. Use absolute paths.
12. **The safety check blocked `rm ../file`** because the Bash cwd resets to the project root and `..` resolved to `D:\`. Use absolute paths, and leave scratch files in scratch.
13. **Named skills were improvised instead of looked up.** The prompt's "grill-with-doc" and "finding_unknown" map to the installed `grill-with-docs` and the Thariq finding-unknowns series. They were hidden from the session's skill list (`disable-model-invocation`). Search `~/.claude/skills` and the skills repo first.

## Reusable pattern

1. Scope each concept as claim, estimators and truth.
2. Grill the references: recompute their numbers and run their code.
3. Choose a DGP where a slider moves the method from working to failing.
4. Put the pure seeded simulations in script 1 and run `node scripts/test_sims.mjs`.
5. Draw charts from CSS tokens.
6. Publish as an Artifact.
7. Write a handoff with known unknowns.

## Next steps
- Check Lin (2013) §5 / Table 1 against the original paper.
- Install R and run the `DoubleML`, `EValue` and `sensitivitymw` snippets.
- Add a covariate-adjusted FRT card.
- Run a `/grill-with-docs` session on Lin vs ANCOVA, trimming estimands and M-bias.
