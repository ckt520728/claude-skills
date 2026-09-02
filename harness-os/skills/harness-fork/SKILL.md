---
name: harness-fork
description: Execution phase of Harness OS — run sub-tasks as real detached background processes with sandboxes and enforced timeouts, delegate model work to context-isolated sub-agents, keep a compact on-disk trace instead of growing the prompt, and break retry loops before they burn a budget. Use while executing a long-horizon task under [[harness-os]].
---

# Harness Fork

The purpose of forking is not speed. It is **keeping raw material out of the
main context**. A job that returns a 40-line summary instead of a 200-page PDF
is doing its job even if it runs strictly serially.

## Two kinds of job

**Deterministic work → kernel process.** Scripts, builds, tests, extraction,
conversion, analysis pipelines.

```bash
$K fork --job pdf_03 --cmd "python tools/summarize.py refs/03.pdf" --timeout 600
$K fork --job build_api --cmd "npm run build" --cwd services/api --timeout 900
$K poll                       # returns immediately; reaps finished, kills timed-out
$K wait --job build_api --timeout 900
```

- Jobs are detached — `fork` returns immediately. Fan out, then `poll` once.
- Each job gets `.harness/state/jobs/<id>/` with `stdout.log`, `stderr.log`,
  `meta.json`. Read the log file; do not stream it into the conversation.
- Timeout is enforced on `poll`, so **poll periodically** during long fan-outs.
  A job nobody polls is a job nobody kills.
- Jobs inherit `HARNESS_WORKSPACE`, `HARNESS_JOB_ID`, `HARNESS_SANDBOX`.

**Judgement work → sub-agent.** Summarising, drafting, classifying, reviewing.
Use the `Agent` tool with a **fresh, non-`fork` subagent** and instruct it to
write its output to a specific file path. Then verify that file with a contract.

Two rules that matter more than they look:

1. A `fork`-type subagent inherits your context — that reintroduces exactly the
   contamination you are forking to avoid, and makes it useless as a verifier.
2. Never let the agent that produced work grade it. See [[verify-with-rubric]].

## Trace discipline

```bash
$K trace --job pdf_03 --action extract --detail "12p, 3 figures"
$K trace --job pdf_03 --action extract --detail "no text layer" --status FAIL \
   --signature "empty_extract|direct|scanned_pdf_no_ocr"
```

One line per meaningful step. Compact — the trace is evidence, not narration.

The `--signature` triple, on every failure:

```
verifier_cause | causal_status | mechanism
```

- **verifier_cause** — what the check actually rejected: `missing_artifact`,
  `empty_extract`, `timeout`, `syntax_error`, `assertion_failed`, `schema_mismatch`
- **causal_status** — `direct` (this behaviour caused the failure),
  `contributing`, or `incidental`
- **mechanism** — the reusable agent-side behaviour behind it, not the symptom:
  `scanned_pdf_no_ocr`, `unbounded_retry`, `async_write_race`,
  `output_path_never_registered`, `budget_not_reconciled_with_methods`

Two failures cluster together only if all three match. Getting the mechanism
right is what makes the next round fix a class of problems instead of one file.
Failures without a signature land in an `unannotated` bucket and are, for repair
purposes, wasted.

## Loop breaking

```bash
$K loopcheck --job pdf_03
```

Run it before any third attempt at the same thing. If it returns
`{"loop": true}`, stop. Retrying harder is not a strategy. Do one of:

- change the **mechanism** (different tool, different approach, not different wording)
- fork a sub-agent with fresh context to look at it
- escalate to the user with what you tried and what the trace says

## Deviations

For long unattended runs, keep a [[deviation-log]] alongside the trace: before
each nontrivial step, one line stating the *assumption*; when reality differs,
take the conservative option, log expected/found/chosen/discarded, and keep
going. Stop and ask anyway when the situation is destructive, irreversible, or
would silently change what the user actually asked for.

## Context hygiene

The pattern that makes 100-PDF or 40-module work possible:

```
fork job → job writes summary file → main thread reads ONLY the summary
         → append one line to the playbook → forget the raw material
```

```bash
$K playbook add --section literature \
   --text "Lin 2026 AHE: gains localise to tools/middleware/memory, not prompt"
$K playbook list
$K playbook prune         # drops entries marked harmful more often than helpful
```

Add deltas; never rewrite the playbook wholesale. Wholesale rewrites are what
erode detail into ever-shorter summaries until the useful specifics are gone.

When a job's summary is on disk and its line is in the playbook, the raw
material is done — do not carry it forward.

Next: [[harness-assert]].
