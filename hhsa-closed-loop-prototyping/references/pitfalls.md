# HHSA closed-loop pitfalls

## Contents

1. Silent scientific errors
2. Timing and streaming errors
3. Stimulation and safety errors
4. Environment and delivery errors
5. Fixed-point and hardware-translation errors

## 1. Silent scientific errors

| Pitfall | Why it survives casual review | Guard |
| --- | --- | --- |
| Use `abs(hilbert(IMF))` as the layer-2 signal | Nearly matches a sinusoid | Use the extrema spline of `abs(IMF)` and test a non-sinusoidal carrier |
| Keep the layer-2 residual | Looks like strong low-frequency power | Exclude the DC residual explicitly |
| Clip samples where `f_am >= f_c` | Produces a populated, plausible spectrum | Drop violations per sample |
| Trust unit tests without synthetic spectra | Code can run while peaks move to the wrong cells | Require known AM/PAC and sawtooth ground truth |
| Use a per-sample Python binning loop | Correct but unusably slow | Use `digitize` plus vectorized accumulation such as `bincount` |
| Ignore extrema plateaus/boundaries | Fails only on realistic waveform edges | Return integer index arrays, mirror extrema, and trim edges |
| Report a mean phase error without its SD, or an SD without its mean | One number reads as a complete accuracy statement | Report both: a large mean with a small SD is compensable group delay, a small mean with a large SD is irreducible jitter, and the two demand different fixes |
| Validate an AM demodulator with an additive cross-frequency test signal | Spectra and phase plots look correct and the test passes | Drive the test with a multiplicative signal such as `(1 + m*sin(2*pi*f_am*t)) * cos(2*pi*f_c*t)`; an additive sum carries no envelope to recover, so the demodulator is never exercised |

## 2. Timing and streaming errors

Middle-column numbers are measured in the reference prototype unless a row is marked `Source analysis`, which refers to the separate streaming AM simulator described in the FPGA prototyping note (`FPGA 即時閉迴路神經調控演算法原型設計.md` — one document, one name, full provenance in [fpga-porting.md](fpga-porting.md) section 1). The two systems have different filters, sample rates, and target frequencies; never merge their numbers or quote one as the other's result.

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
| Hard-code the AM band center frequency | Source analysis: individual dominant AM frequency differs and drifts within a task (figures and their status in [fpga-porting.md](fpga-porting.md) section 1), so a fixed band silently slides off the target while still emitting triggers | Estimate the dominant AM frequency online at the buffer end, or adapt the IIR coefficients with a Kalman filter |
| Store the latency compensation as a constant in degrees | Source analysis: a degrees-valued offset is only correct at the one f_am it was derived at, and goes wrong the moment an adaptive tracker moves the band ([fpga-porting.md](fpga-porting.md) section 7 works the arithmetic and explains why the simulator's own figure must not be copied into a register) | Store the compensation in seconds or samples, convert to a phase code at the current f_am on every update, re-derive it whenever the band moves, and verify the sign empirically before applying it |

## 3. Stimulation and safety errors

- Stimulation artifact can dominate the feature that controls stimulation, creating self-locking feedback. Keep physical output disabled until artifact rejection is validated against an artifact recorded from the intended amplifier/stimulator pair, with the residual quantified. A simulated artifact tests only the artifact model you wrote and cannot license an artifact-tolerance claim.
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

## 5. Fixed-point and hardware-translation errors

These apply when a floating-point Python prototype is translated toward an FPGA or DSP target. The translation described in the FPGA prototyping note is design guidance for a port that has not been built, synthesized, timed, or validated. Do not write or accept text that implies otherwise.

| Pitfall | Why it survives casual review | Guard |
| --- | --- | --- |
| Treat a first derivative as an exact quadrature signal for CORDIC vector mode | Phase is only mildly biased, so trigger timing still looks reasonable | The derivative carries an omega scale factor, so `sqrt(x^2 + xdot^2)` is not the envelope unless normalized; normalize by the nominal center frequency and compare against a Hilbert reference. Magnitude is badly wrong long before phase is, so a magnitude-based amplitude gate fails first and quietly. The residual phase bias is not a constant either — it averages to zero and ripples at twice the signal frequency — so budget it into the phase-error SD, never into a phase-offset register |
| Quantize biquad coefficients without checking pole migration | The filter still runs and the passband looks approximately right | Worst for narrow low-frequency bands, which is exactly where the theta AM filter sits. Run the fixed-point path and the float reference on identical input and report a bounded max absolute output difference plus identical trigger sample indices — bit-exactness against float is unachievable in Qm.n and is not the gate. Inspect the realized response, not the requested one |
| Implement Direct Form II in fixed point without headroom analysis | Input and output both stay inside legal range while internal states overflow | Use Direct Form I: states are plain input/output samples, one wide accumulator with guard bits, one rounding at the output. Direct Form II transposed is the floating-point structure; in fixed point its states hold partial sums and must be carried at accumulator width. Scale explicitly per section and use saturating arithmetic rather than wraparound |
| Assume the FPGA port inherits the Python prototype's validation | Both are described as "the same algorithm" | It inherits none of it. Rerun ground-truth, phase-accuracy, and timing checks against the fixed-point implementation as a separate system |
| Place artifact rejection after the demodulator | The pipeline diagram still shows an artifact stage, so the design looks covered | A 2 mA tACS artifact is reported at more than 10,000x the EEG (second-hand figure, [fpga-porting.md](fpga-porting.md) section 1); once it enters the envelope detector the phase estimate is already corrupted and the loop locks to its own output. Put adaptive noise canceling or a spatial projector, for example a Laplacian montage template, ahead of the demodulator, with actively driven ground and common-mode rejection in hardware. Placement is what you control; efficacy is not. Online tACS artifact removal is unsolved — saturation, non-stationarity, and impedance drift leave a residual that can mimic a phase-locked envelope — so correct placement downgrades this pitfall, it does not close it. Keep physical output disabled until residual artifact is measured on the rig |
| Quote FPGA resource, clock, or latency figures | Numbers with units read as measurements | Do not state LUT/DSP counts, clock rates, pipeline latency, or vendor IP core parameters that were never synthesized or measured. Label any figure that is an estimate or a worked example as such |
