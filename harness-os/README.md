# Harness OS

An operating-system-shaped harness for long-horizon agent work: durable state,
isolated parallel jobs, contracts written before the work starts, physical
verification before anything is called done, and an evidence-driven repair loop
with a regression gate.

Built from the fourteen papers in Lilian Weng's ["Harness Engineering for
Self-Improvement" (2026-07-04)](https://lilianweng.github.io/posts/2026-07-04-harness/),
read in full and mapped to design decisions in `references/evidence-ledger.md`.
Upgrades the Gemini prototype in `../Gemini Notebook notes/` and
`../Harness OS workspace/` (`references/prototype-delta.md`).

The post's own framing — *"Similar to an OS, a harness should encapsulate
complicated logic while keeping the interface simple"* — is the design brief the
kernel/skill split answers to.

**v2.1.0** adds three mechanisms extracted from a second body of material — a
synthesis of 2026 frontier agent benchmarks and the Codex system architecture —
each also independently grounded in the verified corpus (see
`references/evidence-ledger.md`, "v2.1.0 upgrade"):

- **`constraint`** — invariant rules that survive context compaction (Codex
  invariant prefix / ACE context collapse). Given and immutable, surfaced
  verbatim by `status`; distinct from the learned, prunable playbook.
- **`challenge:`** — dynamic challenge-response verification. A fresh nonce each
  run defeats hardcoded/memorised "passes" (ExploitBench oracle / STOP
  sandbox-bypass). Anti-gaming for the objectives that are actually checkable.
- **`ladder`** — a graded capability ladder: highest contiguous tier passed, a
  dense progress meter alongside the binary promotion gate.

## Install

```bash
python scripts/harness_kernel.py selftest          # 42 checks, must PASS
python scripts/verifiers/test_verifiers.py         # 72 checks, must PASS
cp -r skills/* ~/.claude/skills/               # Windows: copy skills\* to %USERPROFILE%\.claude\skills\
```

Then `/harness-os` in any project.

## Use

```bash
export HARNESS_WORKSPACE="/path/to/project"
KP="/path/to/harness-os/scripts/harness_kernel.py"
# quote the path at the call site; a bare $K breaks on paths containing spaces
alias K='python "$KP"'

$K boot --profile academic-writing
$K goal --text "..." --done "<checkable>"
$K contract --name draft --target draft/paper.md --split held_in \
  --checks "exists,min_words:3000,sections:Abstract|Methods|Results,no_placeholder"
$K guard init

$K fork --job sec_methods --cmd "python tools/draft.py methods" --timeout 600
$K poll
$K assertall --round 1
$K publish --contract draft
```

## Kernel commands

| Command | Does |
|---|---|
| `boot` / `status` / `goal` | Initialise, inspect, set goal and definition of done |
| `fork` / `poll` / `wait` | Detached jobs with sandboxes and enforced timeouts |
| `trace` / `readtrace` / `loopcheck` | Compact on-disk trace; loop breaker |
| `contract` / `assert` / `assertall` | Define and physically check "done" |
| `publish` | Re-verify, then copy to `out/` — refuses on failure |
| `mine` | Cluster failures by `(cause \| causal_status \| mechanism)` |
| `manifest` / `attribute` / `gate` | Falsifiable edit predictions; promotion gate |
| `snapshot` / `rollback` | Stepping-stone archive |
| `playbook` | Incremental delta memory (add / list / mark / prune) |
| `guard` | Tripwire on contracts and verifier scripts |
| `constraint` | Invariant rules that survive compaction (add / list) |
| `ladder` | Graded progress meter — highest contiguous tier passed (set / assert) |
| `selftest` | 42 checks proving the kernel works |

## Contract checks

`exists`, `not_empty`, `min_bytes:N`, `min_words:N`, `valid_json`,
`json_keys:a;b;c`, `sections:A|B|C`, `regex_present:PAT`, `regex_absent:PAT`,
`no_placeholder`, `python_compiles`, `cmd:<shell command>`,
`challenge:<shell command>`

Use `;` inside a check argument where a comma is needed. `cmd:` is the strongest
check available — prefer a real test suite over a structural proxy wherever one
exists. `challenge:` is `cmd:` with anti-gaming built in: the kernel injects a
fresh random nonce (`$HARNESS_CHALLENGE`) each run and the check passes only if
the verifier echoes it live, so a hardcoded answer cannot pass a challenge it has
never seen. `scripts/verifiers/` ships nine ready-made ones (budget alignment,
coherence, citation resolution, corpus coverage, glossary consistency,
reproducibility, trial-data integrity, timing quality, and challenge-response).

## Layout

```
harness-os/
├── skills/          harness-os (orchestrator) + boot / fork / assert / mine / evolve
├── scripts/
│   ├── harness_kernel.py   — stdlib only, Python 3.8+, cross-platform
│   └── verifiers/          — 9 verifiers for `cmd:`/`challenge:` checks (see its README)
├── profiles/        six domain starting points
└── references/      evidence ledger, prototype delta
```

The workspace it creates:

```
<workspace>/
├── .harness/
│   ├── config.json  guard.json
│   ├── state/       playbook.json, registry.json, jobs/<id>/
│   ├── logs/        trace.jsonl, eval/round_N.json
│   ├── contracts/   one per deliverable   (read-only once guarded)
│   ├── evidence/    round_N/bundle.json
│   ├── manifests/   round_N.json
│   └── archive/     round_N/ snapshots
└── out/             verified deliverables only
```

## Scope

Worth the overhead on work that is long (over an hour, or spans sessions),
parallel, expensive to redo, or has been falsely reported done before.

**Not** worth it on a single-file edit, a question, or a short script.

Partial adoption is legitimate: contracts + `assert` + `publish` alone remove
most false-completion failures at almost no cost. Add fork / mine / evolve only
when the task needs them.

## Honest limits

- The loop optimises against the verifier. Where the verifier is a real test,
  that is what you want. Where it is a proxy — an LLM judge, a structural check
  standing in for quality — the loop will find the gap. Never run it
  unsupervised against a subjective objective.
- `guard` is a tripwire, not a sandbox. It makes tampering visible; it does not
  prevent it. Real isolation needs OS permissions or a container.
- `challenge:` proves the verifier ran live on an unrepeatable nonce; it does
  not prove correctness in general, and a verifier that re-echoes
  `$HARNESS_CHALLENGE` without routing it through the artifact games itself.
  Route the nonce through the deliverable.
- Detached jobs do not return an exit code; `poll` reports completion and the
  stderr tail. Where the exit code matters, have the job write a result file and
  contract it with `cmd:`.

## Changelog

### v2.1.0 — 2026-09-06

Merged to `master` via [PR #4](https://github.com/ckt520728/claude-skills/pull/4)
(squash `e41f40c`). Three mechanisms extracted from the 2026 frontier-benchmark /
Codex corpus, each also grounded in the verified `Reference/` corpus:

- **`constraint`** — invariant rules that survive context compaction; surfaced
  verbatim by `status`, never pruned. Distinct from the learned/prunable playbook.
- **`challenge:`** — contract check with a fresh random nonce each run; passes
  only if the verifier echoes it live, defeating hardcoded answers. New verifier
  `check_challenge_response.py`.
- **`ladder`** — graded capability ladder (highest contiguous tier passed); a
  progress meter alongside, not replacing, the binary promotion gate.

ScreenSeekeR pixel-grounding and recurrent-depth/latent-reasoning deliberately
excluded, with reasons in `references/evidence-ledger.md`. Gates: kernel selftest
31 → 42, verifier suite 64 → 72.

### v2.0.0 — 2026-09-02

Initial release, merged via PR #3 (`37ffa4f`). OS-shaped kernel: durable
filesystem state, detached parallel jobs with enforced timeouts, contracts +
`assert` + `publish` gate, failure-signature `mine`, falsifiable edit manifests,
held-in/held-out promotion `gate`, snapshot/rollback archive, `guard` tripwire.
Six domain profiles and eight profile verifiers. Built from the fourteen papers
in Lilian Weng's "Harness Engineering for Self-Improvement".
