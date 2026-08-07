---
name: hhsa-closed-loop-prototyping
description: Build, audit, debug, and validate Python research prototypes that combine Holo-Hilbert Spectral Analysis (HHSA), EEG acquisition, AM-envelope phase detection, and closed-loop tACS/TMS-style control. Use for nested two-layer EMD and holo-spectrum work, synthetic ground-truth validation, two-rate causal controller design, streaming AM-phase detection and phase-locked trigger prototypes, group-delay and jitter compensation, LSL integration, stimulation-artifact rejection ahead of the demodulator, adaptive AM-band tracking, safety-interlock review, or fixed-point / FPGA / DSP porting with CORDIC demodulation. Trigger on the intent even if the user never says HHSA - "phase-locked stimulation", "real-time EEG trigger", "my trigger fires late", "closed-loop tACS", "lock to the theta envelope", "port my phase detector to FPGA". Research prototypes only; physical stimulation stays disabled.
---

# HHSA Closed-Loop Prototyping

## Preserve the safety boundary

- Default to synthetic signals, `SimulatedStimulator`, `NullBackend`, or `RecordingBackend`.
- Keep the LSL path marker-only unless a separately reviewed hardware layer exists.
- Do not invent a vendor serial protocol, voltage-to-current scale, impedance rule, or device command.
- Do not describe a same-process software interlock as a medical safety system.
- Require certified equipment, an independent current limiter/interlock, an emergency stop, ethics approval, and qualified human supervision before physical stimulation.
- Nothing in this project has been ported to fixed point, synthesized, timed, or measured on hardware, and no stimulation has been delivered. Treat all FPGA and fixed-point material as design guidance for a port that does not exist; never present it as verified hardware behavior.
- The trigger output stays marker-only, simulated, or logged in every implementation, software or hardware alike. A GPIO pin is the same boundary as a software backend; wiring it to anything that can deliver current requires the full set of conditions in the bullet above.

## Route the task

Classify the requested work before editing:

1. **Offline HHSA:** EMD, envelopes, instantaneous parameters, binning, spectra, or clinical features.
2. **Fast closed loop:** causal filtering, phase detection, gating, refractory logic, stimulation scheduling, or simulation.
3. **Slow supervisor:** trailing-window HHSA, target selection, AM normalization, or intensity adaptation.
4. **Live acquisition:** LSL discovery, labels, sample-rate verification, gaps, timestamps, backlog, or marker output.
5. **Hardware boundary:** backend abstraction, watchdog, charge accounting, dose, impedance, or fail-closed behavior.
6. **Streaming AM-phase prototype:** sliding-buffer demodulation, last-sample phase, trigger tolerance, refractory, phase-error statistics, or the golden-reference validation figure.
7. **Fixed-point / hardware port:** biquad cascades, CORDIC demodulation, quadrature synthesis, word widths, phase-offset registers, or the FPGA/DSP verification ladder.

Read [architecture-and-validation.md](references/architecture-and-validation.md) for the selected path. Read [realtime-am-reference.md](references/realtime-am-reference.md) for route 6 and for any streaming reference behavior a later port must reproduce. Read [fpga-porting.md](references/fpga-porting.md) for route 7. Read [pitfalls.md](references/pitfalls.md) before changing algorithms, latency compensation, blanking, artifact rejection, fixed-point code, or hardware code.

## Establish a trustworthy baseline

1. Locate the project root and read its local `CLAUDE.md`, `AGENTS.md`, or equivalent instructions.
2. Inspect `git status` and preserve unrelated user changes.
3. Record the Python version and dependency state.
4. Run the bundled audit from the project root **when the project uses the two-rate `hhsa/` + `closedloop/` layout** — the script checks for those paths and reports `fail` without them. Invoke it from this skill's own `scripts/` directory:

```bash
python <this-skill-directory>/scripts/audit_hhsa_project.py . --profile core
```

Use `--profile static` when dependencies are unavailable. Use `--profile full` only when regenerating the closed-loop demo figure is intended.

For a standalone streaming prototype (routes 6-7) skip the audit and use the acceptance thresholds in [realtime-am-reference.md](references/realtime-am-reference.md) section 7 as the baseline instead.

## Protect the offline HHSA invariants

- Feed layer 2 with the cubic-spline envelope through extrema of `abs(IMF)`; do not substitute Hilbert magnitude.
- Exclude the positive DC residual from layer 2.
- Compute instantaneous frequency without changing sample length.
- Mirror extrema at boundaries or pad explicitly, then trim unreliable Hilbert/spline edges.
- Enforce `f_am < f_c` per sample by dropping violations.
- Use logarithmic/dyadic bin edges and vectorized accumulation.
- Keep power linear for computation; convert with `10*log10(power + eps)` only for display.
- Prefer masked sifting, then CEEMDAN, then plain sift when mode mixing matters.

Validate with synthetic signals before clinical EEG: clean AM, noisy AM, masked-sift AM, known theta-gamma PAC, and a non-sinusoidal carrier that must not create harmonic PAC.

## Protect the online invariants

- Keep offline whole-window HHSA out of the per-sample fast path.
- Use a two-rate design: causal fixed-state processing for timing and slower trailing-window HHSA for target/intensity updates.
- Detect phase from the AM envelope while gating amplitude on a slow RMS of carrier energy; do not gate trough targets on the instantaneous envelope.
- Measure detection lag at calibration and add transport lag measured after draining acquisition backlog.
- Base scheduling on measured extrema periods, not the supervisor's holo-bin center.
- Prefer deterministic compensable delay over low-delay detectors that generate spurious events.
- Interpolate artifact-blanked samples before slow HHSA; do not sample-and-hold them.
- Reset filters, pending events, and time state after a detected stream discontinuity.
- Pin the phase convention before quoting any target or offset. Under `angle(hilbert(.))`, 0 deg is the envelope peak and +/-180 deg the trough.
- Latency compensation, artifact placement, and mean-vs-SD reporting each have exact rules with traps that survive review; read [pitfalls.md](references/pitfalls.md) sections 2 and 5 before touching any of them.
- Place artifact rejection ahead of the demodulator. A simulated artifact is a smoke test, not evidence: it exercises only the artifact model you wrote. No loop may be described as artifact-tolerant without an artifact recorded from the intended amplifier/stimulator pair, with the residual quantified, not merely reduced. Physical output stays disabled either way.

## Port to fixed point only with evidence

- Port when jitter, not median lag, is the binding constraint: carrier phase at beta or gamma, not envelope phase at theta, where median lag is compensable in software.
- Require a bounded, reported max-absolute output difference against the float reference plus identical trigger sample indices on the same record, before making any timing, resource, or accuracy claim. Bit-exactness against float is unachievable in Qm.n and is not the gate.
- Treat a derivative used as a quadrature signal as an approximation: normalize it by the nominal center frequency and check the sign. Its residual bias ripples at twice the signal frequency and averages to zero, so it belongs in the phase-error SD budget, not in a calibrated offset register.
- Do not quote LUT/DSP counts, clock rates, pipeline latency, or vendor IP parameters for a design that was never synthesized or measured.

## Validate proportionally to the change

- HHSA or EMD change: run ground truth plus HHSA tests.
- Fast controller change: run regression/controller tests plus the closed-loop demonstration.
- Streaming AM-phase prototype change: rerun the fixed-seed synthetic run, regenerate all four validation panels, and report trigger count, mean phase error, and SD of phase error separately.
- Fixed-point change: rerun the float reference and the fixed-point model on the same record, report the output difference and matching trigger sample indices, and document pole radii and headroom before any timing claim.
- LSL change: run LSL tests, then mock-stream tests for wrong rate and packet loss.
- Hardware/interlock change: run all hardware tests and a `RecordingBackend` dry run; never test first on a person.
- Documentation-only skill change: execute the audit script against a known project and re-check that every relative link in this file and in `references/` resolves.

Treat a plausible plot or a firing controller as insufficient evidence. Report exact checks, counts, warnings, and any untested hardware assumptions.

## Hand off clearly

Summarize:

- path changed and why;
- validation commands and results;
- measured latency/phase behavior when relevant;
- whether any figures were regenerated;
- remaining safety, device-manual, acquisition, or ethics blockers.
