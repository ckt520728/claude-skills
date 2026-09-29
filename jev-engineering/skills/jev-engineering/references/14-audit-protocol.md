# 14 — Audit protocol: finding the forks in an existing loop

Use when asked to audit, optimise, or cut the cost of an existing agent loop. The output is a table and one moved fork — not a refactor.

## Step 1 — Inventory every model call

Search the codebase for calls whose *return value* is consumed as a label, a boolean, or a small JSON object rather than as text shown to a user or written to a file.

Grep leads, in rough order of yield:

```
response_format   json_schema      strict=True       pydantic   BaseModel
enum              Literal[         parse(            .choices[0].message
is_safe           should_          can_              needs_     next_step
route             classify         triage            verdict    approve
"yes" / "no"      in ("allow"      == "block"
```

Then read the surrounding code — a structured-output call is not automatically a decision. The test is the **kept text** test: if nothing the model wrote survives past the branch, it is a decision.

Also inventory hooks, interceptors, and middleware — `PreToolUse`, `Stop`, executor wrappers, `before_tool` callbacks. These hold the highest-frequency forks and are easy to miss because they are not in the main loop body.

**Completion criterion:** every model call in the loop appears in the table below, classified. Not a sample — every one.

## Step 2 — Classify each call

| | Class | Meaning | Destination |
|---|---|---|---|
| **[G]** | Generation | produces prose, code, or a plan that is kept | stays on the LLM |
| **[D]** | Decision | produces a label, score, or boolean consumed by a branch | the decision layer |
| **[C]** | Hard rule | a count, a date, a file check, an exact string match, a cap | code |

Record for each: file and line, class, call frequency per task, approximate state size, and what the return value branches on.

The **[C]** column is the one people skip and it is often the cheapest win — a loop asking a model whether it has exceeded ten actions is paying for `if n > 10`.

## Step 3 — Rank by frequency, not by size

The fork worth moving first is the one the loop hits most often, which is usually the **tool gate** or the **worker dispatch**. A once-per-task planning call is expensive per call and irrelevant to the bill; a once-per-tool-call gate at 300 calls a night is the bill.

Compute `frequency × (state tokens + output tokens) × price` per fork and sort descending. Present the table.

## Step 4 — Move exactly one fork

Do not refactor the loop. For the top fork:

1. Write the state shape — evidence, not conclusions (`00-primitives.md`).
2. Write the questions — one judgment each, criteria as situations, an `other` exit, all in one call.
3. Put the hard rules in code **before** the call.
4. Write the gate with its four exits, thresholds as named constants.
5. Keep the old path callable as the escalation fallback.

**Completion criterion:** the new path runs in shadow mode — it labels, the old path still decides, both are logged. Nothing has switched over yet.

## Step 5 — Baseline before, measure after

Capture *before* switching anything:

- cost per completed task (all models, including retries)
- wall-clock per completed task
- retry / rework rate
- for the moved fork: agreement between the new and old path, by confidence band

Then tune `tau` on the shadow log (`10-threshold-tuning.md`), switch on the bands that matched, and re-measure for a week.

**Completion criterion:** cost and wall-clock per completed task improved, retry rate did not worsen, and the escalation path fired at least once and was right to. If escalation never fired, `tau` is too loose — fix that before claiming the win.

## Step 6 — Report, then take the next fork

The report is the before/after table on **their** numbers, plus the remaining forks ranked. One moved fork with a measured result is worth more than a whole-loop refactor with an estimate.

## What an audit should not do

- Move a **[G]** call. Planning, drafting, and explaining stay put; that is the subtraction principle, and a loop whose planner has been replaced by a classifier is broken, not optimised.
- Move everything at once. You lose the attribution and cannot tell which fork caused the regression.
- Report per-call savings. The number that matters is per completed task (`11-economics.md`).
- Replace a **[C]** rule with a **[D]** call to be consistent. Determinism is strictly better where it is available.
