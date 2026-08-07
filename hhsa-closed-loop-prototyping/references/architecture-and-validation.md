# Architecture and validation reference

## Contents

1. System split
2. Offline HHSA data path
3. Closed-loop data path
4. Validation matrix
5. Live and hardware boundaries
6. Hardware translation target
7. Streaming reference prototype

## 1. System split

Keep six responsibilities separate:

| Responsibility | Typical modules | Timing model |
| --- | --- | --- |
| Offline HHSA | `hhsa/emd.py`, `instantaneous.py`, `holo.py` | Whole record/window |
| Fast control | `closedloop/dsp.py`, `phase.py`, `gating.py`, `controller.py` | Causal, per sample |
| Slow supervision | `closedloop/supervisor.py`, `calibration.py` | Periodic trailing window |
| Live transport | `closedloop/lsl.py`, `live.py`, `run_live.py` | Chunked stream + timestamps |
| Output safety | `stimulator.py`, `hardware.py` | Per command + watchdog |
| Fixed-point / hardware target | No module in this project; see section 6 | Pipelined, per sample |

Do not collapse offline and online signal processing into one function. Their boundary and latency assumptions are different.

The sixth row is a *target*, not an implemented layer. Nothing in this project runs in fixed point or on hardware. Keep it in the table only so the Python fast path is written in a form a port could follow: fixed-size buffers, bounded state, no whole-recording operations. Do not report timing, resource, or accuracy figures for that row.

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

### 3.1 Where artifact rejection sits

Artifact rejection belongs **ahead of the demodulator** — before the carrier band-pass, envelope extraction, and phase estimator. Never after. Anything downstream of the demodulator inherits an already-corrupted phase estimate and cannot recover it.

- The quantity to reject: a 2 mA tACS stimulation artifact is reported to exceed the EEG by more than 10,000x. That figure is second-hand — carried from the FPGA prototyping note, not traced to a primary reference and not measured here (see [fpga-porting.md](fpga-porting.md) section 1). Cite a primary source or drop the number before repeating it, and do not treat the ratio as a design specification. The consequence is what matters and does not depend on the exact ratio: at that scale the artifact, not the brain, sets the estimated AM phase, and the loop locks onto its own output.
- Algorithm side: adaptive noise canceling driven by a reference of the delivered stimulation waveform, or a real-time spatial projector such as a fixed Laplacian montage template applied per sample. Both must be causal and fixed-state to stay in the fast path. Placement is what the algorithm controls; efficacy is not. Online tACS artifact removal is an open problem — amplifier saturation destroys signal no downstream stage can restore, and the artifact drifts with impedance, heartbeat, respiration, and movement — so both methods leave a residual that can itself present as a phase-locked envelope. Neither method makes this box solved.
- Hardware side: actively driven ground and common-mode rejection at the amplifier. This is an equipment property, not something the algorithm can supply. State it as a requirement on the rig, not as a step in the code.
- Blanking, where used, is still subject to the existing rule: interpolate blanked samples before slow HHSA, do not sample-and-hold them.
- Until artifact rejection is validated against a measured artifact, keep physical output disabled and the loop marker-only.

### 3.2 Adaptive band tracking

Do not hard-code the AM center frequency in the fast path.

- The dominant AM frequency is individual and drifts within a cognitive task. The figures, and their second-hand status, are in [fpga-porting.md](fpga-porting.md) section 1 — do not restate them independently here.
- Consequence: the supervisor owns retuning the fast path's AM band. It should push updated band edges (or updated filter coefficients) rather than leaving the fast path to guess.
- Options: online dominant-frequency estimation from the trailing window, or a Kalman filter adapting the IIR coefficients. Both are supervisor-rate work, not per-sample work.
- Retuning invalidates any latency compensation expressed in degrees. Store the compensation as a **delay in seconds** and recompute degrees at the current f_am on every retune. A compensation frozen in degrees becomes wrong the moment the band moves.
- Slew-limit band changes the same way intensity changes are slew-limited, and do not retune inside a blanked window.
- Retuning also invalidates the scheduler's period estimate. Re-measure the extremum period after a band change instead of carrying the old one forward.

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
| Streaming AM-phase prototype | The four validation panels (polar trigger-phase histogram, linear phase-error distribution, estimated-vs-true phase trajectory, raw-vs-reconstructed AM time series), plus mean phase error and SD of phase error reported **separately** — a small SD with a large mean is precise and inaccurate, and one number hides that |
| Artifact rejection | Necessary but never sufficient: SD of phase error with a simulated artifact injected, compared against the clean case on the same signal, both reported. A simulated artifact tests only the artifact model you wrote, so it cannot license an artifact-tolerance claim. That requires an artifact **recorded from the intended amplifier/stimulator pair**, with residual artifact quantified. Physical output stays disabled until that measurement exists |
| Fixed-point port | A **bounded, reported max-absolute output difference** against the float reference on a fixed test vector, plus identical trigger sample indices on the same record, established **before** any timing, resource, or latency claim is made. Bit-exactness against float is not achievable in Qm.n and is not the gate |

## 5. Live and hardware boundaries

Use a mock LSL outlet before an amplifier. Verify channel labels rather than relying on positions. Reject materially wrong or irregular sampling rates. Drain backlog before latency measurement, use a short pull timeout, and treat timestamp discontinuity as a state reset.

For hardware work, require a device manual and measured transfer function. Keep waveform generation, backend I/O, and an independent interlock separate. A software watchdog must continue ticking even when no burst is active. Account for delivered signed current, not only requested amplitude. Latch faults until explicit reset.

## 6. Hardware translation target

Design guidance for a port that has **not** been built. Nothing described here has been ported, synthesized, timed, or measured, and no LUT/DSP counts, clock rates, latencies, or vendor IP parameters should be quoted for it.

The block-by-block Python-to-hardware mapping lives in exactly one place: [fpga-porting.md](fpga-porting.md) section 3. Do not copy it here — a second copy is how the two files drift, and the drift lands on details that matter (filter structure, what the amplitude gate reads, what units the compensation is stored in). Read that file for the block detail, fixed-point choices, and what must be measured rather than assumed.

## 7. Streaming reference prototype

Build this before anything else. It is built **before** the two-rate controller, and it is the golden reference the two-rate controller and any later port are checked against. It is small enough to be read in one sitting and strict enough to expose group delay honestly. It earns that role because it is causal, fixed-state, and fully specified: any later variant — adaptive band, artifact rejection, fixed-point port — is validated by comparing against its output on the same input, not by looking plausible on its own.

Read [realtime-am-reference.md](realtime-am-reference.md) section 3 for the algorithm and section 4 for the parameters — they are specified there and nowhere else. Section 6 there carries the baseline measured by the separate streaming AM simulator described in the FPGA prototyping note (`FPGA 即時閉迴路神經調控演算法原型設計.md`), which is **not** this project's numbers, and the reasons accuracy and precision must be reported separately.
