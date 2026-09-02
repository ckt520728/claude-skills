---
name: harness-os
description: Run a long-horizon deliverable as an operating system rather than one long conversation — persistent state on disk, isolated parallel jobs, a written contract for what "done" means, physical verification before anything is called finished, and an evidence-driven repair loop when it isn't. Use for multi-hour or multi-session work with a real artifact at the end: building a web system, writing a grant proposal, analysing a signal-processing method, digesting a PDF library, drafting a paper, or shipping a portable clinical app. Also use when a previous run collapsed — lost the thread, looped on the same failing command, ran out of context, or reported "done" for something that was empty, truncated, or full of placeholders. Triggers: "harness os", "run this as a harness", "long-horizon task", "this keeps losing track", "it said done but it isn't", "跑 harness", "長任務編排".
---

# Harness OS

A frozen model plus a better surrounding system beats the same model in a plain
conversation — often by more than a model upgrade does. That surrounding system
is the **harness**: state, tools, middleware, verification, memory, orchestration.
This skill is a harness you drive from the terminal.

The failures it exists to remove are physical, not intellectual:

| Failure | What actually happened | Kernel answer |
|---|---|---|
| "It forgot the plan" | State lived only in the context window | Playbook + trace on disk |
| "It looped on the same command" | No memory of the last three steps | `loopcheck` |
| "It ran out of context reading PDFs" | Raw material stayed in the prompt | Fork per item, summary to disk, purge |
| "It said done but the file was empty" | Verbal completion, no verification | Contracts + `assert` + `publish` gate |
| "The fix broke something else" | No regression gate | held-in / held-out `gate` |
| "It kept 'fixing' the wrong thing" | Patching symptoms, not mechanisms | Failure signatures + `mine` |

**The kernel is at `scripts/harness_kernel.py`** (relative to this plugin). It is
plain Python 3.8+, standard library only, cross-platform. Run
`python <path>/harness_kernel.py selftest` once — it must report `PASS` before
you trust anything below.

Set `HARNESS_WORKSPACE` once per session so every later call is short:

```bash
export HARNESS_WORKSPACE="/path/to/project"   # PowerShell: $env:HARNESS_WORKSPACE=...
KP="/path/to/harness-os/scripts/harness_kernel.py"
python "$KP" boot --profile academic-writing
```

Keep the path in a variable and **quote it at the call site** — `K="python
/path/…"` then bare `$K` word-splits and breaks the moment the path contains a
space, which it does on this project. `$K` below is shorthand for
`python "$KP"`.

## The loop

```
   BOOT ──► DECOMPOSE ──► CONTRACT ──► FORK ──► TRACE ──► ASSERT ──► PUBLISH
     ▲                        │                              │
     │                        │ (contracts are written       │ fail
     │                        │  BEFORE any work starts)     ▼
     └──── EVOLVE ◄──── PROPOSE ◄──── MINE ◄─────────────────┘
           (gate)      (bounded)   (signatures)
```

Each stage has its own skill; read the one you are in, not all six:
[[harness-boot]] · [[harness-fork]] · [[harness-assert]] · [[harness-mine]] ·
[[harness-evolve]]

### 1. BOOT — state before work

```bash
$K boot --profile <profile>
$K goal --text "<one sentence>" --done "<what a stranger could check>"
```

Pick a profile from `profiles/` (`web-system`, `research-proposal`,
`signal-analysis`, `literature-corpus`, `academic-writing`, `cognitive-app`).
Read it — it names the deliverables, the checks and the failure modes that
domain actually has. If none fits, work from the closest one and say so.

If the request is fuzzy, unfamiliar, or you would otherwise be guessing at a
tacit standard, run [[blindspot-pass]] or [[grilling]] **before** booting.
Unknowns are cheaper to close now than to discover in round three. Then write
the plan as a [[decision-first-plan]].

### 2. DECOMPOSE — one job per context-poisoning unit

Split so that no single job's raw material has to sit in the main context: one
PDF, one module, one section, one subject's recording. The main thread holds
pointers and status, never payloads.

### 3. CONTRACT — write "done" down before you build

```bash
$K contract --name lit_report --target out/review.md --split held_in \
  --checks "exists,min_words:1500,sections:Background|Method|Findings|Limitations,no_placeholder,regex_present:\\[[0-9]+\\]"
```

Non-negotiable: **contracts are written before the work, never after.** A
rubric assembled after the fact gets shaped around whatever was produced, which
is exactly the failure it was meant to catch.

Split at least one contract as `--split held_out`. Held-in tells you the fix
worked; held-out tells you it did not break something else. With no held-out
contract the promotion gate cannot see overfitting, and it will say so.

Then freeze them: `$K guard init`. This is a tripwire, not a sandbox (see
Anti-gaming below).

### 4. FORK — real background processes

```bash
$K fork --job pdf_03 --cmd "python tools/summarize.py refs/03.pdf" --timeout 600
$K poll                      # never blocks
$K wait --job pdf_03 --timeout 900
```

Jobs run detached with an enforced timeout and per-job sandbox at
`.harness/state/jobs/<id>/`. Details: [[harness-fork]].

For work that needs a model rather than a script, use the `Agent` tool with a
fresh (non-`fork`) subagent and have it write its output to a file — then
verify that file. Never grade an agent's work with the agent that produced it.

### 5. TRACE — evidence on disk, not in the prompt

```bash
$K trace --job pdf_03 --action extract --detail "12 pages, 3 figures"
$K trace --job pdf_03 --action extract --detail "no text layer" --status FAIL \
   --signature "empty_extract|direct|scanned_pdf_no_ocr"
$K loopcheck --job pdf_03
```

The `--signature` triple is `verifier_cause|causal_status|mechanism`. Spend the
five seconds to write it: unannotated failures cluster into a useless bucket and
the repair loop degenerates into guessing.

Run `loopcheck` before any third attempt at the same thing. If it fires, stop —
change the mechanism or ask the user. Do not retry harder.

### 6. ASSERT — physical verification

```bash
$K assertall --round 1
$K publish --contract lit_report
```

`publish` re-runs the contract and refuses to copy anything that fails. Nothing
reaches `out/` unverified.

**Report what the verifier said, not what you intended.** If a contract fails,
say so with the failing checks. "Done" is a claim the kernel either supports or
refuses.

### 7. MINE → PROPOSE → EVOLVE — repair with evidence

Only when assertions fail. See [[harness-mine]] and [[harness-evolve]].

```bash
$K mine --round 1
$K manifest --round 1 --edit-id e1 --component middleware \
    --evidence "cluster empty_extract|direct|scanned_pdf_no_ocr (n=7)" \
    --root-cause "extractor assumes a text layer" \
    --fix "detect empty extract, route to OCR" \
    --predict-fix "lit_report" --predict-regress ""
# ... apply the edit, then:
$K assertall --round 2
$K attribute --round 1     # did the prediction land?
$K gate --round 1          # held-in up, held-out not down?
$K rollback --round 1      # if refuted
```

Every edit ships a falsifiable prediction. An edit whose prediction does not
land is rolled back, not rationalised. That single rule is what separates a
repair loop from thrashing.

## Where the leverage actually is

Measured ablation (AHE, Lin et al. 2026): the gains localised to **tools,
middleware and long-term memory** — *not* the system prompt. When something is
failing, your first instinct will be to rewrite instructions. Resist it. Ask
instead: what tool is missing, what check should run automatically, what should
have been remembered?

## Model routing

Harness-updating ability is roughly flat across model tiers — a mid-tier model
writes about as useful an edit as a frontier one. Harness-*benefit* is not: it
peaks at mid-tier and the weak tier gains little, mostly because weak models
fail to invoke the harness artifacts at all or invoke them and then drift.

Practical consequences:

- Cheaper models are fine for mining, summarising, and drafting edits.
- The agent **executing** long-horizon work must actually follow the harness.
  If it stops running `assert` or stops writing traces, that is the failure —
  the harness is being ignored, not disproven.
- Spend capability budget on the executor, not the evolver.

## Boundary condition — read this before trusting the loop

This loop is only as good as its verifier.

- **Strong here:** anything with a fast, faithful, automatic check — code that
  compiles, tests that run, JSON that parses, files that exist, schemas that
  validate, numbers that reconcile.
- **Weak here:** novelty, elegance, scientific taste, whether an argument is
  actually persuasive. There is no cheap faithful verifier for those.

For subjective deliverables (papers, proposals, blog posts) the checkable layer
is *structural*: required sections present, citation markers resolve, no
placeholders, word budget met, terminology consistent, no duplicated paragraphs,
budget lines reconcile with the methods section. Contract those. For the
judgement layer, use [[verify-with-rubric]] with a separate context-isolated
sub-agent — and treat its verdict as advice to a human, not as ground truth.
**Never let a self-improvement loop optimise against an LLM judge unsupervised.**

## Anti-gaming

The loop will exploit whatever it is graded on. Rules:

1. Contracts, verifier scripts and traces are **read-only** to any repair or
   sub-agent work. `guard init` before the loop, `guard check` after each round.
   A `TAMPERED` result voids every result since the last clean check.
2. Never weaken a contract to make it pass. If a contract is genuinely wrong,
   stop and say so to the user — changing the target mid-run is their call.
3. `no_placeholder` is a required check on every prose or code deliverable.
   Truncation and "…rest of the file" are the most common form of fake
   completion.
4. `guard` is a tripwire, not a security boundary — it makes tampering visible
   in the record. Real isolation needs OS permissions or a container.

## Cost discipline

Booting a harness costs real overhead. It pays for itself on work that is long
(over an hour or spans sessions), parallel, expensive to redo, or has been
falsely reported done before. **Do not boot it for a single-file edit, a
question, or a short script.** A harness on a ten-minute task is friction
wearing a costume.

Partial adoption is legitimate and often correct: contracts + `assert` +
`publish` alone remove most false-completion failures and cost almost nothing.
Add fork/mine/evolve only when the task actually needs them.

## Reporting

Work in English internally; deliver to the user in **Traditional Chinese
(繁體中文)** unless they write to you in another language. Keep technical terms
in English where that is what the field uses.

Report status as a compact table — contract, PASS/FAIL, artifact path — not as
prose narration of what you did.
