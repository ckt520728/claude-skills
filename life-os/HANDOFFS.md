# HANDOFFS

One entry per working session, newest first. Each entry says what changed, what was verified,
and what the next session should pick up.

---

## 2026-09-30 — Session 5: the skill is actually used; the vault is actually Compass-shaped

### The user's correction

"Claude didn't follow this prompt to use [the JEV Engineering skill] and take my reference link
[github.com/AgriciDaniel/compass] to design a compass-like Obsidian second brain." Both halves
were right, and both had the same root: sessions 1–4 worked from *descriptions* of the two
references instead of the references themselves.

### 1. JEV: from a private imitation to the skill itself

`decide.py` + `calibrate.py` + `jev_stub.py` were a parallel implementation with their own API.
Measured against the skill's seven rules they broke three: options without criteria (rule 1),
an unlabelled `Score(5)` (rule 3, which `jev.Score` rejects outright), four calls per capture
(rule 5). None of this was catchable because the skill was never imported.

- `lifeos/jev/` — verbatim copy of `D:6 JEV Engineering\skills\jev-engineeringssets\jev`
  v1.1.0, hash-pinned in `lifeos/JEV_VENDOR.json`; `scripts/sync_jev.py [--check]`.
- `lifeos/layer.py` — provider + calibration file + test stub; recalibrates every answer from its
  raw score with one `jev.calibration.Calibrator` (the `local` provider does not calibrate Nouls).
- `lifeos/gtd.py` — rewritten: six questions as `jev.Choice/Score/Noul` with bilingual criteria,
  **one** `jev.decide()` per capture, `jev.gate()` with per-label thresholds (`project` 0.85;
  `知識庫`, `Clippings`, `other` never auto). Duplicate detection moved from a Noul the local
  layer could not answer to a [C] token overlap against `知識庫/index.md`.
- Deleted: `decide.py`, `calibrate.py`, `jev_stub.py`. Tests assert they stay deleted.

### 2. Compass: from "inspired by" to the upstream structure

Full `git clone` this time (session 2's fetch returned a summary). Two consequences:

- **Session 2's central "correction" was itself wrong.** Upstream has a layering rule —
  `Guide/11 Build Order.md`, plus "do not add a layer while the previous one is below 80%
  consistency." Retracted in `references/compass-upstream.md`; `unlock.py` now implements the
  real Build Order (1/31/61/91/121) and the 80% rule, mirrored in `gate.js` with a parity check.
- Vault restructured under `Life OS/` into upstream's numbered layout. Ported the view modules
  (`Meta/views/*.js`) with SSOT labels; added gate/tasks/projects/clinical/onthisday. Eight
  dashboards (指南針儀表板 is the home), 5 templates, Planning notes, boards, master task list,
  12 prompts with `risk`, Setup and Assistant pages, `capture.js` (journal / win / gratitude /
  inbox on one hotkey), `lifeos_status.py` (the [C] numbers prompts call).
- No Templater / Periodic Notes / Tasks: `quicklinks.js` creates periodic notes from templates;
  Dataview reads the Tasks emoji format.
- **User manual**: `vault-src/Guide/使用手冊.md` → deployed to `Life OS/Guide/使用手冊.md`.

### 3. Deploy: a latent data-loss bug

The old deploy copied every `vault-src/**` file on every run — including `GTD/收件匣.md`, the
file the user was told to write captures into. The first real capture would have been
overwritten by the next deploy. Now: `_seed/` files are created once and upgraded only while
their hash is in `scripts/deploy-ledger.tsv` (proof they are untouched); retired files are removed
only under the same proof. A throwaway-vault test in `checks.sh` pins this. A second bug found by
that test: `${2#$VAULT/}` treated the path as a glob; quoted.

### Found, not caused

QuickAdd's `data.json` has **zero choices** — `Ctrl+Shift+Q` was never bound. That is why U2
stayed open four sessions. The manual's chapter 1 and 設定清單 now walk through it.

### Verified

- `bash scripts/checks.sh` → **70 PASS, 0 FAIL** (was 42)
- `eval/test_smoke.py` → **124/124** (rewritten against jev; new: skill-usage, Build Order, 80%)
- All 14 Obsidian-side JS files pass `node --check` (views wrapped for top-level await)
- Deployed: 50 written, 11 retired by hash, second run 0 changed. `每日筆記/`, `.obsidian/` untouched.

### Not verified

Nothing Obsidian-side has run in the app (U8). Criteria text is blind (U3b).

### Next session should

1. Ask whether the two QuickAdd macros exist now, and what the Dataview console said (U2, U8).
2. After ~20 real captures: `python scripts/triage.py --report`; edit criteria, not thresholds.
3. Nothing *applies* a filing decision yet — needed by day 91 (2026-12-28).
4. The user said "git worktree" mid-session, then chose to continue without git. Offer `git init`
   again if they want reviewable history.

---

## 2026-09-30 — Session 4: the resolution loop is wired

Session 3 left `record_outcome()` called only by tests. The user asked for it to be wired into
the ask-resolution flow — and the honest finding was that **no such flow existed**. Nothing
presented a decision to a human and captured the answer. So the surface had to be built, and
the design has one trap worth recording.

### The trap: not every decision is evidence

The obvious design records every decision as an observation. It is wrong, and quietly so.

An `AUTO` decision nobody looked at is **not evidence it was right**. Record it as correct and
you build a loop that confirms itself: the band looks accurate because nothing contradicts it,
confidence rises, it files more, and it generates even less evidence. By the time it is visibly
wrong the calibration file says it is excellent.

So **only adjudicated decisions become observations** — a human agreed or corrected.

Which creates the opposite problem: a band that graduates stops being adjudicated and can never
be corrected downward. Drift becomes invisible. Hence `triage.AUDIT_SAMPLE_RATE = 0.2` — one in
five `AUTO` decisions is shown for confirmation anyway, so a warm band keeps being measured.
That is the price of trusting automation, and it is deliberately not zero.

### Built

- **`lifeos/triage.py`** — `parse_inbox` (read-only), `propose`, `resolve` / `resolve_all`
  (the wiring: calls `gtd.record_outcome`), `needs_human`, `sample_for_audit`, a JSONL audit
  log with `summarize_log` (agreement rate), and `filing_allowed` for the unlock gate.
- **`scripts/triage.py`** — the interactive session. Enter accepts, a number overrides, `s`
  skips. `--demo` touches no vault file; `--report` prints the reliability table and agreement
  rate. Refuses rather than hangs when stdin is not a TTY.
- `vault-src/GTD/收件匣.md` now tells the user how to run it and why their answers matter.

### Shadow mode makes the locked month productive

Filing stays locked until day 31, but *labelling* is safe from day 1: propose, ask, record,
write nothing. That is exactly rule 7's shadow period. Running it during the locked month means
the layer reaches day 31 carrying evidence instead of cold — the lock stops being a wait and
becomes the training window.

### Verified

- `scripts/checks.sh` → **42 PASS, 0 FAIL**, including a new "the resolution loop is wired"
  section that fails if resolving an ask no longer reaches the calibrator, or if audit
  sampling is ever turned off.
- `eval/test_smoke.py` → **125/125** (was 101).
- Simulated end to end against the real config: 4 captures cold at conf 0.30 / ASK → 48
  adjudications → conf 0.93 / AUTO, 100% agreement, 4/4 bins warm.

### Two test-vs-code calls worth recording

- A test asserted a graduated question left `questions_for_human()` empty. Wrong: only `bucket`
  was warmed, so `folder`, `area` and `actionable` correctly still ask. Per-question
  calibration working as designed — the test was fixed, not the code.
- The stdlib allowlist in `checks.sh` lacked `random`, `time` and `ast`. All stdlib; allowlist
  widened rather than the imports removed.

### Honest limits, unchanged from session 3

The 48-adjudication simulation used four captures written by the same person who wrote the
lexicon. It demonstrates the *mechanism*, not the accuracy. Real agreement rate is unknown
until real captures exist (U3b), and the GTD inbox is still empty.

### Next session should

1. **Still unresolved, still highest value: run `Ctrl+Shift+Q` once** (U2).
2. Put 10–20 real captures in `Life OS/GTD/收件匣.md` and run `scripts/triage.py` in shadow
   mode. That resolves U3b and starts warming the layer before day 31.
3. `--report` after a couple of sessions: if agreement sits below ~70%, edit the lexicon rather
   than lowering the gate.
4. Nothing yet *applies* a filing decision to the vault once day 31 unlocks — `resolve()`
   records but does not move anything. That write path is the remaining gap.

---

## 2026-09-29 — Session 3: the decision layer is real (user correction)

### The correction

The user pointed out that sessions 1–2 never actually used the JEV workflow, having concluded
that no `TYPESAFE_API_KEY` meant no decision layer — and that this misreads the idea.

They were right. JEV's argument is about the **KV-cache tax**: what deletes it is that the
decision happens *beside* the loop and returns a typed value the code branches on. That property
is architectural and names no vendor. `jev_stub.py` returning a constant 0.34 was not a decision
layer; it was a placeholder dressed as one, and calling it "inert on purpose" made the mistake
sound like a design choice.

### Built: `lifeos/decide.py` + `lifeos/calibrate.py`

A working local layer. `Choice` / `Score` / `Noul` over a bilingual (繁中 + English) lexicon.
**~0.1ms, zero cost, no network.** For a personal Life OS this is better than the API, not a
fallback — and the decisive reason is the last row of the table in `CLAUDE.md`: it can be
calibrated against *this user's* labels, which no vendor can do.

`calibrate.py` is what makes it JEV-spirited rather than JEV-shaped. A softmax number is not
confidence. Raw scores are histogram-binned against observed accuracy, and:

- a cold bin reports `COLD_CONFIDENCE` (0.30), below every gate, so the layer asks;
- a consistently-correct band crosses `AUTO_FILE_CONFIDENCE` and starts auto-filing;
- **a band that is usually wrong never crosses it**, however many observations it has;
- every resolved ask is a label (`gtd.record_outcome`), so rule 7's shadow period stops being a
  phase to remember and becomes the operating mode.

Demonstrated end-to-end: cold → asks everything → learns → warms → auto-files. `brier_score`
and `expected_calibration_error` report whether confidence means anything.

### A real bug the new tests caught

`clarify()` passed a Noul's **probability** straight in as confidence, so a noul of 0.88
auto-filed while calibration was stone cold. Those are different quantities and the spec is
explicit that a Noul carries no confidence field. Fixed: the caller now derives *decisiveness*
(`|p − 0.5| × 2`, distance from the undecidable midpoint) and runs that through calibration
like every other raw score.

Also fixed: the stdlib-import check was grepping line-by-line and reading docstring examples in
`decide.py` as real imports. Now parsed with `ast`, which knows code from prose.

### Modified the JEV skill itself

`D:\\2026 JEV Engineering\\skills\\jev-engineering`:

- **`assets/jev/calibration.py`** (new) — the generic calibration machinery.
- **`assets/jev/providers/local.py`** (new) — a real `local` provider, registered. It scores the
  state against **each option's own criteria text**, so no lexicon is baked in: the vocabulary is
  the spec the caller already had to write under rule 1. A badly specified `Choice` scores badly
  there, which is the rule failing in the right direction.
- **`references/13-portability.md`** — `local` promoted from "a callable you register" (shipping
  nothing) to a documented first-class path, with the honest comparison table and the warning
  that reaching for `llm` when you lack a key reintroduces the exact cost the layer removes.
- **`references/10-threshold-tuning.md`** — new "Calibration as code, not as a phase" section.
- **`SKILL.md`** — a "No key? The layer still works" paragraph.
- Skill suite: **108 → 137 behavioural checks**, all passing; `bash .claude/checks.sh` green.

Verified through the real `decide()` API: 5/5 correct including `other` for gibberish,
`usage={'input_tokens': 0}`, `cost=$0.000000`, `latency=0.07ms`.

### Verified

- Life OS: `scripts/checks.sh` → **35 PASS, 0 FAIL**; `eval/test_smoke.py` → **101/101**
- JEV skill: `.claude/checks.sh` → all green; **137 behavioural checks**

### Honest limits

- The lexicon was written **blind** — no real capture exists to fit it against (`每日筆記/` has
  one note, no GTD inbox yet). The 5/5 demo used captures written by the same person who wrote
  the lexicon and proves nothing. Recorded as **U3b**.
- No world knowledge, no synonymy, no negation handling. CJK segmentation is bigram-based.
- Safe only because calibration makes it *report* being wrong. That is the whole design.

### Next session should

1. Still unresolved and still highest-value: **run `Ctrl+Shift+Q` once** (U2).
2. Collect 20–30 real captures and edit the lexicon against them (U3b).
3. Wire `record_outcome()` into whatever UI resolves an ask — nothing calls it yet outside tests.
4. Consider registering `lifeos.decide.jev_provider` with the upstream package to use one
   implementation in both places.

---

## 2026-09-29 — Session 2: clinical activation + Compass upstream fetched

Two user decisions landed in one session, and both changed things the first session had
written down as settled.

### 1. Clinical section activated at level `derived` (U4 resolved)

The user activated `## 🏥 臨床`, choosing **derived** over local-only and over full-text.

Contract: code reads the section **on the user's machine** and emits numeric facts only
(`clinical_pending`, `clinical_load`). Raw case text may not reach a prompt, a log line, an
error message, or any network call.

Enforced structurally, not by instruction:

- `lifeos/clinical.py` — `ClinicalDigest` has fixed `__slots__` that hold numbers only, and
  `as_dict()` runs `assert_transmittable()` before returning. A string cannot be smuggled into
  the object that goes to the model.
- `nightly.js` derives the counts inside Obsidian and writes only the two scalars into
  frontmatter. The coach reads frontmatter, so it has no reason to open the body at all.
- `eval/test_smoke.py::TestClinicalBoundary` builds a digest from realistic clinical text and
  asserts none of 12 distinctive tokens appears in the transmittable output. `checks.sh`
  repeats it, so a regression fails the build.
- Writing *into* the section is still refused, activation notwithstanding.
- An unrecognised `clinical_access` value falls back to `never` — a typo cannot widen access.
- Even at `full`, `coach_context()` still does not return raw text. Widening is a second,
  deliberate change.

Two stale tests were found asserting the old `never` policy. They encoded a decision the user
had since reversed, so they were updated to pin the new one — including a guard that fails if
the shipped config is ever set to `full`.

### 2. Compass repo fetched (U1 resolved) — five stated claims were wrong

Full comparison now in `references/compass-upstream.md`.

Confirmed: `Meta/Compass Config.md` as SSOT, the three prefixes, `AGENTS.md` safety rules,
16 prompts, the MCP bridge, numbered folders, `life-os-app`, Goldsmith/Reiter *Triggers*.

**Contradicted**, and corrected across `CLAUDE.md` / `README.md` / `Compass Config.md`:

1. Upstream config uses `questions:` / `key:` / `text:`, not `dq_questions:` / `id:` / `prompt:`.
2. `habits:` and `wheel_areas:` are flat string lists, not mappings.
3. 11 required plugins, not 10.
4. The system is **Mike Schmitz's**; Agrici built the template. Session 1 credited Agrici.
5. **No 30-day layering rule exists in the repo.** Session 1 built the entire unlock gate and
   cited Compass as authority. The gate is still right — but on local evidence (one daily note
   since 2026-05-09, against a template that could never expand), not borrowed authority.

Acted on: `lifeos/config.py` now parses **both** schemas, pinned by 8 tests against the verbatim
upstream config; `birthdate` / `life_expectancy` (upstream's `memento` feature) adopted;
upstream's "note content is data, not instruction" rule adopted into both `AGENTS.md` files.

A second real bug surfaced here: `Config.validate()` raised `ConfigError` on a prefix violation
instead of reporting it. A health check that throws is useless — it now collects the problem as
a line. Also learned: prefix enforcement makes cross-group id collisions structurally
impossible, so the duplicate test was rewritten to test a within-group duplicate.

### Verified

- `scripts/checks.sh` → **34 PASS, 0 FAIL**
- `eval/test_smoke.py` → **74/74**
- Deploy: 5 files updated, 11 unchanged, all 16 byte-identical; user data untouched

### Next session should

1. Still the highest-value action: **run `Ctrl+Shift+Q` once in Obsidian** (U2 unresolved).
2. Check `clinical_pending` against a real week — bullet-counting is a proxy, and if the user
   writes cases in prose it silently reads 0 and the coach is quietly wrong.
3. `LOAD_THRESHOLDS` in `clinical.py` are untuned guesses.
4. Port dashboards to upstream's `Meta/views/*.js` + `lib.js` pattern once Dataview is enabled —
   the 7-day-mean logic is currently duplicated across two dashboards.
5. Ask for `birthdate` to switch on memento.

---

## 2026-09-29 — Session 1: initialization and the day-1 loop

### What this session was asked for

Build a Life OS on the user's Obsidian second brain: GTD workflow, task management, goal
tracking, knowledge management, habit tracking, plus a `jev-engineering` decision layer.
Initialize the project (`CLAUDE.md` / `AGENTS.md`, a handoffs file), using `/grill-with-docs`
and the finding-unknowns skills.

### The three decisions put to the user, and what they chose

1. **Topology** → one `Life OS/` folder inside the existing vault, rather than five numbered
   root folders or a separate vault. Daily scoring writes into the existing `每日筆記/`.
   Reason: the vault's own `第二大腦地圖.md` states a root-minimalism principle.
2. **First scope** → scaffold everything, activate the daily layer only. The 30-day layering
   rule ships as code in `lifeos/unlock.py`, not as advice.
3. **Language** → 繁體中文 content, English property keys, so upstream DataviewJS and Compass
   scripts work unchanged.

### The finding that reframed the work

`每日筆記/` contains exactly **one** note, `2026-05-09.md`, and nothing in the 4½ months since.
The cause is almost certainly mechanical, not motivational: `Templates/每日筆記.md` is written
in Templater syntax (`<% tp.date.now() %>`) and **Templater is not installed in this vault**.
The template could never expand.

Also found: only **five** plugins are enabled — `local-rest-api`, `quickadd`, `calendar`,
`omnisearch`, `make-md`. **Dataview is installed but disabled.** The entire Compass reference
architecture assumes DataviewJS dashboards and Templater templates, so neither was usable.

Consequence, and the main design decision of the session: **the day-1 loop was built to need
zero new plugins.** QuickAdd's user-script API plus Obsidian's native `processFrontMatter` is
sufficient. Dataview (one toggle) and Templater (an install) became optional upgrades, each
documented with what it buys. This also means the dashboards must degrade gracefully, which
they do — they lead with an enablement note and render as an inert code block until Dataview is on.

### What was built

**Workshop** (`G:\我的雲端硬碟\2026 Life OS\`)

| File | Holds |
|---|---|
| `CLAUDE.md` | project brief, the GTD×JEV layer table, 9 invariants |
| `AGENTS.md` | the same, condensed, for non-Claude agents |
| `UNKNOWNS.md` | four quadrants; 7 named known-unknowns with what each would change |
| `lifeos/config.py` | SSOT parser — a narrow YAML subset, stdlib only, raises rather than guess |
| `lifeos/metrics.py` | [C] means that carry their denominator, streaks, deltas |
| `lifeos/unlock.py` | [C] the 30-day gate |
| `lifeos/gtd.py` | [D] clarify/organize, hard rules first, then the confidence gate |
| `lifeos/vault.py` | append-only writes with a subsequence superset check |
| `lifeos/jev_stub.py` | deterministic stub, deliberately low confidence |
| `eval/test_smoke.py` | 47 behavioural checks, no key, no network |
| `scripts/deploy.sh` | one-way idempotent deploy, refuses protected folders |
| `scripts/checks.sh` | the objective evidence |

**Vault layer** (`Second Brain\Life OS\`, 15 notes + 1 script)

`Meta/Compass Config.md` (SSOT), `00 開始這裡.md` (onboarding), `AGENTS.md` (vault agent rules),
`Dashboards/` ×3, `Prompts/` ×3, `GTD/` ×4, `Retreats/`, `scripts/nightly.js`, plus
`Templates/每日筆記 Life OS.md` deployed into the vault's own `Templates/`.

### Verified

- `python eval/test_smoke.py` → **47/47 pass**
- `bash scripts/checks.sh` → all checks pass
- SSOT parses: 4 dq questions, 2 habits, 8 wheel areas, `clinical_access: never`
- Python 3.9.12; `lifeos/` imports nothing outside the stdlib
- Deploy verified idempotent; protected folders untouched
- One real bug found and fixed by the suite: `append_under_heading` treated a whitespace-only
  block as content, which would have stamped a blank bullet into the journal on a night the
  user skipped the reflection.

### Not verified — the honest list

- **`nightly.js` has never run inside Obsidian.** Its QuickAdd API surface
  (`inputPrompt`, `wideInputPrompt`, `yesNoPrompt`, `params.obsidian.Notice`) is taken from
  third-hand notes. Every call is feature-detected and there is a fallback write path, but one
  real run is what settles this. **This is the single highest-value next action.**
- **The Compass repo was never fetched.** All Compass knowledge is from three AI-generated
  Chinese analysis notes whose own citations `[1]`–`[25]` are absent. Never say "Compass does X".
- No threshold has been tuned against real traffic. `AUTO_FILE_CONFIDENCE = 0.75` is a placeholder.
- The decision layer has never been called. `TYPESAFE_API_KEY` is not set.

### Next session should

1. **Ask the user to run `Ctrl+Shift+Q` once** and report what happened — resolves UNKNOWNS U2.
2. **Get an explicit answer on clinical data (U4)** before any feature reads `## 🏥 臨床`.
   Currently blocked in code and in both `AGENTS.md` files.
3. Fetch `github.com/AgriciDaniel/compass` and diff against `vault-src/` — resolves U1.
4. **Known gap:** `gtd.organize()` routes notes to `知識庫/` but does not update
   `知識庫/index.md` or `log.md`, which the vault's own `CLAUDE.md` requires. The decision
   currently carries a reason string saying so. Automate it or keep surfacing it.
5. At day 30 (2026-10-28), ask whether the nightly 30 seconds actually fits — do not assume
   the tooling fix was sufficient.

### Deliberately not done

- No `.claude/hooks/` wiring. The JEV repo learned that hooks without a key produce a
  permission prompt on every call, which is a broken install rather than a safe one. Nothing
  here needs a hook yet.
- No reverse sync from vault to `vault-src/`. One-way is auditable; two-way is not.
- No outcome metrics in the daily loop. Effort-only framing is the Goodhart mitigation.
