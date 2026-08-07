# FPGA and fixed-point porting reference

## Contents

1. Number provenance and system boundary
2. When to port at all
3. Module-by-module translation
4. Pipeline
5. Fixed-point discipline: what actually breaks
6. The quadrature caveat
7. The phase-offset compensation register
8. Verification ladder

How to move a validated Python streaming AM-phase controller onto fixed-point FPGA/DSP logic.
Everything here is design guidance for a port that has **not** been built. No HDL exists, nothing
has been synthesized, timed, or measured on silicon. Do not state or imply otherwise, and do not
report LUT/DSP counts, clock rates, or hardware latency figures: none have been obtained.

## 1. Number provenance and system boundary

This section is the **single provenance table** for every source-derived number in this skill.
Other files point here rather than restating attribution. Two different systems produce numbers.
Never average them, never quote one as validation of the other, and always name the system.

The document called **the FPGA prototyping note** throughout this skill is
`FPGA 即時閉迴路神經調控演算法原型設計.md`. It describes the streaming AM simulator, proposes an
FPGA translation, and discusses tACS artifact and adaptive tracking. It is one document; use that
one name for it.

| System | What it is | Its numbers |
| --- | --- | --- |
| Streaming AM simulator | The Python streaming closed-loop script described in the FPGA prototyping note: 500 ms sliding buffer at 1 kHz, carrier band-pass 16-24 Hz, Hilbert magnitude, AM band-pass 2-6 Hz, Hilbert phase of the last buffer sample, fire when phase is within 15 deg of a -90 deg target, 150 ms refractory | On 10 s of synthetic multiplicative signal `x(t) = 0.5*sin(2*pi*f_am*t) + (1.0 + 0.8*sin(2*pi*f_am*t))*cos(2*pi*f_c*t) + noise` with `f_am = 4 Hz`, `f_c = 20 Hz`: 39 triggers; mean trigger phase -154.47 deg; mean phase error -64.47 deg; SD of phase error 10.51 deg. The note attributes the mean to about 45 ms of filter group delay — **back-computed from the phase error, not measured**; see section 7 |
| Two-rate reference project | The `hhsa/` + `closedloop/` prototype this skill was written from | **Measured:** 63 ms detection lag = 67 deg at 3 Hz; 253 spurious versus 89 real peaks for a 2nd-order envelope low-pass; 225 ms group delay for a true 2nd-order narrow band-pass; about 10 ms median LSL latency after draining backlog; live LSL jitter (p95 - median) of 3.4 ms = 4.1 deg at 3.4 Hz. **Cited, not measured here:** Guth 2026's ~6-12 ms LSL jitter, used as the worst-case default in `latency_budget(target_hz, jitter_ms=12.0)` |

The two systems use different signal models, different filters, and different AM frequencies. A
phase error measured on one says nothing about the other.

Other figures carried from the FPGA prototyping note, listed here so no other file has to restate
their attribution:

| Figure | Status |
| --- | --- |
| Dominant AM frequency about 3.3 Hz (high working-memory capacity) versus 5.2 Hz (low), drifting within a task; attributed by the note to Liang 2021 / Cheng 2023 | Second-hand. Not verified against the primary papers here, and not measured in either system |
| A 2 mA tACS artifact exceeds the EEG by more than 10,000x | Second-hand order-of-magnitude figure; the note cites references this skill has not checked, and nothing here measured it. Cite a primary source or drop the number before repeating it, and never treat the ratio as a design specification. The consequence, not the exact ratio, is what matters: at any comparable scale the artifact sets the estimated AM phase and the loop locks onto its own output |

## 2. When to port at all

Split latency into two quantities and treat them differently.

- **Median lag is compensable.** It is a fixed offset. Measure it, fold it into the schedule or the
  phase-offset register, and it disappears from the mean phase error.
- **Jitter is not compensable.** It sets the achievable SD of trigger phase and therefore the
  feasibility of the whole design.

Jitter converts to phase as `error_deg = jitter_s * f * 360`. Worked example (arithmetic, not a
measurement) at two anchors: the reference project's own **measured** live jitter of 3.4 ms, and
Guth 2026's **cited** ~6-12 ms, which the reference project uses as a worst-case default:

| Target frequency | 3.4 ms (measured here) | 12 ms (cited worst case) |
| --- | --- | --- |
| 3 Hz (AM envelope) | 3.7 deg | 13 deg |
| 6 Hz (AM envelope) | 7.3 deg | 26 deg |
| 20 Hz (beta carrier) | 24 deg | 86 deg |
| 40 Hz (gamma carrier) | 49 deg | 173 deg |

Which column you are entitled to use is a measurement question about your own transport, not a
choice. Measure it before invoking either.

Decision rule:

- **Do not port** when the target is AM-envelope phase at 3-6 Hz and the PC/LSL path's jitter is
  tens of milliseconds. Targeting the modulator is precisely what makes a software implementation
  defensible.
- **Port** when the target is carrier phase at beta or gamma *and* your measured jitter puts the
  phase error outside your tolerance. The same jitter that is negligible on an envelope is
  order-of-magnitude worse on a carrier — but note that at the reference project's measured
  3.4 ms a 20 Hz carrier costs 24 deg, not 86 deg, so this rule is decided by your own
  measurement and not by the worst-case column.
- **Port** when jitter, not median lag, is the binding constraint: an OS/transport path that cannot
  bound its worst case, a blanking or artifact-suppression stage that must run within one sample
  period, or a required response time below the transport's own variability.
- **Do not port** merely because median lag is large. Reduce or compensate it in software first.
- **Do not port an unvalidated algorithm.** The float reference must already pass synthetic
  ground truth before anyone writes HDL; otherwise the port has no oracle.

Cost to state honestly in any plan: porting replaces a debuggable Python path with an HDL path that
needs its own full verification ladder (section 8), plus fixed-point analysis that has no software
counterpart.

## 3. Module-by-module translation

| Python construct | Hardware construct | What actually changes | What to check |
| --- | --- | --- | --- |
| 500 ms sliding buffer, re-filtered every step | Shift-register delay line plus persistent filter state | Hardware filters the stream once and carries state; it does not recompute a window. Edge behavior, warm-up, and any per-window trimming vanish | Re-validate against the float reference: the streaming result is not identical to per-window refiltering |
| Butterworth via `butter` + `lfilter` | Cascaded biquad sections, **Direct Form I**, fixed point on DSP slices (section 5 rejects the note's Direct Form II) | Coefficients quantize; poles move; scaling becomes explicit | Pole radii after quantization; per-section headroom; bounded output difference and identical trigger indices against the float reference (section 5) |
| Any zero-phase step (`filtfilt`) | No equivalent | Non-causal filtering cannot be ported | If the reference used it in the online path, the reference is wrong, not the port |
| `abs(hilbert(x))` (envelope) | CORDIC vector mode, magnitude output | Quadrature must be synthesized in hardware; magnitude carries the CORDIC gain and any quadrature scaling error | Section 6; compare envelope against a true Hilbert reference |
| `angle(hilbert(x))` (phase) | CORDIC vector mode, arctan output, Q15 | Phase becomes a fixed-width integer code; wrap arithmetic replaces float angle arithmetic | Wrap handling at +/-180 deg; monotonic phase advance; Q15 resolution against the tolerance window |
| Tolerance test `abs(phase - target) < tol` | Comparator on wrapped phase codes | Comparison must be modular, not linear | A target near +/-180 deg must not split the acceptance window |
| Amplitude gate | Squarer plus single-pole IIR on the carrier-stage CORDIC magnitude, then a comparator on that slow RMS | Same invariant as software: the gate asks "is the rhythm present at all", which the per-sample magnitude cannot answer because it is the very envelope being phase-targeted | Gate input is time-averaged, not the per-sample magnitude; verify the RMS time constant exceeds several `1/f_am` |
| Refractory period | Down-counter loaded on trigger | Counter units are samples, not seconds | Recompute the load value if the sample rate changes |
| Trigger emission | Single-cycle GPIO pulse into a marker or logging input **by default** — a simulated/recording backend, the amplifier's event input, or a scope. Connecting this pin to anything that can deliver current is not a datapath decision; it needs the full boundary at rung 5 of section 8 | Pulse width becomes a hardware parameter | Width long enough for the downstream logger to latch, and that the pin is verified not to be wired to a stimulator gate |
| `float64` throughout | Qm.n words, saturating arithmetic | Overflow, quantization noise, and limit cycles become possible | Section 5 |
| Latency constant in code | Phase-offset register | The offset is frequency-dependent | Section 7 |

## 4. Pipeline

```text
EEG in (ADC, 1 kHz)
  |
  v
[ artifact suppression: ANC or real-time spatial projector ]   <-- before demodulation, never after
  |
  v
[ biquad cascade: carrier band-pass (e.g. beta 16-24 Hz) ]
  |
  v
[ shift-register delay line ]  -->  aligned sample x and its quadrature partner
  |
  v
[ CORDIC vector mode: magnitude ]  = AM envelope, per sample
  |
  +------------------------------------+
  |                                    |
  v                                    v
[ squarer + single-pole IIR,     [ biquad cascade: AM band-pass (e.g. theta 2-6 Hz) ]
  tau >= several AM cycles ]           |
  = carrier RMS                        v
  |                              [ delay line + quadrature partner ]
  v                                    |
[ amplitude gate:                      v
  carrier RMS > threshold ]      [ CORDIC vector mode: arctan ]  = AM phase (Q15)
  |                                    |
  |                                    v
  |          [ phase-offset register: + tau_s * f_am converted to phase code ]
  |                                    |
  |                                    v
  +--------------------------> [ phase comparator: |phase - target| < tolerance ]
                                       |
                                       v
                             [ refractory down-counter ]
                                       |
                                       v
                                [ GPIO trigger pulse ]
```

Two placement rules the diagram encodes:

- Artifact suppression sits **before** the demodulator. A tACS artifact is reported to exceed the
  EEG by more than four orders of magnitude (section 1); if it reaches the CORDIC stages the phase
  estimate is a function of the stimulator's own output. **Correct placement is necessary and
  nowhere near sufficient.** Online tACS artifact removal is an open problem, not a solved block:
  amplifier saturation destroys signal that no downstream stage can restore, and the artifact is
  non-stationary — it drifts with impedance, heartbeat, respiration, and movement — so ANC and
  spatial projectors leave a residual that can itself look like a phase-locked envelope and be
  locked onto. Treat this box as unvalidated, and keep physical output disabled, until residual
  artifact has been measured on the actual rig.
- The amplitude gate reads a **slow RMS of the carrier magnitude**, averaged over several
  modulator cycles, while the phase comparator reads the **AM phase** derived from that same
  magnitude stream. The two are not different signals; they are different time scales of one
  signal, and the gate is the averaged one. Gating on the instantaneous magnitude rejects
  precisely the low-amplitude samples a trough target is aiming at and yields no triggers — the
  reference project measured exactly that: zero triggers in a 60 s run.

## 5. Fixed-point discipline: what actually breaks

**Coefficient quantization moves poles.** A biquad's pole location is a nonlinear function of its
denominator coefficients. The narrower the band and the lower the center frequency relative to the
sample rate, the closer the poles sit to the unit circle and the more a small coefficient error
displaces them. At 1 kHz, a 2-6 Hz AM band-pass is the dangerous stage, not the 16-24 Hz carrier
band-pass: the same number of fractional bits buys far less accuracy there, and the failure modes
are a shifted center frequency, a wrong Q, extra group delay, or outright instability.

Mitigations, in order:

- Always cascade second-order sections. Never implement a high-order filter as one direct-form
  structure.
- Decimate before the AM stage where the design allows it. Moving the AM band to a larger fraction
  of the working sample rate is the single most effective fix for low-frequency pole crowding.
- Give the denominator more fractional bits than the numerator if the word widths can differ.
- After quantizing, recompute pole radii and the realized magnitude response, and compare against
  the float design. Treat a pole radius that moves toward 1.0 as a stability finding, not a rounding
  detail.

**Structure choice.** The FPGA prototyping note proposes Direct Form II. **Do not use it.** DF-II
minimizes delay elements, but its all-pole internal node has peak gain `max|1/A(e^jw)|`, which for
a narrow resonant section far exceeds both the input and the output range — a well-known overflow
hazard in fixed point.

Use **Direct Form I**. Its states are plain input and output samples at signal word width, the
whole section accumulates in one wide accumulator with guard bits, and rounding happens once at
the output. This is why fixed-point DSP libraries use it — CMSIS-DSP, for example, provides
`arm_biquad_cascade_df1_q15`/`_q31` for fixed point.

Direct Form II **transposed** is the usual *floating-point* structure, not the fixed-point one. Its
state registers hold accumulated partial sums (`d1 = b1*x - a1*y + d2`), so in fixed point they
must be carried at accumulator width or truncation noise is injected straight back into the
recursion — which costs the storage DF2T was chosen to save.

**Overflow policy.** Require saturating arithmetic, not wraparound. A wrap inside an IIR feedback
path can sustain itself as an overflow oscillation that looks like signal. Allocate guard bits on
accumulators, scale each section explicitly, and order the cascade so intermediate magnitudes stay
bounded.

**Low-level artifacts.** In a near-DC AM path, quantization can produce granular limit cycles that
the phase detector will happily convert into triggers. Check the output with a zero input and with
a small DC input.

**Acceptance gate.** Before any phase number from the fixed-point design is believed:

1. Run the float reference and the fixed-point model on the identical input record.
2. Report max absolute output difference and the difference in the trigger-phase distribution
   (mean and SD), not just a plot.
3. Compare trigger sample indices one by one, not trigger counts. Equal counts with shifted indices
   is a failure.

## 6. The quadrature caveat

The FPGA prototyping note proposes feeding a signal and its first derivative into CORDIC as the `(I, Q)` pair.
This is workable but it is **not** the Hilbert transform, and the difference matters differently
for magnitude than for phase.

For `x(t) = A cos(w t)`:

```text
xdot(t) = -A w sin(w t)

sqrt(x^2 + xdot^2) = A * sqrt(cos^2(wt) + w^2 sin^2(wt))     -- equals A only if w = 1
sqrt(x^2 + (xdot/w)^2) = A                                    -- correct after normalizing by w
```

Three consequences:

- **Magnitude is wrong without normalization.** The derivative advances phase by +90 deg but also
  scales by the instantaneous angular frequency `w`. `sqrt(x^2 + xdot^2)` is not the Hilbert
  envelope. Divide the derivative by the nominal center angular frequency `w0 = 2*pi*f0`.
- **The sign is inverted.** With `Q = +xdot/w` the pair is `A*cos - j*A*sin`, i.e. the conjugate of
  the analytic signal, so CORDIC returns the negated phase. Use `Q = -xdot/w0`, or negate the CORDIC
  angle output. Verify that the reported phase advances with time on a known input; this is not in
  the note and is easy to miss because a conjugated phase still looks periodic and still fires
  triggers.
- **Residual error is narrowband and bounded.** With `k = f/f0` the estimated magnitude ripples
  between `A*min(1,k)` and `A*max(1,k)` at twice the signal frequency, and the phase acquires a bias
  `arctan(k*tan(theta)) - theta` whose maximum is `arctan(sqrt(k)) - arctan(1/sqrt(k))`.

Worked examples from that formula (arithmetic, not measurement), for an AM stage nominally centered
at `f0 = 4 Hz`:

| True f_am | k | Max phase bias | Envelope error |
| --- | --- | --- | --- |
| 3.3 Hz (high working-memory capacity, section 1) | 0.83 | about -5.5 deg | up to -18 percent |
| 4.0 Hz | 1.00 | 0 deg | 0 |
| 5.2 Hz (low working-memory capacity, section 1) | 1.30 | about +7.5 deg | up to +30 percent |

The magnitude error is worse than the phase error, but **neither is a constant**. The phase bias
`arctan(k*tan(theta)) - theta` is odd in `theta` with period `pi`: it is zero at 0 and 90 deg,
peaks at `arctan(sqrt(k)) - arctan(1/sqrt(k))`, averages to zero over a cycle, and ripples at
twice the signal frequency — the same `2f` ripple the magnitude error has. It is therefore **not
removable by a phase-offset register**, which adds the same value to every estimate. It lands
wholly in the SD of phase error, the term nothing downstream can buy back. At `k = 1.30` that is a
+/-7.5 deg swing, about 15 deg peak to peak, against the streaming simulator's whole 10.51 deg
phase-error SD. The magnitude error is a first-order amplitude error of the same `2f` period that
additionally biases the amplitude gate and any AM-power-driven intensity scaling.

The bound above is derived for a constant-amplitude sinusoid. For an amplitude-modulated `M(t)`
the `a'(t)*cos(phi)` term in the derivative adds error the formula does not cover, so measure
rather than assume.

Prescription:

- Normalize the derivative by the nominal center frequency of the preceding band-pass, implemented
  as a constant multiply or shift.
- Place the differentiator **after** the band-pass. A differentiator amplifies high-frequency noise,
  and a first-difference approximation's gain departs from `w` as frequency rises.
- Budget the residual as a contribution to the **phase-error SD**, not as a calibrated offset. It
  is not a constant and the phase-offset register cannot touch it. Bound it by keeping `|k - 1|`
  small — retune `f0` whenever the band moves — and measure the resulting SD against a true
  Hilbert reference.
- Validate the pair against a true Hilbert or all-pass reference on the same input. Report envelope
  error and phase bias separately.
- Do not use derivative-pair magnitude for a quantitative amplitude decision until its ripple has
  been measured on the actual band.

**Alternative.** An all-pass IIR quadrature network or a Hilbert FIR gives a genuine 90 deg pair
with no `w` scaling and, for the FIR, flat group delay that is trivial to compensate. It costs more
multipliers and more delay. Choose it when the envelope amplitude must be quantitatively correct;
choose the derivative pair when only phase matters and resources are tight.

## 7. The phase-offset compensation register

**What it fixes.** A constant bias. In the streaming AM simulator the mean phase error was
-64.47 deg at `f_am = 4 Hz`. Store **the delay in seconds**, never the 64.5 deg, and convert to a
phase code at run time — the implementation rules below forbid a degrees-valued constant and this
worked example is not an exception to them. The FPGA prototyping note proposes a degrees-valued
register set to +64.5 deg; do not copy that part.

Before applying any offset, verify the sign empirically against a known input: the wrong sign
doubles the error rather than removing it, and the resulting run still looks orderly. Note also
that the note's -90 deg target is labeled "trough" but is the ascending zero crossing under the
`angle(hilbert(.))` convention the algorithm uses — see
[realtime-am-reference.md](realtime-am-reference.md) section 3. Recentering on the wrong feature is
not fixed by getting the offset right.

**What it cannot fix.**

- **Jitter.** A constant added to every estimate leaves the SD unchanged. The simulator's 10.51 deg
  SD is untouched by any offset value.
- **Non-constant bias.** Amplitude-dependent detection, artifact-driven phase distortion, and
  filter transients after a state reset are not constants and will not cancel.
- **A different frequency.** This is the trap.

**Frequency dependence.** Group delay is a time, not an angle. A fixed delay `tau` seconds maps to

```text
offset_deg = 360 * tau * f_am
```

Worked table using the note's ~45 ms delay figure (arithmetic only, not a measurement):

| f_am | Offset needed for tau = 45 ms |
| --- | --- |
| 3 Hz | 48.6 deg |
| 4 Hz | 64.8 deg |
| 5 Hz | 81.0 deg |
| 6 Hz | 97.2 deg |

**This table is arithmetic, and the 4 Hz row proves nothing.** The note never measured 45 ms — it
back-computed the figure from the -64.47 deg error (`64.47 / (360 * 4 Hz)` = 44.8 ms), so feeding
45 ms through the same conversion returns 64.8 deg as an identity, not as a confirmation of the
delay-in-seconds model. The model is right on physical grounds — group delay is a time — not
because of this row.

The sign does not close either. With the error scored as (ground-truth phase at trigger) - (target),
a causal delay `tau` makes the trigger fire late and the error **positive**, `+360*tau*f_am`. The
reported error is -64.47 deg, consistent either with the opposite error convention or with ~205 ms
of lag, not with 45 ms. **Do not load a compensation register from this number.** Measure `tau`
directly instead: inject a known modulator, compare the estimator's zero crossings against the
ground truth's, read `tau` in seconds off the cross-correlation lag, convert with `360*tau*f_am`,
and confirm the sign empirically before applying it.

Implementation rules:

- **Store the delay in seconds or samples. Never store a constant in degrees.** Convert to a phase
  code at the current `f_am` each time the comparator runs, e.g. for a 16-bit phase word,
  `offset_code = round(tau_s * f_am * 65536)`.
- **Recompute the offset whenever adaptive tracking moves the AM center frequency.** Filter-bank
  centers must not be hard-coded: individual dominant AM frequency differs and drifts within a
  task (figures and their status in section 1), so an online dominant-frequency estimator or a
  Kalman filter adapting the IIR coefficients is required. A fixed offset in degrees is silently
  wrong for every subject except the one it was measured on.
- **Update the coefficients and the offset atomically.** A window in which the filter has moved but
  the offset has not is a window of systematically wrong triggers.
- **Re-measure rather than extrapolate for large moves.** Group delay is only approximately flat
  across a band, so `tau` itself is a function of the tuning. The linear conversion above is exact
  only near the frequency where `tau` was measured.
- **Re-measure after any datapath change.** Changing biquad order, structure, word width, or the
  quadrature method changes `tau`.

## 8. Verification ladder

Climb in order. Do not skip a rung because the previous one looked good.

| Rung | What runs | Acceptance |
| --- | --- | --- |
| 0. Float reference | Python streaming controller on synthetic signals with known AM phase | Trigger phase distribution matches the intended target within a stated tolerance; ground-truth checks pass |
| 1. Fixed-point model | Same algorithm in Qm.n, same input record as rung 0 | Bounded, reported output difference against float; identical trigger sample indices, not merely identical counts; pole radii and headroom documented |
| 2. RTL/HDL simulation | The HDL against recorded EEG and against the rung-0 synthetic input | Trigger indices match the fixed-point model; no overflow or saturation events on the recorded data; behavior at reset and after a gap defined |
| 3. Hardware-in-the-loop | Signal generator producing a known AM signal with a sync output, into the real ADC, trigger measured on the GPIO | End-to-end latency and jitter measured from generator sync to GPIO edge, including ADC and output stage; phase error distribution measured against the generator's known phase |
| 4. Artifact conditions | Rung 3 repeated with the stimulator energized into a **resistive head phantom or dummy load only — never a person, never a live electrode montage** — using a certified stimulator behind an independent hardware current limiter and an emergency stop | Phase error distribution under stimulation compared against the unstimulated case; artifact suppression validated where it sits in the datapath, not downstream; **residual artifact quantified, not merely shown to be reduced** |
| 5. Human | Not a verification step | Requires certified equipment, an independent hardware current limiter, an emergency stop, ethics approval, and qualified supervision. A same-process software interlock is not a safety system |

**Status for this project: none of rungs 1 through 5 has been performed.** No FPGA design has been
implemented, synthesized, timed, or measured. Any resource utilization, clock rate, or hardware
latency figure appearing in a report about this port would be fabricated. Say "not implemented"
rather than estimating.
