# UNKNOWNS

Four quadrants, per `map-vs-territory`. The point of this file is that the map in `CLAUDE.md`
is not the territory, and this is the list of places they are known to diverge.

Every entry says **what it would change**. An unknown that changes nothing is trivia.

Last surveyed: **2026-09-30** (session 5: jev skill actually used; Compass structure adopted).

---

## 1. Known knowns — verified on this machine, this session

These were checked, not assumed. Each names how it was checked so the next session can re-check.

| Fact | How verified | Consequence |
|---|---|---|
| Vault is `G:\我的雲端硬碟\Second Brain` | `obsidian.json` lists it with `"open": true`; user confirmed in-session | All deploys target it |
| 694 markdown notes, excluding `.obsidian/` | `find -name "*.md" \| wc -l` | Dataview scans stay fast; the >5k slowdown is far off |
| Structure: `Clippings/` `知識庫/` `創作庫/` `每日筆記/` `Templates/` | `ls` of vault root | Life OS adds one root folder, does not restructure |
| Vault `CLAUDE.md` mandates 繁體中文 + three-layer PKM | read the file | Content language decided; not ours to overrule |
| Python 3.9.12 | `python --version` | No `X \| Y` unions, no `match` in `lifeos/` |
| `TYPESAFE_API_KEY` is **not set** | `${TYPESAFE_API_KEY:+YES}` returned NO | Decision layer ships stub-backed and inert |
| MCP server `obsidian` → `mcpvault.cmd` at Second Brain | `~/.claude/settings.json` | Agent can read/write the vault already |
| **Only 5 plugins enabled**: `local-rest-api`, `quickadd`, `calendar`, `omnisearch`, `make-md` | `.obsidian/community-plugins.json` | **Design constraint #1**, see below |
| **Dataview installed but NOT enabled** | present in `plugins/`, absent from `community-plugins.json` | Every dashboard must degrade gracefully |
| **Templater NOT installed at all** | no `plugins/*templater*` directory | Existing templates cannot expand |
| `Tasks` plugin not installed | same check | GTD cannot rely on `Tasks` query syntax |
| `每日筆記/` holds exactly **one** note, `2026-05-09.md` | `ls` + `find` | **Design constraint #2**, see below |
| `Templates/每日筆記.md` uses `<% tp.date.now() %>` | read the file | It is Templater syntax with no Templater → dead template |
| Existing daily note shape: `## 🏥 臨床` / `## 💡 今日反思` / `## 明日優先事項` | read `2026-05-09.md` | Extend this shape; do not replace it |
| `Thariq_finding_unknown` seven skills installed under `~/.claude/skills/` | `ls` | `/finding unknown` resolves to them |
| `grill-with-docs` = `/grilling` + `/domain-modeling` | read its `SKILL.md` | Both available; `/grill-with-doc` singular does not exist |

### The two design constraints those facts produce

**Constraint 1 — the day-1 loop must need zero new plugins.**
QuickAdd is enabled. Its user-script API plus Obsidian's native `app.fileManager.processFrontMatter`
can collect scores and write frontmatter with no Dataview and no Templater. So nightly scoring
works today. Dataview (one toggle) and Templater (an install) are *upgrades*, each gated behind
its own note, never prerequisites for the habit.

**Constraint 2 — this is habit *formation*, not habit *support*.**
One daily note in five months, and a template that could never expand, is not a discipline
problem — it is a broken tool. The system is therefore designed so the first 30 days ask for
about 30 seconds a night via one hotkey, and the dashboard's job is to make the streak visible.
Any change that adds friction to the nightly path is a regression, however much capability it adds.

---

## 2. Known unknowns — named, unresolved, with the cost of being wrong

### U1. ~~The Compass reference material is third-hand~~ — **RESOLVED 2026-09-29**

The repo was fetched. Full comparison in `references/compass-upstream.md`.

**Confirmed** — `Meta/Compass Config.md` is the real SSOT filename; `dq_*` / `habit_*` / `wheel_*`
prefixes; `AGENTS.md` with read-before-write and ask-before-edit; 16 prompts in `Prompts/`; Local
REST API MCP bridge at `127.0.0.1:27123` exposing 16 tools; `00 Dashboards/` `01 Journal/`
`02 Retreats/` numbering; `life-os-app` first-party plugin; Goldsmith/Reiter *Triggers* as the
source of the effort-framed daily questions; build scripts that verify JS syntax and size.

**Contradicted** — five claims this repo had stated as fact:

1. Config uses `questions:` / `key:` / `text:`, **not** `dq_questions:` / `id:` / `prompt:`.
2. `habits:` and `wheel_areas:` are **flat string lists**, not mappings.
3. **11** required plugins, not 10, and the list differs.
4. The thesis is **Mike Schmitz's** system; Agrici built the template. The notes credited Agrici.
5. **There is no 30-day layering rule in the repo.** This one matters most — the unlock gate in
   `lifeos/unlock.py` was justified by citing Compass. The gate is still correct for this vault,
   but on local evidence (one daily note since 2026-05-09, against a template that could never
   expand), not borrowed authority. Corrected in `CLAUDE.md`, `README.md`, `Compass Config.md`.

**Acted on** — `lifeos/config.py` now parses upstream's schema as well as this repo's, pinned by
8 tests against the verbatim upstream file. `birthdate` / `life_expectancy` (the `memento` feature)
adopted. Upstream's data-not-instruction rule adopted into both `AGENTS.md` files.

**Still open** — upstream `AGENTS.md` could not be retrieved verbatim (the fetch returned a
summary and declined full reproduction), so rule *wording* remains second-hand though the rule
*set* is confirmed. The contents of `Meta/views/*.js` and the `life-os-app` plugin were not read.

### U2. The QuickAdd script API surface is unverified
The nightly script uses `quickAddApi.inputPrompt`, `quickAddApi.wideInputPrompt`, and the `params`
object shape, all taken from U1's notes. QuickAdd's actual current API may differ.
- **Would change:** whether `nightly.js` runs at all. It is the one piece the day-1 loop depends on.
- **Resolve by:** running it once in Obsidian and reading the console. This has **not** been done —
  it cannot be, from here.
- **Found 2026-09-30 — the real reason it never ran:** `.obsidian/plugins/quickadd/data.json` has
  **zero choices**. No macro was ever created, so `Ctrl+Shift+Q` was bound to nothing. Sessions
  1–4 kept asking the user to "run Ctrl+Shift+Q once" without checking this. The manual's
  chapter 1 and `00 Dashboards/設定清單.md` now walk through creating both macros
  (`Life OS 夜間評分` → nightly.js, `Life OS 收件` → capture.js). Same unverified API applies to
  `capture.js` (`suggester`, `inputPrompt`, `app.vault.process`).
- **Mitigation taken:** the script feature-detects each API it calls and shows a `Notice` naming
  the missing method rather than throwing. It also writes a fallback plain-markdown block if
  `processFrontMatter` is unavailable, so a failed run still records the night's data somewhere.

### U3. No threshold tuned against real traffic — **mechanism built 2026-09-29, data still absent**

`AUTO_FILE_CONFIDENCE = 0.75` is still a guess. What changed is that the system can now *find
out* instead of needing someone to run a manual sweep.

`jev.calibration` (the skill's; formerly the private `lifeos/calibrate.py`) bins raw scores against observed accuracy on the user's own resolved
decisions. A bin below `MIN_OBSERVATIONS` (12) reports `COLD_CONFIDENCE` (0.30), under every
gate, so the layer asks. Every ask the user resolves is a label, fed back via
`gtd.record_outcome()`. The shadow period is no longer a phase to remember — it is the
operating mode, and bands unlock one at a time as they earn it.

- **Still unknown:** the real accuracy of the `local` provider over `gtd.py`'s criteria text on this user's actual captures.
  A demo on 5 repeated captures scored 5/5 and proves nothing — the same person wrote the
  captures and the lexicon.
- **Would change:** whether the GTD flow ever reaches `AUTO` at all. If real accuracy in the
  high bands sits below 0.75, nothing ever auto-files — which is the correct outcome, not a bug.
- **Resolve by:** using it, then reading `cal.reliability("bucket")` and the ECE.
- **Sharp edge:** ECE also penalises *under*-confidence. A layer reporting 0.30 while being
  right every time scores badly and is perfectly safe. Read the reliability table, not ECE alone.

### U3b. The criteria text in `gtd.py` was written blind
Since 2026-09-30 there is no separate lexicon: the jev `local` provider scores a capture against
each option's own criteria text (skill rule 1), so the bilingual verb/noun lists in `BUCKET`,
`FOLDER`, `URGENCY`, `ENERGY`, `ACTIONABLE` and the `criteria:` of each wheel area in Compass
Config *are* the vocabulary. All written without sight of a real capture.
- **Known weakness, observed:** area classification leans on single characters — "張醫師" pulls
  toward `wheel_health` via 醫. Calibration makes this safe (it asks), not accurate.
- **Would change:** how many adjudications before any band warms.
- **Resolve by:** 20–30 real captures through `scripts/triage.py`, then edit criteria text where
  `--report` shows agreement below ~70%. Never lower a threshold to compensate.

### U8. The Obsidian-side layer has never rendered in the real app
Twelve Dataview views, five templates filled by `quicklinks.js`, and Dataview task queries
(standing in for the Tasks plugin) all pass `node --check` and nothing more.
- **Would change:** whether the dashboards show anything. Likeliest failure points: `dv.view()`
  nested inside `gate.js`; Dataview's parsing of `⏫` / `➕` emoji; `t.section.subpath` for the
  inbox filter; `app.vault.process` availability.
- **Resolve by:** enable Dataview, open `指南針儀表板`, read the console.

### U9. Decision recorded 2026-09-30: adopt upstream's Build Order over session 1's schedule
Session 1's 1/31/91 schedule came from third-hand notes. Upstream's real one is 1/31/61/91/121
with an 80% consistency rule, and the user asked for a Compass-like system, so it replaces it.
Consequence: GTD **filing** moved from day 31 to day 91 (upstream's Tasks layer). Shadow-mode
labelling still runs from day 1, so the layer trains through all three months. Capture is never
gated. Legacy `daily/weekly/quarterly` keys still parse.

### U4. ~~Whether the user wants clinical content inside the scoring loop~~ — **RESOLVED 2026-09-29**

The user activated the clinical section at level **`derived`**, choosing it over local-only and
over full-text access.

**What that means in practice:** code reads `## 🏥 臨床` on the user's own machine and derives
numeric facts (`clinical_pending`, `clinical_load`). Those numbers may enter a coaching prompt.
The raw case text may not — not in a prompt, not in a log line, not in an error message.

**How it is enforced.** Not by instruction. `lifeos/clinical.py` defines `ClinicalDigest` with
fixed `__slots__` holding numbers only, and `as_dict()` runs `assert_transmittable()` before
returning. The derivation happens inside Obsidian in `nightly.js`, which writes only the two
scalars into frontmatter; the coach reads frontmatter and has no reason to open the body.
`eval/test_smoke.py` builds a digest from realistic clinical text and asserts that none of 12
distinctive tokens appears in the transmittable output. `scripts/checks.sh` repeats that
assertion, so a regression fails the build.

**What remains open, and is now the live question:**
- Counting bullets is a *proxy* for workload. If the user keeps cases in prose rather than as a
  bullet list, `clinical_pending` silently reads 0 and the coach is quietly wrong. Worth checking
  against a real week of notes.
- `clinical_load` bands (`LOAD_THRESHOLDS` in `clinical.py`) are untuned guesses. 6 cases being
  "band 4 of 5" is not grounded in anything.
- Widening to `full` would put patient-adjacent text into a third-party model context on every
  coaching call. That is a separate decision with a different risk profile, and the code
  deliberately still does not return raw text even at `full` — a second, explicit change would
  be required.

### U5. ~~Chart.js availability for the wheel-of-life radar~~ — **MOOT 2026-09-30**: upstream `wheel.js` draws pure SVG; ported as is
The reference radar script pulls Chart.js from a CDN inside a DataviewJS block. The notes flag
this themselves as a failure mode with no network.
- **Would change:** whether the quarterly radar renders. Quarterly is dormant until day 91, so
  this is not urgent.
- **Mitigation taken:** the retreat dashboard ships a pure-markdown horizontal bar fallback that
  needs no Chart.js and no network, and the radar is an enhancement layered above it.

### U6. Google Drive sync vs. concurrent writes
Both the vault and this workshop sit under `G:\我的雲端硬碟\` — Google Drive. The reference notes
name concurrent-write conflicts as a real risk when an agent writes while a sync runs.
- **Would change:** whether append-only is sufficient protection. Append-only survives a lost
  update far better than a rewrite, but a Drive conflict copy could still appear.
- **Resolve by:** watching for `...(1).md` conflict files during the first weeks.
- **Mitigation taken:** append-only everywhere (invariant 2), and `deploy.sh` never writes a file
  whose content it has not first read.

### U7. Whether `每日筆記/` or `Life OS/` should own the daily note long-term
Chosen: `每日筆記/`, because the user's notes already live there and the calendar plugin points at it.
- **Would change:** every path in `nightly.js` and every dashboard query.
- **Cost of the choice:** Life OS scoring data is now interleaved with clinical notes in one file,
  which is exactly why U4 needs an explicit answer.

---

## 3. Unknown knowns — what the vault already knows that the design must respect

Things true of the user's existing setup that a fresh design would have quietly broken.

- **The vault map file (`第二大腦地圖.md`) states a root-minimalism principle.** Honoured: one new
  root folder, not five. A future session adding `00 Dashboards/` at root would violate a rule the
  user wrote down and would not find it stated in `CLAUDE.md` alone.
- **`知識庫/` maintains `index.md` and `log.md`, and the vault `CLAUDE.md` requires updating both
  on every addition.** Any GTD "organize" step that files a note into `知識庫/` inherits that duty.
  Currently the GTD flow routes to `知識庫/` but does **not** yet update `index.md` — a known gap,
  listed in HANDOFFS as the first thing to fix.
- **`Clippings/` is declared immutable** ("這些是原始資料，不要修改"). The GTD flow may read and
  link Clippings, never edit them.
- **The user's own vocabulary is 繁體中文 with English technical terms** — visible in `2026-05-09.md`,
  which mixes 踩坑/啟示 with `soil-image-deck`. Content matches that register rather than either extreme.
- **`obsidian-git` is installed but disabled.** If the user enables it, the vault gains real version
  history, which materially weakens the append-only argument's urgency — and would make a
  reverse-sync from vault to `vault-src/` safe to build. Worth revisiting then.

---

## 4. Unknown unknowns — where surprises are most likely

Not predictions. Places to look first when something breaks.

1. **QuickAdd's macro/user-script configuration is manual GUI work.** Nothing in this repo can
   verify the user wired the macro correctly. The most likely failure of the whole project is a
   hotkey that does nothing and no error message. The onboarding note therefore ends with a
   *verification* step that produces visible output, not a "you're done".
2. **The 4½-month gap may not be a tooling problem.** Constraint 2 assumes the dead template caused
   the dead habit. It may be that nightly journaling simply lost to clinical workload — in which
   case 30 seconds is still too long and the honest fix is fewer questions, not better tooling.
   The day-30 review should ask this directly rather than assuming success.
3. **`make-md` (Spaces) is enabled and rewrites folder metadata** — there are `.space` directories
   inside `每日筆記/`. It may present, reorder, or wrap the new `Life OS/` folder in ways nothing
   here anticipates.
4. **Scoring may change the thing it measures.** Goodhart's Law is named in `CLAUDE.md` as a
   failure mode; effort-not-outcome framing is a mitigation, not a cure. If scores drift upward
   while life does not improve, the instrument is being gamed and the questions need rewriting.
5. **`datacore` is installed** — a Dataview successor with different syntax. If the user enables
   it instead of Dataview, every dashboard query needs porting.

---

## 5. What would make this repo trustworthy

In priority order. Nothing below is done.

1. Fetch the real Compass repo and resolve **U1**. Until then every Compass claim is hearsay.
2. Run `nightly.js` once in Obsidian and resolve **U2**. One run settles the day-1 risk entirely.
3. Get an explicit answer on clinical data, **U4**, before any feature reads `## 🏥 臨床`.
4. Shadow the decision layer for two weeks before trusting any threshold, **U3**.
5. Ask at day 30 whether the nightly loop actually fits the user's life, per unknown-unknown 2.
