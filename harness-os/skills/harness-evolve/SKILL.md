---
name: harness-evolve
description: Repair phase of Harness OS — turn mined failure clusters into small bounded edits, each shipping a falsifiable prediction, then promote or roll back based on measured held-in improvement and held-out non-regression rather than on how good the reasoning sounded. Includes a test-time harness-learning tournament (Zhang et al., CMU 2026) — G candidate SEARCH/REPLACE edits scored on a separate score split, incumbent retained unless strictly beaten, iterated over rounds, then one blind run on a sealed eval split. Use after [[harness-mine]] has named an addressable mechanism under [[harness-os]].
---

# Harness Evolve

Every self-improving loop fails the same two ways: it makes sweeping changes
nobody can attribute, and it convinces itself the change worked. This phase is
built entirely to prevent both.

There are two ways to run it. Both share steps 1, 3 and 7.

| Mode | When | Selection |
|---|---|---|
| **Predict-and-gate** (§1–7) | One clear mechanism, one obvious fix | Prediction lands + `gate` |
| **Tournament** (§T) | Several plausible fixes, a cheap scorer, or repeated refuted rounds | `score` each candidate on Q_score, `select` |

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

Prefer applying through the kernel rather than by hand — it is atomic, refuses
to touch contracts, verifiers or `.harness/`, and refuses a `.py` edit that does
not parse (format in §T.2):

```bash
$K patch --file edits/e1.patch --dry-run   # validate only
$K patch --file edits/e1.patch
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

## T. Tournament mode — test-time harness learning

From *Harness Learning Enables Generalizable Test-Time Adaptation* (Zhang et
al., CMU 2026): a frozen model improves at test time by revising its **harness
program** from execution feedback. You play the proposer; the kernel plays the
outer loop's bookkeeping. What the paper adds over predict-and-gate:

1. **Three disjoint sets.** Feedback (`held_in`, Q_fb) is what you read.
   Score (`held_out`, Q_score) picks among candidates — you see only its
   aggregate J. Eval (`sealed`, Q_eval) is never touched until the end.
   One set doing two jobs is how selection bias gets reported as improvement.
2. **Structured edits.** SEARCH/REPLACE blocks, validated before anything is
   written. A proposal that does not apply cleanly is a failed proposal,
   counted as such (`patch_validity`).
3. **Retain the incumbent unless strictly beaten.** Ties keep the old harness.
4. **Iterate.** Several rounds of feedback → revise beat one big batch of
   independent samples (paper: a 10-round run beat the best of 80 one-shot
   proposals on MuSiQue). Keep G small (2–4) and run rounds instead.

### T.1 Round t

```bash
$K assertall --round t                 # refresh Q_fb evidence
$K report --round t                    # YOUR input: read this, not the raw trace
$K snapshot --round t --paths "tools,middleware"   # the incumbent h_{t-1}
$K score --round t --label incumbent   # J(h_{t-1}; Q_score) — must come first

$K patch --file edits/t_c1.patch --round t --label c1   # restores incumbent, applies c1
$K score --round t --label c1
$K patch --file edits/t_c2.patch --round t --label c2   # restores incumbent, applies c2
$K score --round t --label c2

$K select --round t                    # PROMOTE best if J > incumbent J, else RETAIN
$K guard check
```

`report` gives the task spec, invariants, Q_fb failures with check messages,
mined clusters, score-split aggregates only, every prior candidate with its
outcome, and the patch validity rate. **Do not re-propose a rejected
candidate's mechanism** — it is listed there so you can see it.

`patch --label` always restores the incumbent before applying, so candidates
never stack; it refuses any file outside the round's snapshot paths, because
`select` could not roll that back.

`score` computes J as the mean per-contract check-pass fraction on Q_score —
dense, so a near-miss ranks above a miss — plus a validity term
v = 0.05·parses + 0.10·runnable + 0.15·ρ_run (the paper's weights). v only
breaks ties *between candidates*; it never promotes over the incumbent, because
a runnable-but-wrong harness must not beat a correct one.

The predict-and-gate checks still apply: write a `manifest` per candidate
(`--edit-id` = its label) before you score it, and after a PROMOTE run
`assertall --round t+1`, `attribute --round t`, `gate --round t`. Winning on
Q_score does not excuse a prediction that did not land.

### T.2 Edit format

```
Diagnosis: <failure from the report, by signature and size>
Mechanism: <evidence rewiring / interpreter loop / verification branch / ...>

FILE: tools/answer.py
<<<<<<< SEARCH
    return llm(f"Answer based on: {summaries}")
=======
    return llm(f"Context: {raw_passages}\nAnswer the query:")
>>>>>>> REPLACE
```

SEARCH must match **exactly once** (add context lines if ambiguous). Empty
SEARCH creates a new file. Several blocks and several files are allowed; all
apply or none do. Line endings are preserved. Prose before the first `FILE:` is
kept as the candidate's diagnosis and shown in later `report`s.

### T.3 Mechanism library

Edit shapes the paper's trained proposer converged on. Reach for these before
rewriting instructions — they are tools/middleware changes, which is where AHE
also found the gains.

| Mechanism | Failure it fixes | Shape |
|---|---|---|
| **Evidence rewiring** | Detail lost through summary-of-summary | Keep summaries for routing/query-building; pass the **raw** source passages to the final step |
| **Interpreter loop** | Verbal arithmetic / logic errors | Have the model emit code; execute it; feed the result back |
| **Verification branch** | Answer not grounded in retrieved evidence | If the draft is not found in the evidence, trigger one more retrieval using the draft as the query |
| **Validate-and-retry** | Output fails a format/parse rule | Check the format, retry with the parser error as feedback, bounded retries |

In this pack: evidence rewiring maps to `literature-corpus` (per-PDF summaries
feeding a review), interpreter loop to `signal-analysis` (compute metrics, never
estimate them), verification branch to citation checks in any writing profile.

### T.4 Stopping and the final run

Stop the tournament on the same rules as above, plus: two consecutive RETAIN
rounds. `status` shows the adaptation curve.

Then, once:

```bash
$K final                                   # sealed contracts in the workspace
$K final --sealed-dir "D:/held_by_user"    # or contracts you never saw
```

`final` reports aggregates only and marks Q_eval **spent**. Every later
`patch`/`select` carries a warning, and a second `final` is flagged as not
blind. Report the first final score. `assert`/`assertall` refuse sealed
contracts outright.

`sealed` contracts inside the workspace are readable by you, so blindness there
is discipline plus a tripwire. For a genuinely blind number, have the user keep
the contracts outside the workspace and pass `--sealed-dir` at the end.

### T.5 What the paper did that this does not

- **No trained proposer.** The paper trains a 4B proposer with GRPO across task
  families; here the proposer is whatever model is running, untrained. What
  carries across runs is the playbook and the prior-candidate record, not
  weights. Expect the paper's untrained-baseline behaviour (more invalid
  proposals), which is why `patch_validity` is tracked.
- **Long chains do not compound reliably.** The paper's multistep RL did not
  clearly beat single-step; credit assignment across rounds is open. Judge each
  round on its own `select` and `gate`, not on a story about the trajectory.
- **Seed dependence.** Gains accumulated where the seed harness already had
  structure (a retrieval workflow); a trivial seed collapsed to one pattern.
  Start the tournament from a harness with real stages to rewire.
- **Verifiable objectives only.** Like everything else here.

## What this loop cannot do

It optimises against the verifier, faithfully and relentlessly. Where the
verifier is a real test, that is exactly what you want. Where the verifier is a
proxy — an LLM judge, a heuristic score, a structural check standing in for
quality — the loop will find the gap between proxy and goal, because that is
cheaper than doing the work.

So: never run this loop unsupervised against a subjective objective, and never
let the thing being graded write the grader. A human reads the result before
anything ships.

Where the objective *is* deterministic, harden the verifier so the loop cannot
fake it: use a `challenge:` check instead of a static one. The kernel issues a
fresh nonce each round, so the loop cannot converge on a hardcoded answer — it
has to actually produce the response to a challenge it has not seen. This does
not make an LLM-judge objective safe (nothing does); it removes the cheapest
gaming route on the objectives that *are* checkable. See [[harness-os]]
Anti-gaming for the mechanism and its limit.
