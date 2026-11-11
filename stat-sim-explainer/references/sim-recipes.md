# Simulation recipes (verified)

All results come from `examples/covariate-causal-inference.html`, measured with node on 2026-11-11 using the seeds shown. Use them as starting DGPs and as regression tests. If your numbers drift far from these, something broke.

| Concept | DGP | Estimators | Expected result | Seed |
|---|---|---|---|---|
| Blocking | n=80, half male; Y(0)=10+δ·male+N(0,1); τ=2; finite population, re-randomize | CRE Δmeans vs within-stratum randomization | δ=6: SD 0.736 → 0.248 (≈89% variance cut) | 101 |
| Rerandomization (ReM) | n=100, n₁=50, X₁,X₂~N(0,1); Y(0)=X₁+0.8X₂+N(0,0.6²); τ=1; accept if M ≤ a, a=−2ln(1−pₐ) (χ²₂) | CRE, ReM, CRE+Lin (two covariates) | pₐ=0.05: SD 0.273 / 0.133 / 0.126; ReM ≈ Lin (Li & Ding 2020) | 202 |
| Lin 2013 vs ANCOVA | n=400, z~U(−2,2); a=eᶻ+¼e^{z/2}+N(0,1), b=−eᶻ+¼e^{z/2}+N(0,1) | Δmeans, ANCOVA (pooled within slope), Lin (arm-wise slopes, predict at x̄) | n₁/n=0.75: SD 0.141 / **0.255** / 0.109. n₁/n=0.5: all ≈ 0.075 | 303 |
| PS / IPW / AIPW | X~N(0,1), logit e=γX; Y(0)=X+0.6eˣ+N(0,1); Y(1)=Y(0)+2+X; n=1000, 300 reps | naive, OLS Y~Z+X, Hájek IPW, AIPW (linear arm models, logistic PS) | γ=1.5: 4.55 / 1.90 / 1.99 / 1.96. Trim 0.05: AIPW SD 0.66 → 0.10 | 404 |
| DAG pitfalls | n=20,000, one draw, true effect 1 | Y~Z vs Y~Z+W | confounder 1.74→1.01; mediator 1.01→0.25; collider 1.00→0.00; M-bias 1.00→0.72; precision 1.02→1.01 | 505 |
| DML partialling-out | n=500, p=40, five confounders; Z=0.5·Σx₁..₅+N, Y=Z+Σx₁..₅+N; ridge λ; 5-fold cross-fit | naive ridge plug-in (Z unpenalized), DML, oracle OLS | λ=25: 1.12 / 1.01 / 1.00, coverage 93.5%. λ=100: DML 1.11, coverage 34% | 606 |
| Covariate-adjusted FRT | n=50 (25:25), X~N(0,1), Y(0)=ρX+√(1−ρ²)ε, Y(1)=Y(0)+τ; sharp null, permute Z | Δ means of Y; Δ means of residuals from pooled Y~X (ignores Z); studentized Lin t | ρ=0.8, τ=0.5, 2000 perms: p 0.260 / 0.006 / 0.006. Size (τ=0) 0.050/0.054/0.057. Power τ=0.4: 0.28 vs 0.62 | 808 (one experiment), 809 (power) |
| E-value | E = RR+√(RR(RR−1)), use 1/RR if RR<1 | — | 0.45 → 3.87; 0.63 → 2.55; 3.84 → 7.14 | — |
| Rosenbaum Γ | 60 pairs, diff ~ N(0.8,1); worst case p⁺=Γ/(1+Γ); normal approximation to Wilcoxon T | worst-case one-sided p | p at Γ=4 ≈ 0.04 | 707 |
| Mean vs median (template demo) | (1−ε)N(0,1)+εN(0,10²), n=30 | mean, median | ε=0: Var ratio 1.57 (π/2); ε=0.1: 0.17 | 1 |

## Closed forms worth reusing

- **ANCOVA coefficient** with one covariate: `τ̂ = Δȳ − β_pooled·Δx̄`, where `β_pooled = (Sxy₁+Sxy₀)/(Sxx₁+Sxx₀)`. No matrix solve needed.
- **Lin estimator:** `[ȳ₁ + β̂₁(x̄ − x̄₁)] − [ȳ₀ + β̂₀(x̄ − x̄₀)]`.
- **ReM threshold:** with K covariates, M ~ χ²_K under CRE; for K=2, `a = −2 ln(1 − pₐ)`.
- **Bounding factor curve** for the E-value plot: `RR_UD = R(RR_EU − 1)/(RR_EU − R)`.
- **Logistic regression with one covariate:** Newton's method, with a 2×2 Hessian inverted by hand (about 8 iterations).
