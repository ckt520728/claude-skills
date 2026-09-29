# 09 — The confidence gate: deciding whether to answer at all

Every other playbook uses the gate. This one is about the gate itself: a classifier deciding whether the system is entitled to answer, and what happens when it is not.

## What confidence is and is not

**Is:** a statistic of the returned probability distribution. Concentrated on one outcome means confident; spread evenly means uncertain. Calibrated, meaning that across many calls higher confidence really does correspond to higher accuracy. Measured error-detection AUROC of 0.83-0.87 on in-envelope tasks.

**Is not:** an accuracy percentage. Not a certificate about the answer in your hand. `confidence = 0.92` does not mean "92% likely correct on this item" — it means this item sits in a population that is mostly correct. Calibration is a distribution property; it says nothing about any single answer.

The practical consequence: **you may use confidence to route, never to justify.** "The classifier was 0.94 confident" is not a defence for an action that turned out wrong. The defence is the policy the 0.94 fed into.

## Four exits, not two

A gate with only accept/reject throws away most of the value. Real gates have four:

```python
def gate(answer, *, tau_act, tau_ask, policy_flags):
    if any(policy_flags):            return "human"      # irreversible / money / public
    if answer.choice == "other":     return "human"      # the exit option is not a bucket
    if answer.confidence >= tau_act: return "act"
    if answer.confidence >= tau_ask: return "escalate"   # bigger model, or ask a question back
    return "abstain"                                     # decline, safe default, or null action
```

| Exit | When | Cost of getting it wrong |
|---|---|---|
| `act` | confident, and the action is cheap to undo | one wrong action |
| `escalate` | uncertain, and a better answer is purchasable | latency + frontier fee |
| `human` | policy, regardless of confidence | a person's minute |
| `abstain` | uncertain, and no better answer is available in budget | a non-answer |

`abstain` is the exit people leave out, and it is the one that makes a system honest. A pipeline with no abstain path converts every uncertainty into a confident-looking output.

## Policy beats confidence, always

```python
r = decide(
    state={"action": proposed_action, "context": context},
    questions={
        "reversible":     Noul(instructions="This action can be undone without cost."),
        "touches_money":  Noul(instructions="This action moves money or changes billing."),
        "external_reach": Noul(instructions="This action is visible outside the organisation."),
        "risk": Score(instructions="Blast radius if this is wrong.",
                      criteria=["Local and trivial", "Recoverable with effort", "Irreversible or public"]),
    },
)
```

Four questions, one call. The rule that follows from them: **anything irreversible, anything that costs money, and anything externally visible gets a human regardless of confidence.** Everything else escalates on uncertainty.

That is a policy in code, not a vibe in a prompt — and it is the sentence to reach for when someone asks why a confident classifier still asked permission.

## Choosing the two thresholds

`tau_act` and `tau_ask` come from the same sweep (`10-threshold-tuning.md`) but from different costs:

- `tau_act` is set by the cost of a **wrong action** against the cost of an escalation. Cheap-to-undo actions take a low bar; destructive ones take a high one. Do not use one global value across actions with different blast radii — that is the most common way a gate is mis-set.
- `tau_ask` is set by your **escalation budget**. At `tau = 0.90` expect roughly a third of in-envelope traffic to escalate; on harder traffic, more than half. If that bill is unaffordable, the honest move is to lower coverage via `abstain`, not to raise `tau_act` and pretend.

## Two numbers to watch after it ships

**Escalation rate.** If it is 0%, `tau` is too loose and you have built an unsupervised system without deciding to. If it is 80%, you are paying the cheap layer for nothing — either the task is outside the envelope or the state is too thin to separate the cases.

**Escalation precision** — of the items you escalated, how many did the expensive path actually change? That is the gate's real score. Escalating 34% and changing 3% of verdicts means the threshold is buying very little; the confidence signal may be uninformative on your workload, which is measurable: compute the AUROC of `q` against correctness on your labelled set. Near 0.5 means confidence carries no information *here* and no threshold will help.

## Where the signal is known to fail

On reference-free prose judging, AUROC was 0.518 — coin-flip — with high mean confidence and low agreement. On style-adversarial pairs it fell to 0.77, and a third of items scored in `[0.90, 0.95)` were wrong.

The pattern: **confidence routes well where the first stage is competent but uncertain, and badly where it is confidently misled.** So the gate must be validated on the kind of input it will actually meet, including the adversarial kind, and not only on ordinary traffic where it will always look good.

## Noul has no confidence

There is no `confidence` field on a Noul — the single probability carries both answer and certainty. To feed one into a shared gate, derive `certainty = abs(noul - 0.5) * 2` and tune that threshold separately. It is your statistic, on a different scale from a Choice confidence, and reusing a Choice threshold on it is a silent mis-set.
