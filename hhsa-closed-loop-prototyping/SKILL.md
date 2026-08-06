---
name: hhsa-closed-loop-prototyping
description: Build, audit, debug, and validate Python research prototypes that combine Holo-Hilbert Spectral Analysis (HHSA), EEG acquisition, AM-envelope phase detection, and closed-loop tACS/TMS-style control. Use for nested two-layer EMD and holo-spectrum work, synthetic ground-truth validation, two-rate causal controller design, LSL live-stream integration, latency and artifact handling, simulated stimulation, or safety-interlock review. Treat all outputs as research prototypes and keep physical stimulation disabled unless the user supplies a verified device protocol, independent hardware safeguards, ethics approval, and qualified supervision.
---

# HHSA Closed-Loop Prototyping

## Preserve the safety boundary

- Default to synthetic signals, `SimulatedStimulator`, `NullBackend`, or `RecordingBackend`.
- Keep the LSL path marker-only unless a separately reviewed hardware layer exists.
- Do not invent a vendor serial protocol, voltage-to-current scale, impedance rule, or device command.
- Do not describe a same-process software interlock as a medical safety system.
- Require certified equipment, an independent current limiter/interlock, an emergency stop, ethics approval, and qualified human supervision before physical stimulation.

## Route the task

Classify the requested work before editing:

1. **Offline HHSA:** EMD, envelopes, instantaneous parameters, binning, spectra, or clinical features.
2. **Fast closed loop:** causal filtering, phase detection, gating, refractory logic, stimulation scheduling, or simulation.
3. **Slow supervisor:** trailing-window HHSA, target selection, AM normalization, or intensity adaptation.
4. **Live acquisition:** LSL discovery, labels, sample-rate verification, gaps, timestamps, backlog, or marker output.
5. **Hardware boundary:** backend abstraction, watchdog, charge accounting, dose, impedance, or fail-closed behavior.

Read [architecture-and-validation.md](references/architecture-and-validation.md) for the selected path. Read [pitfalls.md](references/pitfalls.md) before changing algorithms, latency compensation, blanking, or hardware code.

## Establish a trustworthy baseline

1. Locate the project root and read its local `CLAUDE.md`, `AGENTS.md`, or equivalent instructions.
2. Inspect `git status` and preserve unrelated user changes.
3. Record the Python version and dependency state.
4. Run the bundled audit from the project root:

```bash
python path/to/hhsa-closed-loop-prototyping/scripts/audit_hhsa_project.py . --profile core
```

Use `--profile static` when dependencies are unavailable. Use `--profile full` only when regenerating the closed-loop demo figure is intended.

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
- Detect phase from the AM envelope while gate amplitude from carrier energy; do not gate trough targets on the envelope itself.
- Measure detection lag at calibration and add transport lag measured after draining acquisition backlog.
- Base scheduling on measured extrema periods, not the supervisor's holo-bin center.
- Prefer deterministic compensable delay over low-delay detectors that generate spurious events.
- Interpolate artifact-blanked samples before slow HHSA; do not sample-and-hold them.
- Reset filters, pending events, and time state after a detected stream discontinuity.

## Validate proportionally to the change

- HHSA or EMD change: run ground truth plus HHSA tests.
- Fast controller change: run regression/controller tests plus the closed-loop demonstration.
- LSL change: run LSL tests, then mock-stream tests for wrong rate and packet loss.
- Hardware/interlock change: run all hardware tests and a `RecordingBackend` dry run; never test first on a person.
- Documentation-only skill change: run `quick_validate.py` on this skill and execute the audit script against a known project.

Treat a plausible plot or a firing controller as insufficient evidence. Report exact checks, counts, warnings, and any untested hardware assumptions.

## Hand off clearly

Summarize:

- path changed and why;
- validation commands and results;
- measured latency/phase behavior when relevant;
- whether any figures were regenerated;
- remaining safety, device-manual, acquisition, or ethics blockers.
