# Pitfalls (measured in the first build, 2026-11-11)

## Simulation design

1. **A symmetric DGP hid the bias.** Y(0)=X+0.5X² with logit e=γX makes X|Z=1 and X|Z=0 mirror images, so X² has the same distribution in both arms and misspecified OLS looked unbiased (2.00). **Fix:** use an asymmetric nonlinearity (eˣ); OLS then showed bias 1.90.
2. **A 1:1 allocation hides Freedman's problem.** At n₁/n = 0.5, ANCOVA, Lin and Δmeans all had SD ≈ 0.075. The failure needs both unequal allocation *and* arm-specific slopes. **Fix:** give the allocation a slider whose default is 0.75.
3. **DML is not magic.** With ridge λ = 300 (n = 300), DML had bias 0.59 and 0% coverage, because both nuisance fits were poor. Even at λ = 0, coverage was 85% with p/n = 0.13 at n = 300. **Fix:** use n = 500 and λ in 0–100 (default 25, coverage 93.5%), and say on the page that orthogonality forgives moderate nuisance error, not a bad learner.
4. **Extreme IPW weights wreck the chart axis.** At γ = 3, AIPW SD was 3.6 and the dot chart became unreadable. **Fix:** cap γ at 2.5 and add a trimming slider (SD 0.66 → 0.10). Note that trimming changes the estimand.
5. **A reference's numbers did not reproduce.** The Lin note quoted SDs 0.093/0.171/0.080 with z ~ U(−4,4) and a = eᶻ…, but Var(eᶻ) ≈ 140 implies an unadjusted SD near 0.4 at n = 1000. **Fix:** label your own DGP "inspired by, not identical to", and log the mismatch.
6. **Reference code had bugs.** `gamma_seq[which(p >= 0.05)[25]]` should be `[1]`. The claim that `senmw(method="t")` is a Wilcoxon test is doubtful. Run reference code before copying it.

## Code

7. **`seed()` must reset the Box–Muller spare.** Otherwise the first normal after a reseed comes from the previous stream, and reruns are not reproducible. Fixed in the template (`_spare = null` inside `seed`).
8. **Script split for testing.** The harness takes the *first plain* `<script>` block. Keep script 1 free of DOM calls and give it no attributes. `<script type=…>` breaks the split.
9. **Main-thread cost.** DML (150 reps × 10 ridge solves of a 41×41 system) takes about 1.4 s. Render cheap sections first and stagger the heavy ones with `setTimeout`. Rerun on `change`, not `input`.
10. **Theme.** Chart colors are read from CSS tokens at draw time, so charts must redraw on a `prefers-color-scheme` change, or they keep the old theme's colors.
11. **Artifact CSP.** MathJax and KaTeX CDNs and fetches are blocked, so write formulas in Unicode inside `.formula` (`white-space: pre`, `overflow-x: auto`).

## Process / tooling (Windows, Git Bash)

12. **An unset shell variable caused a hang.** `cat > "$TMP/t.js"` with `$TMP` unset became `cat > /t.js` waiting on stdin until the 120 s timeout. Use absolute scratchpad paths.
13. **`rm ../file` was blocked by the safety check.** The Bash tool resets the working directory to the project root, so a relative `..` path resolved to `D:\`. Use absolute paths and don't delete what you can leave in scratch.
14. **Named skills were improvised instead of looked up.** The prompt mentioned "grill-with-doc" and "finding_unknown". Both exist in the user's `~/.claude/skills` (`grill-with-docs`, the Thariq finding-unknowns series), but they were not in the session's skill list (`disable-model-invocation`). Search `~/.claude/skills` and the user's skills repo before inventing a replacement protocol.
