# 10 — Threshold tuning and calibration protocol

Thresholds do not transfer. Not between tasks, not between fallback models, not from a paper to your workload. Everything else in this skill depends on doing this properly.

Demonstrated failure of transfer: a policy tuned for one fallback accepted 81% of pairs at `tau = 0.70` and lost 2.35 accuracy points — outside its own two-point tolerance — while three policies at `tau = 0.50` collapsed to no escalation at all. Same signal, same code, different fallback.

## The protocol

**1. Build a labelled set from your own traffic.** 150-300 items is enough to start; 100 is workable for a pilot. They must be *your* items — sampled from real traffic, including the awkward ones, not written to be representative. Ground truth is what a competent human says, or in triage what you actually did with the item.

**2. Split by source, not by row.** 40/60 into a **selection set** (used to fit the threshold) and a **test set** (touched once, at the end). Items that share a source — the same email thread, the same document, the same question asked twice — must land on the same side, or a near-duplicate leaks and your threshold looks better than it is.

**3. Run the cheap layer on everything and log the full distribution.** Label, `confidence`, and every entry of `probabilities`. Logging only the label makes the set un-re-tunable and you will need to re-tune.

**4. Sweep `tau` on the selection set only.**

```
for tau in [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99]:
    coverage = share of items with q >= tau
    accuracy = accuracy of the cascade (accept if q >= tau, else fallback's answer)
    fee      = cheap_fee_on_all + fallback_fee_on_escalated
```

**5. Pick by rule, not by eye.** The rule that has held up: *maximise coverage subject to cascade accuracy staying within 2 points of the fallback alone.* Write the rule down before you look at the numbers — choosing a threshold after seeing which one wins is how a post-hoc number gets shipped as a validated one.

**6. Re-check on the test set. Once.** If it does not hold, you do not get to re-tune on the test set; you go back to step 1 with more data. A threshold that only works on the set it was fitted to is not a threshold.

**7. Freeze and pin.** Record `tau`, the model version (`jev-1.13.0`, not `jev-latest`), the date, the label set's location, and the rule you used. Aliases move, and a threshold tuned against a model you can no longer identify is a threshold you have to re-derive.

`assets/examples/tune_threshold.py` implements the sweep, the split, and the selection rule.

## Baselines that keep you honest

A sweep with no baseline always looks good. Compute two:

- **Random escalation at the same budget.** At `tau = 0.90` a real gate scored 91.3% where escalating the same 34% at random reached 88.1%. The gap is what the confidence signal is actually worth — about half the attainable gain in that measurement.
- **The label-aware oracle** that escalates the errors first: 94.4% on the same items. That is the ceiling. If your gate sits closer to random than to the oracle, the problem is the signal on your workload, not the threshold.

Then compute **AUROC of `q` against correctness** on your labelled set. Around 0.85 the gate works. Near 0.5 confidence carries no information *for this task* and no threshold will help — stop tuning and fix the state or the criteria.

## Calibration as code, not as a phase

`jev/calibration.py` implements the protocol above as something that actually runs, for any
provider whose confidence you do not already trust — `local` and `llm` both qualify.

```python
from jev import calibration

cal = calibration.Calibrator.load("~/.jev/calibration.json")

conf = cal.calibrate("bucket", raw_confidence)      # observed accuracy for that band
cal.observe("bucket", raw_confidence, was_correct)  # one resolved escalation = one label
cal.save()
```

Histogram binning: group observations by the raw score, and report each bin's *observed*
accuracy as the confidence for that band. The reliability table is the audit artefact —

```
band      n     observed accuracy   state
0.2-0.3   34    0.41                warm
0.7-0.8   61    0.92                warm
0.9-1.0   7     1.00                cold   <- too few to claim anything
```

Three properties are load-bearing:

1. **Cold bins return `COLD_CONFIDENCE` (0.30)**, which sits below any sane gate. An untuned
   layer therefore escalates everything and automates nothing. It earns the right to act.
2. **Each question id calibrates separately.** A global mapping lets an easy question lend its
   accuracy to a hard one, and you cannot see it happening. Same reasoning as per-decision
   thresholds above, one level down.
3. **A band that is usually wrong never passes the gate**, however many observations it has.
   Warmth is permission to *report* an accuracy, not permission to act on it.

### The two numbers that say whether confidence means anything

```python
calibration.brier_score(pairs)                  # 0 is perfect, 0.25 is a coin flip
calibration.expected_calibration_error(pairs)   # gap between stated confidence and accuracy
```

ECE is the one to watch. Near 0 means a stated 0.8 really is right about 80% of the time. At
0.3 the number is decorative, and the gate built on it is not a gate.

Read it beside the reliability table rather than alone: ECE also penalises *under*-confidence,
and a layer reporting 0.30 while being right 100% of the time scores badly here and is
nonetheless perfectly safe, because it escalates.

### Shadow mode comes free with a calibrated local layer

When every escalation a human resolves is fed back through `cal.observe(...)`, the shadow
period stops being a phase you run and finish and becomes how the layer works: it starts cold,
escalates everything, and unlocks bands one at a time as they earn it. Rule 7 becomes
structural rather than a discipline somebody has to remember.

## Shadow mode, before anything switches

Rule 7, spelled out. Run a period — a week is the usual figure — where the cheap layer labels every item and the old path still decides. Log both. Then:

- Where they agreed, at what confidence? Those are your safe bands.
- Where they disagreed, who was right? Adjudicate by hand. This is the only part that costs real time and the only part that tells you anything.
- What would the gate have done? Replay the policy over the log before it controls anything.

Switch on the confidence bands that matched. Not on the average.

## Per-decision thresholds, not one global tau

One `tau` across actions with different blast radii is the most common mis-set. A read-only action and a destructive one in the same system should not share a bar:

```python
TAU = {
    "read_only":   0.70,
    "local_edit":  0.85,
    "destructive": 0.95,     # and still ask, never auto-deny-and-forget
    "external":    1.01,     # unreachable on purpose: always a human
}
```

`1.01` as "always escalate" keeps policy in the same table as the thresholds instead of in a special case somewhere else.

## Re-tune when any of these change

The model version. The criteria text — rewording an option changes the distribution, so a criteria edit invalidates the threshold. The state shape, including field names and truncation limits. The traffic mix, seasonally or after a launch. The fallback model.

Put a dated note beside the threshold constant recording which of these it was fitted against. It costs one line and saves the argument six months later.

## What re-tuning looks like when answers are wrong

In order, cheapest first:

1. **Rewrite the criteria text.** Most wrong answers are a criteria problem, not a model or threshold problem. "Collect evidence still needed for the goal" versus "research" is the entire difference.
2. **Enrich the state** — evidence, not conclusions. Split a field the model has to infer from.
3. **Split the question.** If it is really two judgments, rule 2 is being violated and no threshold fixes it.
4. **Then** move the threshold.
5. Only then conclude the task is outside the envelope.
