# Oak Option Ledger — <program name>

Durable evidence for the loop's Features, SubTasks, Options, Models, and planning decisions.
Update at the end of every interaction. Pre-filled for the `distil-cluster` literature-synthesis
Option; edit to your program. `loop-pause-all: false`

> Document-based *engineering analogue* of Oak's learned step-sizes (confidence/Brier in place
> of neural learning rates), not a literal implementation of Sutton's algorithm.

## Parent objective and reward
- **Parent objective:** <verified synthesis of the corpus, shipped as blog then manuscript>.
- **Trusted closed-world reward:** every load-bearing claim passes an independent
  `verify-with-rubric` check; every cited paper resolves to a real file or DOI.
- **Human-only judgment:** the thesis, scope, "what counts as enhancement/effect", publish.
- **Absolute gates:** publishing/push · writing to the source library · manuscript submission ·
  `.env*`/secrets.
- **Attempt cap:** 3 → `ESCALATE_HUMAN`. **Daily budget:** <set per session>.
- **Durable state authority:** this file, appended by hand. **Read-only** source library.

## Maintenance
- **Prune/reset:** weekly or per shipped artifact. **Confidence floor:** <2 trials → LOW; reset
  to LOW on any verification failure.

## Feature registry
### Feature: cluster-thin-for-target-scope
- **detector:** a corpus cluster with no covering synthesis note, OR whose existing note covers
  a *different* cluster/scope. **status:** proposed | verified | archived.

## SubTasks
### SubTask: distil-one-cluster
- **initiation:** a Feature-flagged cluster with an anchor list.
- **terminal test:** `synthesis/<cluster>.md` exists, cites ≥3 sources by path, passes the
  rigor rubric under an independent checker. **attempt cap:** 3.

## Options
### Option: distil-cluster  (status: proposed=L1 → gated=L2 → allowlisted=L3)
- **policy/steps (v1.1):** pkm-three-levels (index→synthesis→gaps) over the anchors →
  **cross-check every quantitative claim vs full-text methods** → **confirm each cited
  filename's actual title** → apply source-quality gate → verbatim-quotes-only → self-check vs
  rubric → hand to a **fresh, non-fork** decoupled verifier.
- **rollback:** additive doc / delete-draft (fully reversible; source library untouched).
- **regression:** re-running on an already-covered cluster returns "no new note needed".
- **signal:** trials=0, clean-pass=0, same-target=0.

## Option Model: distil-cluster@v1
- **predict before each trial:** p(first-try clean verify), cost, touched paths, failure modes.
- **scoring:** unresolved (pre-checker) = unknown, no update · accepted w/ only cosmetic fixes &
  no rubric failure = clean pass y=1 · **any rubric failure = y=0** (even if "accepted"). Brier
  `(p−y)²`.
- **promotion thresholds (HUMAN-APPROVED, fill in):** L1→L2 after ≥__ checker-confirmed clean
  trials AND mean Brier ≤ ____ + regression union + human digest. **L2 keeps the per-note
  independent verify.** Missing human approval blocks promotion. **Maker never self-promotes.**
- **calibration history:** <trial rows: predicted p, outcome y, Brier, new failure modes>.

## Planning decisions
| cycle | Feature/state | candidates | chosen | predicted utility/risk | baseline | actual | error |
|------:|---|---|---|---|---|---|---|

## Interaction log
| cycle | Option | prediction | evidence | surprise | Model/rate change | next |
|------:|---|---|---|---|---|---|

## Gate decisions
| date | artifact | transition | checker evidence | planning utility | approved by |
|---|---|---|---|---|---|

## Archive
Move pruned items here; never erase the audit trail.
