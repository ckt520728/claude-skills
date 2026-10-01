# 2026 Life OS

Builds and maintains a **Live Operation Rating System** on top of an existing Obsidian vault:
GTD's five stages, with the non-generative decisions moved off the frontier model onto a cheap
calibrated decision layer and gated on confidence.

The vault is the product. This folder is its workshop.

`AGENTS.md` is the same brief for non-Claude agents. Keep the two in step.

## Two locations, one system

```
G:\我的雲端硬碟\2026 Life OS\      <- THIS folder. The workshop. Never synced to the vault wholesale.
G:\我的雲端硬碟\Second Brain\      <- The live vault, 694 existing notes. The product.
```

Everything under `vault-src/` is the source of truth for what gets **deployed** into
`Second Brain\Life OS\`. Edit `vault-src/`, run `bash scripts/deploy.sh`, never hand-edit the
deployed copy — a hand edit is silently overwritten on the next deploy.

The one exception is user data: daily notes, retreats and GTD lists live only in the vault
and are never written by the deploy. `deploy.sh` refuses to touch them.

## The one idea

```
[G] generation   -> the frontier LLM, unchanged: coaching dialogue, note prose, synthesis
[D] decision     -> a System One decision model (Jev), typed answer + calibrated probability
[C] exact rule   -> code: date math, 7-day means, streaks, unlock gating, append-only guards
```

**Subtraction, not migration.** The LLM keeps everything it was built for. What leaves it is the
class of call it was never built for: "is this actionable", "which bucket", "how urgent".

If a change here reads as "let the classifier write the reflection", it has misread the idea.

## GTD x JEV: which stage asks which layer

| GTD stage | The question | Layer | Primitive |
|---|---|---|---|
| **Capture** | none — just write it down | — | — |
| **Clarify** | Is this actionable? | [D] | `Noul` |
| | Two-minute job / next action / project / reference / someday? | [D] | `Choice(5)` + `other` |
| | Which life area? | [D] | `Choice(8)` + `other` |
| **Organize** | Clippings / 知識庫 / 創作庫 / GTD? | [D] | `Choice(4)` + `other` |
| | Already covered by an existing 知識庫 page? | **[C]** | token overlap with `知識庫/index.md` |
| **Reflect** | How urgent? How much energy does it need? | [D] | `Score(5)`, `Score(3)` |
| | Did today's `dq_*` fall below its 7-day mean? | **[C]** | arithmetic |
| | Is the weekly review due? Which unlock day are we on? | **[C]** | dates |
| **Engage** | Given energy and context, which next action now? | [D] | `Choice` |
| | The actual coaching conversation, the written reflection | **[G]** | frontier LLM |

The rule that decides the column: if a wrong answer is caught by arithmetic, it is [C]. If the
answer is a label from a fixed set, it is [D]. If the answer is prose a human will read, it is [G].

## Layout

```
lifeos/                  stdlib-only Python. Runs in hooks; a dependency here is a real cost
  jev/                   THE jev-engineering skill's runnable layer, vendored verbatim and
                         hash-pinned (JEV_VENDOR.json). Never edit; fix the skill, then re-sync
  layer.py               Life OS's handle on jev: provider, calibration file, test stub
  gtd.py                 [D] clarify/organize as jev.Choice/Score/Noul, one decide() call, jev.gate()
  triage.py              the ask-resolution flow: where a decision becomes a label
  config.py              reads Meta/Compass Config.md -- the SSOT parser
  metrics.py             [C] 7-day means, streaks, deltas
  unlock.py              [C] Compass Build Order + the 80% consistency rule, as code
  clinical.py            derived clinical facts; numbers may travel, text may not
  vault.py               append-only writes, frontmatter mutation
vault-src/               source of truth for the deployed vault layer (Compass structure)
  00 Dashboards/         指南針儀表板 + 每日提問, 習慣畫布, 任務, 專案, 看板, 助理, 設定清單
  Meta/views/*.js        DataviewJS view modules (upstream pattern); gate.js = the Build Order
  Prompts/               12 recurring-job prompts with a `risk` property (upstream: 16)
  Guide/使用手冊.md       the user manual
  scripts/               nightly.js (Ctrl+Shift+Q) and capture.js (Ctrl+Shift+I), QuickAdd scripts
  Templates/             daily reference + 週記/季記/個人退修/專案/人物, filled by quicklinks.js
  _seed/                 created once, then the user's: Compass Config, 03 Planning, boards, 任務總表
scripts/deploy.sh        vault-src -> vault. Code overwritten, seeds kept once edited, retire by hash
scripts/deploy-ledger.tsv every hash deploy ever shipped: the proof a vault file is untouched
scripts/sync_jev.py      re-vendor the skill; --check fails on drift
scripts/lifeos_status.py the [C] numbers every coaching prompt calls instead of doing arithmetic
scripts/triage.py        the interactive clarify session; run it to teach the layer
scripts/checks.sh        the objective evidence. Run before calling anything done
eval/test_smoke.py       behavioural checks -- no key, no network
references/compass-upstream.md  what upstream Compass actually contains (full clone 2026-09-30)
UNKNOWNS.md              what is verified, what is assumed, what would change the design
HANDOFFS.md              session log; one entry per working session
```

## Invariants

Load-bearing. Changing one is a decision to record in `UNKNOWNS.md`, not a tidy-up.

1. **`lifeos/` stays stdlib-only, Python 3.9+.** Verified 3.9.12 on this machine — no runtime
   `X | Y` unions, no `match`. It runs inside Obsidian-adjacent hooks where a dependency is a cost.
2. **Journals are append-only.** Never rewrite or delete existing content in `每日筆記/`. New
   material is appended under a heading. This is the single rule whose violation loses real data.
3. **Decisions fail to `ask`, never to `auto`.** No key, network blip, low confidence — all three
   land on "ask the human". A gate that auto-files on error is worse than no gate.
4. **`other` is never auto-filed**, and anything touching money, health or another person
   always reaches a human regardless of confidence. Policy outranks classification.
4b. **Clinical text is derived, never transmitted.** `clinical_access: derived` (set by the
   user 2026-09-29). Code reads `## 🏥 臨床` locally and emits numeric facts only. The
   container that carries those facts to a prompt physically cannot hold a string —
   see `lifeos/clinical.py`. Widening to `full` is a separate explicit decision.
5. **Hard rules run in code before any model call.** Dates, means, streaks, unlock days. The
   model reads dates as text and miscounts at scale.
6. **Thresholds live in named constants in `lifeos/`**, never in a prompt and never in a
   DataviewJS block. The model reports belief; turning belief into a filing action is business logic.
7. **`Meta/Compass Config.md` is the only SSOT.** Every `dq_*`, `habit_*` and `wheel_*` key is
   defined there. A dashboard that hardcodes a key it did not read from config is a bug — when
   the user renames a question, the dashboard must follow without a code edit.
8. **English property keys, 繁體中文 content.** `dq_read: 8`, not `每日_閱讀: 8`. Keys stay
   English so upstream Compass scripts and DataviewJS work unchanged; every label a human reads
   is 繁體中文.
9. **The vault's own `CLAUDE.md` still governs the vault.** It says 繁體中文 responses and defines
   the three-layer PKM. The Life OS adds a layer; it does not overrule that file.

## The layering rule ships as code, not as advice

**Attribution re-corrected 2026-09-30.** Session 2 claimed upstream Compass has no layering
rule and "corrected" the docs. That was wrong — the fetch only returned a summary. The full
clone has `Guide/11 Build Order.md` and `Guide/01 Principles.md` §10, quoting Mike Schmitz:
pick one workflow, run it 30 days, then add the next; and "do not add a layer while the
previous one is below 80% consistency." Both rules are now code in `lifeos/unlock.py`,
mirrored in `vault-src/Meta/views/gate.js` (checks.sh fails if they drift):

| Day | Layer | Unlocks |
|---|---|---|
| 1 | `journal` | nightly `dq_*`, daily notes, capture (capture is never gated) |
| 31 | `habits_weekly` | habit canvas, weekly note + review |
| 61 | `retreat` | quarterly retreat, `wheel_*` radar, Life Theme / Core Values / Ideal Week |
| 91 | `tasks` | task + project dashboards, people, GTD **filing** (triage shadow-labels from day 1) |
| 121 | `writing` | 創作看板 |

Layers after the journal also need journal consistency ≥ 0.80 over the last 30 days. Only the
journal's consistency is measured — a deliberate narrowing of upstream's rule, stated here.

`start_date` lives in `Meta/Compass Config.md`. Dormant layers are built, tested and
inert — shown greyed with their unlock date and a "peek" button, not hidden. Do not
"helpfully" unlock a layer early; the gate is the feature.

## The decision layer IS the jev-engineering skill

**Corrected 2026-09-30.** Sessions 1-4 built `decide.py` + `calibrate.py`, a private copy of the
skill's ideas with its own API. Its questions broke the skill's own rules — bare option names
with no criteria (rule 1), an unlabelled 5-level Score (rule 3), four calls per capture
(rule 5) — and the skill's validation could not catch it because the skill was never imported.
The user called this out: the skill was not used.

Now `lifeos/jev/` is a verbatim copy of `D:\2026 JEV Engineering\skills\jev-engineering\assets\jev`
(`scripts/sync_jev.py`; `--check` in checks.sh fails on any hand edit). `gtd.py` defines every
question as a `jev.Choice` / `jev.Score` / `jev.Noul`, sends them all in **one**
`jev.decide(provider="local")` call, and gates with `jev.gate()` using per-label thresholds
(`BUCKET_TAU`, `FOLDER_TAU`). The criteria text on each option **is** the vocabulary the
`local` provider scores against — there is no separate lexicon. Improve accuracy by editing
criteria against real captures, never by lowering a threshold.

What `layer.py` adds is only Life-OS-specific: the calibration file lives in the vault, one
`jev.calibration.Calibrator` recalibrates every primitive from its raw score (the `local`
provider does not calibrate Nouls, by spec), and a stub provider for tests.

The `local` provider is not a fallback. JEV's argument is the KV-cache tax; a decision beside
the loop returning a typed value deletes it whether it is an HTTP call or a function call:

| | vendor API | local |
|---|---|---|
| latency | ~100ms + network | ~0.1ms |
| cost | fractions of a cent each | zero |
| offline | no | yes |
| calibrated against **your** labels | no | yes |

### Confidence is earned, never asserted

Raw scores are binned against **observed accuracy on this user's own resolved decisions**; a
bin with fewer than `MIN_OBSERVATIONS` reports `COLD_CONFIDENCE` (0.30) — below every gate.

- A cold layer asks about everything and files nothing. It earns the right to act.
- **Only adjudicated decisions become observations.** An unreviewed `AUTO` is not evidence.
- `triage.AUDIT_SAMPLE_RATE` = 20% of `AUTO` decisions are still shown, so a warm band can be
  corrected downward.
- **A band that is usually wrong never crosses the gate**, however many observations it has.
- 知識庫 and Clippings are never auto-filed (`FOLDER_TAU` = 1.01): 知識庫 carries an
  index.md/log.md duty nothing automates yet.

If a `TYPESAFE_API_KEY` ever arrives, `LIFEOS_PROVIDER=jev` makes it a third option to measure
against the local layer — not an automatic upgrade.

## Working here

**Run `bash scripts/checks.sh`** before calling any change done. It checks the SSOT parses, the
deploy is idempotent, the append-only guard holds, Python compiles on 3.9, and the behavioural
tests pass.

**Add a behavioural test for anything with a threshold in it.** `eval/test_smoke.py` drives
`jev.decide()` through `layer.make_stub()`, so every gate and unlock path is testable with no
key and no network.

**Never invent a `dq_*` question, a habit or a wheel area.** Those are the user's own honest
questions; a synthetic one pollutes their data and their trust. Ask, or leave the slot empty with
a comment.

**Deploy is one-way and idempotent.** `vault-src/` -> vault. If you need to pull a user edit back,
read it, decide deliberately, and edit `vault-src/`. There is no reverse sync and there should not be.

**Quantification bias is a known failure mode, not a footnote.** A 1-10 effort score invites
Goodhart's Law — scoring for the number instead of the day. The daily prompt asks about *effort*,
never outcome, for exactly this reason. Do not add outcome metrics to the daily loop.

## Suggested skills

- `map-vs-territory` / `blindspot-pass` — before a change to the system's structure or claims.
- `decision-first-plan` — order any multi-step change by decision volatility, not execution order.
- `grilling` + `domain-modeling` (= `/grill-with-docs`) — when a design decision here is genuinely
  unresolved. Facts get looked up; decisions get put to the user.
- `verify-with-rubric` — before accepting work that touches the user's real journal data.
- `handoff` — at the end of a session, appended to `HANDOFFS.md`.
- `pkm-three-levels` — the vault's existing Clippings/知識庫/創作庫 model.

## Open questions

Tracked in `UNKNOWNS.md` with what each one would change. The two that matter most: no threshold
here has been tuned against the user's real traffic, and nothing Obsidian-side (nightly.js,
capture.js, the Dataview views) has yet run inside the real app.
