# HHSA closed-loop pitfalls

## Contents

1. Silent scientific errors
2. Timing and streaming errors
3. Stimulation and safety errors
4. Environment and delivery errors

## 1. Silent scientific errors

| Pitfall | Why it survives casual review | Guard |
| --- | --- | --- |
| Use `abs(hilbert(IMF))` as the layer-2 signal | Nearly matches a sinusoid | Use the extrema spline of `abs(IMF)` and test a non-sinusoidal carrier |
| Keep the layer-2 residual | Looks like strong low-frequency power | Exclude the DC residual explicitly |
| Clip samples where `f_am >= f_c` | Produces a populated, plausible spectrum | Drop violations per sample |
| Trust unit tests without synthetic spectra | Code can run while peaks move to the wrong cells | Require known AM/PAC and sawtooth ground truth |
| Use a per-sample Python binning loop | Correct but unusably slow | Use `digitize` plus vectorized accumulation such as `bincount` |
| Ignore extrema plateaus/boundaries | Fails only on realistic waveform edges | Return integer index arrays, mirror extrema, and trim edges |

## 2. Timing and streaming errors

| Pitfall | Observed consequence in the reference prototype | Guard |
| --- | --- | --- |
| Run HHSA in the fast path | About 32 ms/window versus a 1.95 ms sample period | Two-rate architecture |
| Leave causal detection lag uncompensated | About 63 ms, roughly 67 degrees at 3 Hz | Calibrate detection lag and schedule ahead |
| Gate on AM envelope while targeting its trough | Zero triggers in a 60 s run | Gate on carrier RMS |
| Use a low-order envelope filter without ripple tests | Spurious peaks greatly outnumber real peaks | Prefer a stable symmetric detector even if delay is larger |
| Schedule from a holo-bin center | Example: 2.18 Hz estimate for a true 3 Hz timing process | Measure period from successive detections |
| Lead from zero crossing | Large biased phase error | Lead from the detected extremum |
| Feed held blanked samples to HHSA | AM power biased upward, creating positive feedback | Interpolate; accept a conservative downward bias |
| Use an ordinary narrow bandpass without measuring delay | Group delay can exceed an AM cycle | Measure end-to-end phase delay before selection |
| Use a 50 ms LSL chunk timeout | Adds avoidable tens of milliseconds | Use a short timeout and measure actual behavior |
| Measure latency with queued samples | Backlog masquerades as transport delay | Drain inlet backlog first |
| Expect calibration to reveal transport lag | Calibration only sees arrived samples | Add measured median transport lag separately |

## 3. Stimulation and safety errors

- Stimulation artifact can dominate the feature that controls stimulation, creating self-locking feedback. Keep physical output disabled until artifact rejection is validated.
- An amplitude ceiling does not detect a legal-amplitude DC offset. Integrate signed delivered current and enforce net-charge limits.
- If a process stalls, an analog device may hold its last non-zero command. Use an independent watchdog and a backend that zeroes output on arm, stop, trip, and exception.
- Do not auto-rearm after an intermittent trip. Latch the fault until explicit inspection and reset.
- Never infer the device's volts-per-milliamp mapping from software. Measure it with the manual and a current probe.
- A toy plant proves controller logic, not neuroscience or clinical efficacy.

## 4. Environment and delivery errors

- New Python releases may lack wheels for `emd`, `mne`, or `pylsl`. Prefer a project-local environment on a supported interpreter instead of patching scientific dependencies ad hoc.
- A cp950 Windows console can mangle or crash on CJK output. Write UTF-8 files and avoid depending on console rendering.
- Restricted sandboxes can block `.pytest_cache`; run pytest with `-p no:cacheprovider` when cache state is irrelevant.
- Demo scripts can regenerate tracked PNGs. A quick run and a canonical run may not produce the same artifact; inspect the binary diff and regenerate canonically before commit.
- Status counts in documentation drift as tests are added. Treat current command output as evidence and update stale counts deliberately.
- A clean source project and a skills repository are different scopes. Stage explicit artifact paths and verify both worktrees before pushing.
