---
name: harness-mine
description: Diagnosis phase of Harness OS — turn a pile of failures into a small number of named, addressable mechanisms by clustering them on failure signatures, so the next repair fixes a class of problems instead of one file. Use when assertions keep failing under [[harness-os]], when the same contract has failed three rounds running, or when a run is producing many errors that feel unrelated but probably are not.
---

# Harness Mine

The reason repair loops thrash is that they patch **symptoms**. Two jobs both
time out; one is an infinite retry, the other is a genuinely slow build. Same
verifier outcome, completely different fix. Patching "timeout" fixes neither.

Mining separates *what the verifier rejected* from *what the agent did to cause
it*, then groups only the failures that share both.

```bash
$K mine --round 1
# writes .harness/evidence/round_1/bundle.json
```

## The signature triple

```
verifier_cause | causal_status | mechanism
```

| Field | Answers | Examples |
|---|---|---|
| `verifier_cause` | What did the check reject? | `missing_artifact`, `empty_extract`, `timeout`, `syntax_error`, `schema_mismatch`, `missing_section` |
| `causal_status` | How did agent behaviour relate to it? | `direct`, `contributing`, `incidental` |
| `mechanism` | What reusable behaviour produced it? | `async_write_race`, `unbounded_retry`, `scanned_pdf_no_ocr`, `output_path_never_registered`, `budget_not_reconciled_with_methods` |

Clustering is exact-match on all three, so it is deterministic and auditable —
no semantic similarity, no judgement, no drift between rounds.

The `mechanism` field carries all the value. `timeout|direct|timeout` is worth
nothing. `timeout|direct|unbounded_retry_on_transient_network` names a thing you
can fix once and never see again.

## Reading the bundle

Clusters come back sorted by size. For each, ask two questions in order:

**1. Is it addressable by a harness change?** Not every failure is. A cluster
that reflects genuine task difficulty, an unstable external service, or a limit
of the model is not a harness bug. `addressable: false` marks clusters with no
annotated mechanism — annotate them or exclude them.

Excluding a cluster is a legitimate outcome. Forcing a patch onto a
non-addressable failure is how a harness accumulates junk that later has to be
untangled.

**2. Which component owns it?** Map the mechanism to exactly one:

| Component | Owns |
|---|---|
| **tool** | A capability that does not exist yet, or exists with the wrong interface |
| **middleware** | Something that should happen automatically every time — a pre-check, a retry policy, a write barrier, a budget guard |
| **memory / playbook** | Something that was learned and then forgotten |
| **skill** | A repeatable procedure worth writing down as steps |
| **sub-agent config** | Work that needs isolation or a different context |
| **system prompt** | Genuine behavioural framing — the *last* resort, not the first |

Measured ablation from the AHE work put the gains in **tools, middleware and
long-term memory**, and specifically *not* in the system prompt. Your instinct
under pressure will be to rewrite instructions. That instinct is wrong more
often than it is right. Ask: what tool is missing? What should run
automatically? What should have been remembered?

## Annotating late

If most failures landed in `unannotated`, the trace discipline slipped. Recover
by reading `$K readtrace --status FAIL --limit 60`, then re-tracing a
representative sample with proper signatures before mining again. It is worth
the five minutes — mining on unannotated failures produces nothing usable.

## Output

Pick **one to three** clusters. Not more. Each becomes a bounded proposal in
[[harness-evolve]]: one mechanism, one component, one minimal edit.

If mining shows the failures are not a harness problem at all — the spec is
wrong, the data is unusable, the request is underspecified — say that to the
user instead of proposing an edit. Some rounds correctly produce no edit.
