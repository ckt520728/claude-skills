---
name: harness-boot
description: Boot phase of Harness OS — establish durable state, write the goal and the definition of done, decompose the work so no job's raw material poisons the main context, and write deliverable contracts BEFORE any work starts. Use at the start of a long-horizon task under [[harness-os]], or when resuming a task whose state was lost.
---

# Harness Boot

Boot is where the run either becomes recoverable or does not. Everything here is
written to disk so that a crash, a context overflow, or a new session tomorrow
loses nothing but the conversation.

```bash
export HARNESS_WORKSPACE="<project root>"
KP="<plugin>/scripts/harness_kernel.py"      # quote it at the call site:
python "$KP" boot --profile <profile>        # a bare $K breaks on paths with spaces
python "$KP" status                          # resuming? run this first
```

Below, `$K` is shorthand for `python "$KP"`.

## Step 1 — Resume before you restart

If `.harness/` already exists, `status` tells you the goal, which contracts pass,
which jobs are stale, and whether the guard is intact. Read
`.harness/state/playbook.json` and the last 40 trace lines
(`$K readtrace --limit 40`) before doing anything else. Re-deriving state you
already have on disk is the most common waste in a resumed session.

## Step 2 — Goal and definition of done

```bash
$K goal --text "Draft an NSTC proposal for the HRV-cognition study" \
        --done "proposal.md passes all contracts and out/ contains the PDF"
```

The `--done` string has to be checkable by someone who was not in the room.
"A good proposal" is not a definition of done. "Six required sections present,
budget table totals match the equipment named in Methods, no placeholders,
≥ 4000 words" is.

If you cannot write a checkable `--done`, that is the signal to run
[[blindspot-pass]] or [[grilling]] first. Do not boot around an unresolved
unknown — it will surface in round three as a rewrite.

## Step 3 — Load the domain profile

`profiles/` in this plugin holds six starting points:

| Profile | For |
|---|---|
| `web-system` | Hospital pharmacy inventory, staff check-in/attendance systems |
| `research-proposal` | NSTC / grant applications, structured proposals |
| `signal-analysis` | EEG / HRV method development on public datasets |
| `literature-corpus` | Local PDF library triage, classification, review reports |
| `academic-writing` | Paper drafts, blog posts, structured long-form |
| `cognitive-app` | Portable clinic-time cognitive tests (Stroop, N-back) |

Each profile names its deliverables, the contract checks that matter for it, and
the failure modes that domain actually produces. Adapt rather than obey — but
say what you changed.

## Step 4 — Decompose by context poisoning, not by topic

The unit of a job is *whatever would otherwise have to sit in the main context*:
one PDF, one module, one section, one subject's recording, one migration.

Bad: "job: write the paper." Good: `sec_intro`, `sec_methods`, `sec_results`,
`refs_align` — each producing a file, each independently checkable.

The main thread keeps pointers and statuses. If you catch yourself pasting a
job's raw output into the conversation, the decomposition was wrong.

## Step 5 — Contracts before work

```bash
$K contract --name proposal --target draft/proposal.md --split held_in \
  --checks "exists,min_words:4000,sections:研究背景|文獻回顧|研究方法|預期成果|經費預算,no_placeholder"
$K contract --name budget --target draft/budget.json --split held_in \
  --checks "exists,valid_json,json_keys:equipment;personnel;total"
$K contract --name refs --target draft/proposal.md --split held_out \
  --checks "regex_present:\\[[0-9]{1,3}\\],regex_absent:\\[citation needed\\]"
```

Available checks: `exists`, `not_empty`, `min_bytes:N`, `min_words:N`,
`valid_json`, `json_keys:a;b;c`, `sections:A|B|C`, `regex_present:PAT`,
`regex_absent:PAT`, `no_placeholder`, `python_compiles`, `cmd:<shell command>`.

Notes:
- Inside `--checks`, use `;` where a check argument needs a comma — the kernel
  converts it back.
- `cmd:` runs any external verifier (`pytest -q`, `tsc --noEmit`,
  `python -m json.tool`, a puppeteer script) and passes on exit code 0. This is
  the strongest check available; prefer it wherever a real one exists.
- `no_placeholder` belongs on every prose or code deliverable.

**At least one contract must be `--split held_out`** — a check the repair loop is
not allowed to aim at. Without it the promotion gate cannot detect overfitting
and will warn you every round.

## Step 6 — Freeze the verifier

```bash
$K guard init                      # or: $K guard init --extra tools/verify.py
$K guard check                     # after every round
```

From here on, contracts and verifier scripts are read-only. Weakening a check to
make a deliverable pass is the single most damaging thing this loop can do, and
the guard is what makes it visible.

## Boot checklist

- [ ] `selftest` reported PASS at least once on this machine
- [ ] goal and a *checkable* definition of done are written
- [ ] a profile is loaded, or its absence is stated
- [ ] every deliverable has a contract, written before the work
- [ ] at least one contract is `held_out`
- [ ] `guard init` has run

Then hand off to [[harness-fork]].
