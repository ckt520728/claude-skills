# Real-time AM phase-lock reference prototype

## Contents

1. Purpose and scope
2. Test signal model
3. Algorithm
4. Parameters
5. Reconciling this with offline HHSA
6. Required validation output
7. Acceptance thresholds
8. What this prototype does not establish

Numbers in sections 3, 4, and 6 come from the streaming AM simulator described in **the FPGA
prototyping note** (`FPGA 即時閉迴路神經調控演算法原型設計.md`) — the one name this skill uses for
that document everywhere. They are **not** the reference project's numbers. The reference
project's own measurements (63 ms detection lag, 67 deg at 3 Hz, ripple counts, LSL latency)
belong to a different implementation on a different plant. The authoritative side-by-side list of
both systems' numbers is [fpga-porting.md](fpga-porting.md) section 1; see also
[pitfalls.md](pitfalls.md). Never average, merge, or interchange the two sets.

## 1. Purpose and scope

Build this before the two-rate controller. Its only job is to prove the timing story.

- Single channel, single carrier band, single AM band.
- Strictly causal: a fixed-length sliding buffer, no whole-recording operation, no forward
  prediction, no acausal filtering.
- One output: a trigger emitted when the amplitude-envelope phase reaches a chosen target.
- No intensity control, no supervisor, no HHSA, no montage, no artifact handling.
- Physical stimulation stays disabled. The trigger goes to a marker stream, a log, or a
  simulated backend. Nothing in this prototype justifies energizing an electrode.

Treat the finished script as a **golden reference**: the numerical behavior a later port
(fixed-point DSP, FPGA, or a different language) must reproduce sample for sample before that
port is trusted. It is a reference, not a controller.

FPGA translation of this reference is design guidance only. No such port has been built,
synthesized, timed, or measured here. Do not state resource counts, clock rates, or latency for
a design that has not been run.

## 2. Test signal model

Use the multiplicative construction verbatim from the FPGA prototyping note:

```text
x(t) = 0.5 * sin(2*pi*f_am*t)
     + (1.0 + 0.8 * sin(2*pi*f_am*t)) * cos(2*pi*f_c*t)
     + eta(t)

f_am = 4 Hz (theta modulator)
f_c  = 20 Hz (beta carrier)
eta  = Gaussian white noise
duration 10 s, fs = 1000 Hz
```

Read the three terms separately:

| Term | Role |
| --- | --- |
| `0.5*sin(2*pi*f_am*t)` | a visible slow oscillation in the raw trace, so the plot is interpretable |
| `(1.0 + 0.8*sin(2*pi*f_am*t))` | the envelope to be recovered; this is the ground truth |
| `cos(2*pi*f_c*t)` | the carrier the envelope rides on |

**Multiplicative is load-bearing.** An additive test signal (`sin(theta) + cos(beta)`) has no
envelope to recover: the beta component's amplitude is constant, so a correct AM demodulator
returns a flat envelope and a meaningless phase, while a broken one returns filter ringing that
looks like a modulator. An additive signal therefore cannot distinguish a working demodulator
from a broken one and must not be used to validate this path. The known modulator phase from the
`(1.0 + 0.8*sin(...))` term is the only reason phase error is computable at all.

Keep the noise term. A noiseless run hides ripple sensitivity and understates the phase-error SD.

## 3. Algorithm

Per incoming sample, at fs = 1000 Hz:

1. Push the sample into a ring buffer of **500 ms = 500 samples**. Do nothing until the buffer
   has filled once.
2. Band-pass the buffer contents in the **carrier** band (beta, 16-24 Hz) to isolate `C(t)`.
3. Hilbert-transform `C(t)` to the analytic signal `z_c(t)`; take `AM(t) = |z_c(t)|`. This is the
   recovered envelope, the quantity the whole loop is about.
4. Band-pass **`AM(t)`** in the **modulator** band (theta, 2-6 Hz) to get `M(t)`. This removes the
   DC level of the envelope and any residual broadband and near-`2*f_c` content the magnitude
   carries — small for the analytic magnitude of a narrowband signal, which is why Hilbert
   magnitude is preferred over rectify-and-low-pass, but first-order if the envelope is ever
   computed by rectification instead (the reference project measured 253 spurious peaks against
   89 real ones with a 2nd-order envelope low-pass).
5. Hilbert-transform `M(t)` and take the instantaneous phase of the **last buffer sample only**:
   `theta_am = angle(z_m[-1])`.
6. Compute the wrapped difference between `theta_am` and the target phase (**-90 deg**). Read the
   phase-convention note below before treating that number as a trough.
7. If `|difference| < 15 deg` **and** at least **150 ms** has elapsed since the previous trigger,
   emit the trigger and restart the refractory timer.
8. Log, for every trigger: sample index, wall time, estimated phase, and the ground-truth
   modulator phase at that sample. Without the last field there is no error distribution.

### Phase convention — pin this before comparing any number

Step 5 defines the phase as `angle(hilbert(M))`. Under that convention, for `M = A*cos(phi)`:

| Phase | Feature of the modulator |
| --- | --- |
| 0 deg | envelope **peak** |
| +/-180 deg | envelope **trough** |
| -90 deg | **ascending** (rising) zero crossing, maximum positive slope |
| +90 deg | descending zero crossing |

The FPGA prototyping note labels its -90 deg target "波谷" (trough). That label uses a
sine-referenced convention and is off by a quarter cycle from the `angle(hilbert(.))` convention
the algorithm itself mandates. The reference project uses the same convention as the table above:
`closedloop/phase.py` maps `peak -> 0`, `rising -> -pi/2`, `trough -> pi`, `falling -> +pi/2`, and
`closedloop/plant.py` documents "0 = envelope peak, pi = envelope trough".

Consequences:

- Keep **-90 deg** as the target if you are reproducing the note's run — every one of its numbers
  is scored against it — but call it the **ascending zero crossing**, not the trough.
- If the excitability minimum is what you actually want, the target is **+/-180 deg** and the
  note's error statistics do not transfer.
- State the convention next to any target or offset you publish. A quarter-cycle mislabel produces
  a run that looks orderly and stimulates the wrong point.

Two further details are load-bearing:

- **Step 4 filters the envelope, not the raw signal.** Band-passing `x(t)` in theta returns the
  additive slow term `0.5*sin(2*pi*f_am*t)`, which is present so the raw trace has a visible slow
  oscillation. On this synthetic signal that term is *in phase* with the modulator — both are
  `sin(2*pi*f_am*t)` — and that is exactly what makes it a trap: a raw-trace theta band-pass will
  validate successfully here, with less group delay than the correct path, and then fail on real
  EEG, where no additive in-phase copy of the modulator exists. Step 4 must filter `AM(t)` because
  the envelope is the only quantity that generalizes.
- **Step 5 uses only the last sample.** Every other sample in the buffer has both past and future
  neighbors inside the window, so its phase estimate is effectively non-causal and far more
  accurate. Reporting phase from the buffer center, or from an averaged buffer, produces numbers a
  real-time system can never reproduce. The last sample's estimate is the only one that exists
  online, and its degradation relative to the buffer interior is precisely the cost being
  measured.

## 4. Parameters

| Parameter | Source value | Trade-off |
| --- | --- | --- |
| Sample rate | 1000 Hz | Sets the timing quantum; 1 ms is far below a theta cycle, so it is not the limiting term |
| Buffer length | 500 ms (500 samples) | Longer stabilizes the low-frequency filters and Hilbert estimate but raises per-sample cost and edge-transient duration. 500 ms spans one modulator cycle at the 2 Hz bottom of the band and two at 4 Hz. A useful heuristic (not a measured constraint, and not stated in the note) is >= 2 cycles at the lowest modulator frequency in use, i.e. `2/f_am_min` = 1000 ms for a 2 Hz floor; the note's 500 ms buffer and its 2-6 Hz modulator band are therefore only mutually consistent above ~4 Hz. State which of the two you are relaxing |
| Carrier band | 16-24 Hz (beta) | Narrower rejects more neighboring rhythm but adds group delay and can miss a drifting individual beta frequency. **Binding constraint the trade-off usually omits:** the modulation lives in sidebands at `f_c +/- f_am`, so the carrier band must be at least `+/- f_am_max` wide about `f_c`. 16-24 Hz around 20 Hz supports modulation only to 4 Hz, and at 4 Hz the sidebands sit on the -3 dB edges, so the recovered modulation depth is already attenuated before anything else happens (arithmetic: 0.8 * 0.707 ~ 0.57). It cannot support the 2-6 Hz modulator band below, which needs at least 14-26 Hz and realistically wider so the sidebands clear the roll-off. Narrowing past this point attenuates the envelope itself, not just neighboring rhythms — either widen the carrier band or narrow the modulator band to <= 4 Hz so the two rows agree |
| Modulator band | 2-6 Hz (theta) | Narrower cleans `M(t)` but delays it; the delay lands directly on the quantity being phase-locked. See the carrier-band row: 6 Hz modulation does not survive a 16-24 Hz carrier band |
| Target phase | -90 deg | Under `angle(hilbert(M))` this is the **ascending zero crossing**, not the trough — see the phase-convention note in section 3. The trough is +/-180 deg. Peak, trough, ascending, and descending targets are equally implementable and are the basis of the phase-reversal control condition |
| Phase tolerance | +/-15 deg | Wider fires more often and admits worse events; narrower can silently fire never if the estimator's jitter exceeds the window |
| Refractory | 150 ms | Must exceed the shortest modulator period in the band to prevent double-fires, and must not exceed it either or cycles get skipped. Both bounds are the period at the **top** of the band (167 ms at 6 Hz), so no single constant serves a 2-6 Hz band; 150 ms sits below that bound and admits double-fires at high `f_am`. Derive the refractory from the supervisor's current `f_am` rather than freezing a constant |
| Phase compensation | not applied in the note's run | Adding a fixed offset before comparison removes a constant group delay; it cannot remove jitter |

Do not hard-code the two bands in anything beyond this prototype. Dominant AM frequency differs
between individuals and drifts within a task (figures and attribution in
[fpga-porting.md](fpga-porting.md) section 1). In the full system the bands come
from the slow supervisor; online dominant-frequency estimation or a Kalman-adapted filter
coefficient set is the stated design direction, and neither is implemented here.

## 5. Reconciling this with offline HHSA

This prototype uses band-pass plus Hilbert magnitude as the envelope. The skill's offline HHSA
invariants **forbid** exactly that substitution for layer 2, which requires the cubic-spline
envelope through the extrema of `abs(IMF)`. That is not an oversight and not a relaxation of the
invariant. It is a bounded exception with a stated price.

- The fast path cannot run EMD. Sifting is iterative, data-dependent in cost, and whole-window;
  it has no fixed-latency causal form.
- Band-pass plus Hilbert magnitude is the causal stand-in: fixed cost, fixed state, known group
  delay, portable to fixed point.
- The price is two distinct things, and only the second is the classic spurious-PAC mechanism.
  (a) The narrow carrier band-pass discards the carrier's own harmonics — at `f_c = 20 Hz` they
  sit at 40, 60, 80 Hz, far outside a 16-24 Hz passband — so it sinusoidalizes exactly the
  waveform shape HHSA exists to preserve. On the filtered output, Hilbert magnitude and spline
  envelope then agree closely and the substitution looks free; the shape information was already
  removed upstream. (b) Harmonics of a non-sinusoidal **low-frequency** component land inside the
  carrier passband, and their amplitude is phase-locked to the slow cycle, which modulation-index
  and filter-based methods report as cross-frequency coupling. EMD keeps such harmonics with
  their fundamental in one IMF and the spline envelope of that IMF stays flat; a fixed passband
  cannot do this.

Consequences, all mandatory:

- **Band selection and AM target must come from the slow HHSA supervisor**, not from the fast
  path's own spectrum. The supervisor is the component entitled to say which carrier and which
  AM band are real. The fast path only tracks phase inside a band it was told to track.
- **The fast path must never be used to make a scientific claim about PAC.** Its envelope is a
  control signal, not evidence. Any PAC statement is an offline HHSA result.
- Validate the substitution explicitly: run the sawtooth-carrier ground-truth signal through both
  paths and record how far they diverge. The reference project measured, on **unfiltered** IMFs —
  which is what offline layer 2 actually consumes — agreement to ~0.01% on sinusoidal carriers
  and ~5% median divergence (4.5x at the extremes) on sawtooth-like ones (its `README.md`, "Design
  decisions that are load-bearing"). Those figures do **not** describe band-passed fast-path
  output, where the harmonics are already gone. Treat them as the direction of the effect and
  measure your own on your own path.

See [architecture-and-validation.md](architecture-and-validation.md) sections 1-3 for where the
supervisor sits and what it is required to hand down.

## 6. Required validation output

Four panels, per the note's verification figure. All four, every run; each catches a failure the
others hide.

| Panel | Shows | Catches |
| --- | --- | --- |
| Raw signal with reconstructed AM envelope overlaid, time domain | whether the envelope tracks the modulator at all | demodulator wired to the wrong band, locking to the additive slow component, envelope collapsed to a constant |
| Estimated vs true instantaneous phase trajectory | the estimate's fidelity over time, not just at triggers | cycle slips, wrapping bugs, drift, and the visible constant offset of a group delay |
| Polar histogram of trigger phase | concentration of the actual firing distribution | multimodal firing, near-uniform firing that mean statistics would hide |
| Linear histogram of phase error | shape, center, and spread of the error | asymmetric tails and outliers that a single SD number smooths away |

### Reporting rule

Always report the **mean** phase error and the **SD** of phase error separately, and label them
explicitly:

- **mean = accuracy.** A systematic offset. Caused by group delay through the two band-passes and
  the envelope extraction. It is removable, by subtracting a measured offset before the phase
  comparison.
- **SD = precision.** Cycle-to-cycle variability. It is not removable by any offset.

Two failure modes that a single averaged number confuses:

- Tight SD, large mean: a **working detector with an uncorrected delay**. Measure the offset,
  compensate, re-run.
- Centered mean, wide SD: **unusable**. The detector is guessing and happens to guess symmetrically.
  No compensation fixes this. Change the filters, the buffer length, or the target.

### Worked example (streaming AM simulator, attributed)

From the streaming AM simulator in the FPGA prototyping note, on the 10 s synthetic signal of
section 2. Attribution and the side-by-side comparison with the reference project's own numbers
live in [fpga-porting.md](fpga-porting.md) section 1; this table is repeated here only because
you are meant to reproduce it.

| Quantity | Value |
| --- | --- |
| Triggers in 10 s | 39 |
| Mean trigger phase | -154.47 deg |
| Mean phase error (vs -90 deg target) | -64.47 deg |
| SD of phase error | 10.51 deg |

Read it this way: **the -64.47 deg mean is group delay, not detector quality.** The note
attributes it to accumulated filter and envelope-smoothing delay. **The 10.51 deg SD is the real
quality figure** — it says the detector finds the same point on the modulator cycle every time,
which is the property that cannot be bought back later.

Two cautions about the "45 ms" figure that circulates with this result:

- **It was not measured.** The note back-computed it from the phase error itself
  (`64.47 / (360 * 4 Hz)` = 44.8 ms). Converting 45 ms back into degrees at 4 Hz therefore
  reproduces 64.5 deg as an identity, not as a confirmation of anything.
- **The sign does not close.** With the error scored as (ground-truth phase at trigger) - (target),
  a causal delay `tau` makes the trigger fire late, so the error should be **positive**
  `360*tau*f_am`. The reported error is negative. That is consistent with the opposite error
  convention, or with ~205 ms of lag, but not with a 45 ms causal delay under the stated
  convention.

Measure your own `tau` directly instead of inheriting one: inject a known modulator, compare the
estimator's zero crossings against the ground truth's, and read `tau` in seconds off the
cross-correlation lag. Then confirm the sign empirically before applying it. A compensation
register with the wrong sign doubles the error instead of removing it, and the resulting run still
looks orderly.

## 7. Acceptance thresholds

Apply these to your own run. They are rules, not this project's results, and none of them is
satisfied by a plausible-looking plot.

1. **Trigger count is near the expected count.** Expected is roughly `duration * f_am`, reduced by
   the refractory. Order-of-magnitude over-count means spurious detections, typically ripple.
   Zero or near-zero means the tolerance window is narrower than the estimator's jitter, or a gate
   is inverted.
2. **Trigger phase is unimodal** on the polar histogram. A second lobe means the detector is
   locking to a harmonic, to the additive slow component of the raw trace, or to both a peak and a trough.
3. **SD of phase error is small and stable across reruns with different noise seeds.** Fix the
   number you will accept before you look at the output. An SD that changes materially with the
   seed means the result was noise-dependent, not a property of the detector.
4. **Mean phase error is stable across reruns.** A drifting mean is not a fixed group delay and
   cannot be compensated with a constant offset.
5. **Compensation demonstrably works.** Apply the measured offset, re-run, and show the mean moves
   to near zero **while the SD is unchanged**. If the SD also changes, the offset is interacting
   with the detector and the model of "constant delay" is wrong.
6. **Behavior degrades gracefully with noise.** Increase the noise term; the SD should widen
   smoothly. A cliff means the detector is threshold-dependent in a way not yet characterized.
7. **The last-sample constraint is honored.** Re-run with the phase read from the buffer center.
   If the error statistics barely change, the causal path is not actually causal somewhere.
8. **The result reproduces bit-for-bit from a fixed seed.** A golden reference that does not
   reproduce cannot be used to validate a port.

## 8. What this prototype does not establish

- **No artifact.** No tACS or TMS artifact is present. The FPGA prototyping note reports a 2 mA
  stimulation artifact exceeding the EEG by more than 10,000x (see [fpga-porting.md](fpga-porting.md)
  section 1 for what that figure is and is not); at any comparable ratio the artifact, not the
  brain, sets the estimated phase. Handling it needs hardware measures (actively driven ground,
  common-mode rejection) plus an algorithmic stage — adaptive noise canceling or a real-time
  spatial projector such as a Laplacian montage template — placed **before** the Hilbert/CORDIC
  demodulator. Placement is what you control; efficacy is not. Online tACS artifact removal is an
  open problem: amplifier saturation destroys signal no downstream stage can restore, and the
  artifact is non-stationary, so a residual survives that can itself look like a phase-locked
  envelope. None of that is in this prototype, and none of it has been validated here.
- **No real EEG.** The test signal is stationary in frequency and amplitude statistics. Real EEG
  is non-stationary, has phase resets, bursts, drifting individual frequencies, and epochs where
  no modulator exists at all. Performance on this signal predicts none of that.
- **No transport lag.** Phase error is measured against samples already in the buffer. Acquisition
  transport, chunking, and device latency are additional, are not visible to this measurement, and
  must be measured separately and added.
- **No stimulator.** The trigger goes nowhere physical. There is no charge accounting, no dose, no
  interlock, no blanking, and therefore no closed loop — the signal never contains the consequence
  of the trigger.
- **Synthetic ground truth only.** The phase error is computable only because the modulator was
  constructed. On real data there is no ground truth to score against, and every number in section
  6 becomes unmeasurable in that form.
- **No FPGA result.** The hardware architecture in the FPGA prototyping note (shift-register delay
  line, cascaded Direct Form II biquads on DSP slices, dual CORDIC in vector mode for magnitude
  then arctan with Q15 phase output, phase-offset compensation register) is that note's *proposal*.
  [fpga-porting.md](fpga-porting.md) section 5 supersedes the Direct Form II choice, and section 7
  supersedes the degrees-valued compensation register. Nothing here states that any of it has been
  implemented or that it meets any timing figure.
