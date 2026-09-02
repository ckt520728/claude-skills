---
name: harness-evolve
description: Repair phase of Harness OS — turn mined failure clusters into small bounded edits, each shipping a falsifiable prediction, then promote or roll back based on measured held-in improvement and held-out non-regression rather than on how good the reasoning sounded. Use after [[harness-mine]] has named an addressable mechanism under [[harness-os]].
---

# Harness Evolve

Every self-improving loop fails the same two ways: it makes sweeping changes
nobody can attribute, and it convinces itself the change worked. This phase is
built entirely to prevent both.

## 1. Snapshot first

```bash
$K snapshot --round 1 --paths "tools,middleware,draft/proposal.md"
```

Nothing is edited until the current state is recoverable. Rollback is a
first-class move, not an emergency.

## 2. Bounded proposals

From the top clusters, write **one to three** candidate edits. Each must be:

- **grounded** — tied to a specific cluster, with its size quoted
- **single-mechanism** — one failure mechanism, not "general improvements"
- **single-component** — tools OR middleware OR memory OR skill, not several
- **minimal** — change only the surface needed; no rewriting the control flow
- **distinct** — genuinely different from the others, not the same idea reworded

If you cannot say which cluster an edit is for, it is not a proposal, it is a
preference. Drop it.

## 3. Manifest — the prediction is the point

```bash
$K manifest --round 1 --edit-id e1 --component middleware \
  --evidence "cluster empty_extract|direct|scanned_pdf_no_ocr (n=7 of 19)" \
  --root-cause "extractor assumes every PDF has a text layer" \
  --fix "detect <200 chars extracted, route to OCR, log the fallback" \
  --predict-fix "lit_summary_03,lit_summary_07,lit_report" \
  --predict-regress "throughput_budget"
```

`--predict-fix` names the contracts this edit should turn from FAIL to PASS.
`--predict-regress` names what it might plausibly break. Both are written
**before** the next evaluation.

Write predictions you could actually be wrong about. "It will improve things" is
not falsifiable and defeats the mechanism. If you cannot name a contract that
should flip, you do not yet understand the failure — go back to
[[harness-mine]].

## 4. Apply, then re-evaluate

```bash
# apply the edits
$K guard check                    # must be OK before you trust anything
$K assertall --round 2
```

## 5. Attribute — did the prediction land?

```bash
$K attribute --round 1
```

| Verdict | Meaning | Action |
|---|---|---|
| `confirmed` | Predicted fixes landed, no unpredicted regressions | Keep |
| `partial` | Fixes landed, but broke something unpredicted | Keep only if the gate passes; investigate the regression |
| `refuted` | Predicted fixes did not land | **Roll back** |

A refuted edit gets rolled back even when the round improved overall. An edit
that improves things for reasons you did not predict is a coincidence you do not
understand, and keeping it is how a harness accumulates cargo cult.

## 6. Gate — promote or reject

```bash
$K gate --round 1
```

Promotion requires **both**: held-in improved, held-out did not regress. Either
one alone is not enough. Held-in-only improvement is the signature of fitting the
specific failures you were shown.

If the gate warns that no held-out contracts exist, it is telling you the loop is
running blind. Add one before the next round.

```bash
$K rollback --round 1        # reject: restore the snapshot
```

Rejected proposals are logged, not deleted. A failed edit is evidence about the
problem, and the next round should not re-propose it.

## 7. Consolidate what was learned

```bash
$K playbook add --section mechanism \
  --text "Scanned PDFs in refs/ have no text layer — check extract length before summarising"
$K playbook prune
```

Add a delta. Never rewrite the playbook wholesale — repeated wholesale rewrites
compress detail away until only generic advice survives, which is exactly the
knowledge you needed.

## Stopping

Stop the loop when any of these is true:

- all contracts pass
- two consecutive rounds produce no `confirmed` edit
- mining shows the remaining failures are not addressable by the harness
- the guard has tripped (stop immediately, tell the user, do not "fix and
  continue" — the record is compromised)

Round count is not a measure of progress. Two rounds that fix real mechanisms
beat ten that shuffle wording.

## What this loop cannot do

It optimises against the verifier, faithfully and relentlessly. Where the
verifier is a real test, that is exactly what you want. Where the verifier is a
proxy — an LLM judge, a heuristic score, a structural check standing in for
quality — the loop will find the gap between proxy and goal, because that is
cheaper than doing the work.

So: never run this loop unsupervised against a subjective objective, and never
let the thing being graded write the grader. A human reads the result before
anything ships.
