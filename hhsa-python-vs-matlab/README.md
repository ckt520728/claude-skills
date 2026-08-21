# hhsa-python-vs-matlab

A controlled comparison of two Holo-Hilbert Spectral Analysis implementations —
the Python one in `hhsa-clinical-timeseries/scripts/hhsa.py`, and a MATLAB-language
one written from the NCU / Nguyen et al. reference specification — run on identical
inputs and separated one algorithmic choice at a time.

**Session wrap-up (繁中):** `../2026-08-21_HHSA_Python_vs_MATLAB_Lessons_and_Pitfalls.md`

---

## Why this exists

"Does the MATLAB version agree with the Python version?" has no useful answer as a
single number. The two differ in at least five places at once, so any single
similarity score is uninterpretable. This folder replaces that question with an
**attribution ladder**: five configurations, each one step apart, so every point of
divergence can be charged to the choice that caused it.

```
mat_mask            masking EMD, natural spline everywhere        <- the reference method
   ↓ step 1         amplitude-normalisation spline -> PCHIP
mat_mask_pchip
   ↓ step 2         masking EMD -> plain EMD
mat_emd_pchip
   ↓ step 3         sifting spline natural -> not-a-knot
mat_emd_nak_pchip
   ↓ step 4         layer-2 envelope: |IMF|-maxima spline -> 4x PCHIP normalisation
py_noadm
   ↓ step 5         admissibility cut f_am < f_c: off -> on
py                  the Python implementation exactly as it ships
```

## What it found

| | |
|---|---|
| **The two codebases implement the same EMD** | Configured alike, 98.4–100 % of layer-1 variance sits in modes matching at \|r\| ≥ 0.9. Divergence is method, not bugs. |
| **The biggest lever is undocumented** | No source specifies the interpolant inside the amplitude normalisation. A natural cubic spline inflates one real mode's instantaneous amplitude **4.25 × 10⁶-fold**; PCHIP stays bounded. |
| **Masking EMD is not cosmetic** | On clean synthetic signals the two decompositions agree. On a real, mode-mixed clinical record they share *no* mode, and masking EMD resolves a rhythm carrying 24 % of the variance that plain EMD splits and hides. |
| **Sifting spline and admissibility barely matter** | Cosine 0.96–1.00 across both steps. The admissibility cut costs under 1 % of the layer-2 energy — cheap, keep it. |
| **The Python API has no time axis** | The reference method builds (f_am, f_c, *t*) and marginalises last. `holo_spectrum()` returns 2-D, so time-varying coupling needs the layer-2 loop rewritten by hand. |

Ranked, on eight signals: normalisation spline (cosine 0.00–0.96) ≫ layer-2
envelope (0.11–0.86) ≈ masking vs plain EMD (0.11–0.84) ≫ sifting spline
(0.96–1.00) ≈ admissibility cut (0.999–1.000).

## Provenance — read this before citing anything

The original NCU MATLAB pipeline **was never executed**. `NCU_Neuroholo/` holds only
the GUIDE front end; the core functions it calls (`eemd2layer_tf`, `holo_eeg_tf`,
`eemd1_tf`, `hht_eeg_tf`) were not obtainable, and the local MATLAB licence had
expired. The `matlab/` code here is written from the specification that the sources
actually pin down:

- **Nguyen et al. 2019**, *Sci. Rep.* 9:16919, Supplementary Methods — two-layer EMD,
  masking EMD in both layers, natural spline through the maxima of |IMF|, projection
  to (f_am, f_c, time) then marginal summation.
- **`neuroholo_bak.m`** — EEMD defaults (ensemble 40, noise 0.1 × SD), HHT grid
  (0–50 Hz, 101 bins, 400 time bins), holo grids linear and dyadic.
- **Deering & Kaiser 2005** — the masking EMD itself. Tsai et al.'s enhancement, cited
  by the supplement, could not be obtained offline; the phase-averaged dyadic schedule
  used here follows standard mask-sift practice and **no equivalence to Tsai et al. is
  claimed**.

Anything the sources leave open is a switch in the code, not a silent decision.

## Layout

```
matlab/    ncu_*.m           the reference-spec HHSA core, Octave- and MATLAB-compatible
           run_matlab_side.m driver: 5 configurations over every shared signal
           dump_instability.m the one trace that explains the largest divergence
python/    run_python_side.py driver: 2 configurations (as-shipped, and cut disabled)
work/      make_signals.py   writes the shared inputs once, at %.17g, for both sides
           compare.py        the ladder, IMF correspondence, ground-truth recovery
           make_figures.py   figures 1-6
assets/    fig1 … fig6
results/   comparison.json, summary_table.csv, compare_console.txt
```

## Running it

Needs Python with NumPy/SciPy, and GNU Octave (or MATLAB). From a working directory
containing this folder's contents:

```bash
mkdir -p data output figs
cp ../hhsa-clinical-timeseries/scripts/hhsa.py python/     # the Python side under test

python work/make_signals.py                                 # -> data/sig_*.txt, manifest.json
octave-cli --no-gui --path matlab --eval "run_matlab_side"  # ~30 s, 5 configurations
python python/run_python_side.py                            # ~2 s, 2 configurations
python work/compare.py                                      # -> output/comparison.json
python work/make_figures.py                                 # -> figs/*.png
```

**Runs with zero patient data.** The seven EEG simulations carry their own published
ground truth. If `data/cgm_1min.csv` is absent — as it is here, and always will be —
`make_signals.py` skips the clinical record and the three CGM figures are skipped with
a notice. Verified: a clean run from this folder alone reproduces every EEG number in
`results/`.

## The signals

| Name | Source | Ground truth |
|---|---|---|
| `nguyen_s1` | Nguyen 2019 Supp. Fig. S1 | 2 Hz additive, 14 Hz carrier, 3 Hz AM |
| `juan_f4_b00/04/10` | Juan 2021 Fig. 4 | ⟨4 \| 32⟩ energy must rise with β |
| `juan_f5_tv` | Juan 2021 Fig. 5 | recovered AM power ∝ β², β ramping 0→1 |
| `juan_f6a` / `juan_f6b` | Juan 2021 Fig. 6 | two carriers by one modulator / one carrier by two |
| `cgm_5min` | *not public* | a real 13-day CGM record; excluded by the repository's de-identification rule |

## Related

- `hhsa-clinical-timeseries/` — the Python implementation under test, and the clinical pipeline around it
- `hhsa-closed-loop-prototyping/` — the online sibling
- `2026-08-20_CGMS_HHSA_Case_Lessons_and_Pitfalls.md` — the case that produced the CGM record
