# Architecture and validation reference

## Contents

1. System split
2. Offline HHSA data path
3. Closed-loop data path
4. Validation matrix
5. Live and hardware boundaries

## 1. System split

Keep five responsibilities separate:

| Responsibility | Typical modules | Timing model |
| --- | --- | --- |
| Offline HHSA | `hhsa/emd.py`, `instantaneous.py`, `holo.py` | Whole record/window |
| Fast control | `closedloop/dsp.py`, `phase.py`, `gating.py`, `controller.py` | Causal, per sample |
| Slow supervision | `closedloop/supervisor.py`, `calibration.py` | Periodic trailing window |
| Live transport | `closedloop/lsl.py`, `live.py`, `run_live.py` | Chunked stream + timestamps |
| Output safety | `stimulator.py`, `hardware.py` | Per command + watchdog |

Do not collapse offline and online signal processing into one function. Their boundary and latency assumptions are different.

## 2. Offline HHSA data path

```text
EEG x(t)
  -> layer-1 EMD -> carrier IMFs c_j(t)
  -> instantaneous carrier frequency f_c(t)
  -> spline envelope through extrema of abs(c_j(t))
  -> layer-2 EMD -> envelope IMFs c_jk(t), excluding DC residual
  -> instantaneous AM frequency f_am(t) and amplitude a_jk(t)
  -> discard invalid/edge samples and samples with f_am >= f_c
  -> vectorized accumulation into H(f_am, f_c[, time])
```

Recommended acceptance set:

- 16 Hz carrier under a 2 Hz envelope: one peak near `(f_c=16, f_am=2)`.
- Same signal with noise: peak remains within the declared log-bin tolerance.
- Masked sifting: agrees within the same tolerance.
- 40 Hz gamma modulated by 6 Hz theta: gamma AM power is concentrated near theta.
- Sawtooth-like carrier with true 2 Hz AM: harmonic structure does not create broad false AM power.

## 3. Closed-loop data path

```text
multichannel EEG
  -> Laplacian montage
  -> causal carrier-band selection
  -> carrier RMS -----------------------> amplitude gate
  -> AM envelope -> phase extrema ------> compensated scheduler
event markers --------------------------> event gate
refractory -----------------------------> trigger decision
slow HHSA window ------------------------> target band + intensity
trigger command ------------------------> simulated/recording backend by default
```

Calibration must estimate at least individual carrier frequency, carrier-energy gate, phase-detector hysteresis, detection lag, and AM-power normalization. Transport lag is measured separately because calibration on received samples cannot observe network/device transit time.

## 4. Validation matrix

Run from the project root when those entry points exist:

```bash
python validate_ground_truth.py --no-plot
python -m pytest tests -q -p no:cacheprovider
python demo_closed_loop.py --quick
```

The quick demo may rewrite a tracked figure. Run the canonical full demo before committing a figure, and compare `git diff` afterward.

| Change area | Minimum evidence |
| --- | --- |
| EMD/extrema/envelope | Reconstruction/order tests, boundary and plateau regressions, five ground-truth signals |
| Holo binning | Constraint, time-resolved sum, vectorization/performance, peak location |
| Phase/envelope | Extremum accuracy, ripple rejection, measured compensation improvement |
| Gating/scheduling | Both gate outcomes, event window, refractory, pending-event cancellation |
| Supervisor | AM-power response, smoothing, slew limit, blanked-window skip |
| LSL | Labels, actual sample rate, irregular rate, gap reset, latency/backlog |
| Stimulator | bounds, overlap, ramp, duty cycle, zero outside burst |
| Hardware interlock | rail/current clamp, slew, signed net charge, watchdog, dose, impedance, latch/reset, fail-closed backend errors |

## 5. Live and hardware boundaries

Use a mock LSL outlet before an amplifier. Verify channel labels rather than relying on positions. Reject materially wrong or irregular sampling rates. Drain backlog before latency measurement, use a short pull timeout, and treat timestamp discontinuity as a state reset.

For hardware work, require a device manual and measured transfer function. Keep waveform generation, backend I/O, and an independent interlock separate. A software watchdog must continue ticking even when no burst is active. Account for delivered signed current, not only requested amplitude. Latch faults until explicit reset.
