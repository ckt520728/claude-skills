# HHSA on clinical time series — pitfalls

Every item below was hit for real, on a 13-day CGM record, and every number is
reproducible by running `scripts/validate_hhsa.py` (synthetic ground truth) or
`scripts/hhsa_pipeline.py` on the demo data. Read this before changing anything
in the decomposition.

Ground-truth signal used throughout:

```
x(t) = [1 + 0.5·cos(2πt/24h)]·cos(2πt/3h) + 0.7·cos(2πt/12h)
```

carriers at 3 h and 12 h; the 3 h carrier is amplitude-modulated at 24 h. True
envelope SD of the AM component is 0.354.

---

## 1. EEMD noise destroys the amplitude modulation HHSA exists to measure

The literature convention is EEMD in both layers. On ground truth that is wrong
for layer 2 and risky for layer 1.

**Layer 2 (EMD of the envelope) — measured energy in the 24 h sub-IMF:**

| layer-2 method | modulation energy | recovered period |
|---|---|---|
| plain EMD | **394.0** | 23.91 h |
| EEMD, noise 0.05·SD | 385.4 | 23.97 h |
| EEMD, noise 0.10·SD | 338.2 | 24.10 h |
| EEMD, noise 0.20·SD | **104.8** | 24.39 h |

At the commonly-quoted 0.2·SD, **three quarters of the modulation energy is
gone**. The period survives; the amount does not. If you report modulation
*strength*, EEMD in layer 2 will understate it by a factor of ~4.

**Layer 1 — envelope SD recovered from the 3 h carrier (true value 0.354):**

| layer-1 method | carriers found in the 2.2–4.2 h band | envelope SD |
|---|---|---|
| plain EMD | 3.00 h | **0.352** ✓ |
| EEMD 0.05 | 3.01 h | 0.391 (inflated) |
| EEMD 0.10 | 3.03 h | 0.476 (inflated) |
| EEMD 0.20 | 2.92 h **and** 3.02 h — split | 0.356 / 0.121 |

Two failure modes, both bad:
- at low noise the added noise **manufactures** apparent modulation (0.354 → 0.476);
- at 0.2·SD the carrier **splits into its own AM sidebands** (2.92 and 3.02 h),
  which is exactly the structure HHSA was supposed to describe rather than shatter.

**Rule: plain EMD in both layers.** Keep EEMD for a reported sensitivity analysis,
never as the primary path. An envelope is smooth and near-unimodal; it does not
need mode-mixing protection.

> Correction worth recording: an earlier version of this analysis claimed EEMD
> layer 1 returned a *257 h* modulation for a 24 h ground truth. That number came
> from the spline bug in pitfall 3, not from EEMD. With the bug fixed, EEMD layer 1
> recovers 22.17 h — wrong by ~8 %, not catastrophically. The sideband split and
> the layer-2 energy loss above are the real, reproducible EEMD problems.

---

## 2. Amplitude modulation must be slower than its carrier — enforce ω < f

Without an admissibility mask the holo-spectrum's peak cell on ground truth was
**carrier 2.79 h / modulation 2.18 h** — a "modulation" faster than the thing it
modulates. It outranked the true 24 h cell.

Points with ω ≥ f are not AM. They are envelope-estimation ripple: the spline
through the maxima of |IMF| inevitably wobbles at roughly half the carrier
period, and layer 2 dutifully decomposes that wobble.

Drop them, and **report the discarded fraction** so the exclusion is auditable. A
healthy decomposition rejects a few percent. If it rejects tens of percent, the
layer-1 modes are not oscillatory enough for AM analysis to mean anything.

---

## 3. Use a shape-preserving interpolant for amplitude normalisation

Huang's normalised Hilbert transform divides the IMF by a spline through the
maxima of `|IMF|`, iterated. With a **natural cubic spline** this explodes: on
intermittent modes, successive maxima differ by orders of magnitude, the spline
undershoots toward zero between them, and dividing by it four times drove
instantaneous amplitudes to **3 × 10⁶** on real data (a glucose series whose true
amplitudes are ~1 mmol/L).

Use **PCHIP**. It is shape-preserving, so it cannot undershoot below the data it
interpolates.

Symptom to watch for: mean instantaneous amplitude wildly larger than the
physical range of the signal. Print `A.mean()` per IMF and sanity-check it against
the units. This is easy to miss because the *periods* still look plausible.

---

## 4. Collapse plateaus in extrema detection

Clinically stored values are quantised (CGM: 0.1 mmol/L). Flat runs are
everywhere — in the case record, **34 % of 1-minute steps were exactly zero**. A
naive `x[i-1] < x[i] > x[i+1]` detector returns every sample of a flat peak,
which corrupts every envelope downstream.

Detect turning points on the sign of the *non-zero* differences, then place the
extremum at the midpoint of the plateau.

---

## 5. EMD is a dyadic filter bank — a 24 h mode is not a circadian rhythm

Run EMD on any red-noise process of this length and one IMF will land near 24 h
**by construction**. Measured on AAFT surrogates of the real record: the
"circadian" IMF appeared at **21.9 ± 1.9 h** in surrogates that have no rhythm at
all, with 38 ± 8 % of variance.

So "we found a circadian IMF" is not evidence. Two different nulls are needed,
and they answer different questions:

| null | what it destroys | what it can test |
|---|---|---|
| **AAFT surrogate** | phase relations, keeps the power spectrum | whether the joint carrier–modulation structure exceeds a linear process |
| **Cycle rotation** | alignment to external clock, keeps within-cycle dynamics | whether the rhythm is genuinely **entrained** |

AAFT **cannot** tell you a rhythm exists — it preserves the spectrum, so it
already contains the 24 h peak. Asking it is circular. On the case record the
rotation test returned p = 0.0002 with clock phase explaining 56.8 % of variance,
while AAFT put the circadian period, variance and phase concentration all at
p > 0.35.

---

## 6. Establish effective resolution *before* decomposing

Storage cadence is not information cadence. On the case record, values were
stored every minute but:

- the quantisation step (0.1) exceeded the SD of 1-min increments (0.095);
- thinning to 5 min and splining back cost only ~1 quantum of RMSE;
- the PSD steepened from −1.97 (20–240 min) to −2.56 (2–10 min).

A **steepening** roll-off at the fast end means the vendor already low-pass
filtered; a genuine measurement noise floor would be flat. Conclusion: nothing
below ~15 min was physiology, and the analysis moved to a 5-min cadence.

This matters because EMD will happily produce IMFs from interpolation and
quantisation artefacts, and they will be reported as "fast oscillations" by
anyone who does not check.

---

## 7. Report the variance sum, and the reconstruction error

EMD modes are near- but not exactly orthogonal. Variance shares summed to
**101.9 %** on the case record and **118.6 %** on the synthetic demo. A pipeline
that reports exactly 100 % is normalising something it should be showing you.

Reconstruction (`Σ IMF + residual − x`) should be at machine precision for plain
EMD — 3.6 × 10⁻¹⁵. **EEMD does not reconstruct exactly**, because the ensemble
mean of the IMFs is not the signal; if you use it, say so.

---

## 8. Statistics significant in the *wrong* direction are still findings

On the case record two statistics came out far **below** their null:

- AM depth 0.229 vs 0.437 ± 0.094 expected;
- MODD 2.28 vs 2.48 ± 0.08 expected.

The naive reading is "not significant". The correct reading is that the record is
*more* regular and *more* day-to-day reproducible than a spectrum-matched linear
process — consistent with an externally imposed schedule. Use one-sided p on both
tails and label them separately (`above null` / `below null` / `not
distinguishable`).

---

## 9. Short records cannot support the holo-spectrum's own claim

13 days ≈ 13 circadian cycles. The modulation frequencies HHSA exists to resolve
(> 32 h) then have only a handful of periods in the window. On the case record
exactly one holo cell exceeded the AAFT null at p = 0.035 uncorrected — which does
not survive correction for the eight statistics tested.

Be willing to report that the method did not add anything. HHSA's value
proposition needs weeks-to-months of recording, not two weeks.

---

## 10. Vendor report PDFs are often losslessly invertible

Not a pitfall so much as a trapdoor out of one. A clinical report with "no raw
data available" may still contain the raw data: if the PDF is vector, the plotted
curve is a polyline whose **anchor points are the stored samples**.

On the case record this recovered a 13-day series that reproduced all 12 printed
vendor statistics to ≤ 0.25 percentage points. Verify any such reconstruction
against numbers printed elsewhere in the same document, and check whether the
recovered values fall on the vendor's quantisation lattice — if they snap to a
0.1 grid, the calibration is right.

Curve object indices are vendor-specific. Do not assume they transfer between
report formats.
