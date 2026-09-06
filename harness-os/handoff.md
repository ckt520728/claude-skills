# Handoff — Harness OS build

**Date:** 2026-09-06 (v2.1.0); base build 2026-09-02
**Workspace:** `D:\2026 Claude Harness OS_General Purpose`
**Status:** v2.1.0 complete, self-tested (kernel 42/42, verifiers 72/72), and **merged to `ckt520728/claude-skills` master** — squash-merged 2026-09-06 via [PR #4](https://github.com/ckt520728/claude-skills/pull/4), master commit `e41f40c`; branch `harness-os-v2.1.0` deleted. `master`'s `harness-os/.claude-plugin/plugin.json` now reads `2.1.0` (verified on GitHub). The v2.0.0 base was merged earlier (commit `37ffa4f`, PR #3, 2026-09-02). Nothing in flight.

## v2.1.0 — frontier-benchmark upgrade (2026-09-06)

**Goal:** use core concepts from the 2026 frontier-benchmark / Codex material
(`E:\...\ChatGPT_Work_Code\` — two zh-TW survey notes + `harness_agent_plugin.py`
/ `-v2.py`) to upgrade the Harness OS. Three general mechanisms added to the
kernel, each grounded both in those notes (framing) and in the already-verified
`Reference/` corpus (licence to build). Two mechanisms deliberately declined.

| Added | What it is | Kernel surface | Source |
|---|---|---|---|
| `constraint` | Invariant rules that survive context compaction; surfaced verbatim by `status`, never pruned. Distinct from the learned/prunable playbook. | `constraint add --text …` / `constraint list`; `state/constraints.json` | Codex invariant prefix + AgencyBench/OSWorld (notes); ACE context-collapse + Meta-Harness (corpus) |
| `challenge:` | Contract check with a fresh random nonce (`$HARNESS_CHALLENGE`) each run; passes only if the verifier echoes it live → defeats hardcoded answers. | new check kind in `_run_check`; verifier `check_challenge_response.py` | ExploitBench oracle (notes); STOP sandbox-bypass + existing anti-gaming section (corpus) |
| `ladder` | Graded progress meter — highest contiguous tier passed. A meter, **not** a gate; promotion still runs through held-in/held-out `gate`. | `ladder set/assert`; `state/ladders/`, `eval/ladder_*.json` | ExploitBench 16-tier (notes); Self-Harness dense signal (corpus) |

**Declined (recorded, not dropped):** ScreenSeekeR cascaded pixel-grounding
(GUI-specific; kernel owns files not pixels) and recurrent-depth/latent-reasoning
(model architecture; its one harness lesson *reinforces* the existing on-disk
trace). Both in `evidence-ledger.md` "Deliberately excluded" and
`prototype-delta.md` "The second (ChatGPT/Codex) prototype".

**Files touched (all local):** `harness_kernel.py` (v2.0.0→2.1.0, +11 selftest
checks), `verifiers/check_challenge_response.py` (new) + `test_verifiers.py` (+8
checks), skills `harness-os` / `harness-boot` / `harness-evolve`,
`references/evidence-ledger.md` + `prototype-delta.md`, `README.md`,
`USER_MANUAL.md`, `.claude-plugin/plugin.json`, `verifiers/README.md`, this file,
and `CLAUDE.md` check counts.

**Honesty note carried in the ledger:** the frontier *benchmark papers* (OSWorld
2.0, ExploitBench, ScreenSpot-Pro, Codex arch) are **not** in `Reference/` and
were **not** read in full — their quoted statistics are marked unverified. What
was adopted is the design pattern, which the corpus independently supports.

**Published & merged:** PR #4 squash-merged to master (`e41f40c`), branch
deleted. Only the real content changes went in (git `core.autocrlf=true`
normalised line endings, so the diff was 12 files / 621+ / 25−, no CRLF churn).

**Follow-up doc commits (direct to master, doc-only):**

| Commit | What |
|---|---|
| `1b70136` | `README.md` — added a `## Changelog` section (v2.1.0 + v2.0.0) |
| `15b2fb3` | `USER_MANUAL.md` — fixed a stale count (延伸閱讀: 八個→九個 verifiers) and added a `## 版本` footer mirroring the README changelog |
| `236004a` | `USER_MANUAL.md` — added a runnable worked `challenge:` example (honest artifact passes a fresh nonce; hardcoded version fails only that check; how to map sha256 → a real deliverable via `--algo` / `--expect-cmd`) |

master HEAD is `236004a`. These were committed directly to master (not via PR)
because they are doc-only and record an already-merged release; the working copy
on `D:\` is kept in sync with each. If doc changes should also go via PR in
future, say so.

---

## v2.0.0 base build

**Date:** 2026-09-02
**Status:** v2.0.0 complete, self-tested, and merged to `ckt520728/claude-skills` master (commit `37ffa4f`, PR #3, 2026-09-02).

## What was asked

Per `2026 Agentic Harness OS skill.txt`:

1. Analyse the papers in `Reference/`, the Gemini prototype notes, and the
   prototype code, using the `academic-paper-deep-analysis` framework.
2. Extract the core mechanisms into a **reusable, general-purpose orchestration
   skill** for an Agentic Harness OS, applicable to six domains: web systems,
   research proposals, signal-analysis methods (EEG/HRV), literature corpora,
   academic writing, and portable clinical apps.
3. `/init` — CLAUDE.md referencing `/grill-with-docs` and the
   `Thariq_finding_unknown` skills, plus this handoff.

## What was built

| Artifact | Path |
|---|---|
| Corpus deep analysis (7 layers, zh-TW) | `analysis/harness-corpus-deep-analysis.md` |
| Orchestrator skill | `harness-os/skills/harness-os/SKILL.md` |
| Phase skills | `harness-os/skills/harness-{boot,fork,assert,mine,evolve}/SKILL.md` |
| Kernel (stdlib, Py3.8+, cross-platform) | `harness-os/scripts/harness_kernel.py` |
| Domain profiles (6) | `harness-os/profiles/*.md` |
| Evidence ledger | `harness-os/references/evidence-ledger.md` |
| Prototype delta | `harness-os/references/prototype-delta.md` |
| Profile verifiers (8) + test suite | `harness-os/scripts/verifiers/` |
| User manual (zh-TW) | `harness-os/USER_MANUAL.md` |
| Build retrospective / pitfalls | `analysis/build-retrospective-pitfalls.md` |
| Plugin manifest | `harness-os/.claude-plugin/plugin.json` |
| Project guidance | `CLAUDE.md` |

The six skills are also installed to `~/.claude/skills/`, so `/harness-os` works
in any project. The plugin is published at
<https://github.com/ckt520728/claude-skills> under `harness-os/`.

**Verification:** both suites must pass; run them first in any new session.

```bash
python harness-os/scripts/harness_kernel.py selftest      # 31/31 PASS
python harness-os/scripts/verifiers/test_verifiers.py     # 64/64 PASS
```

Verified from a clean clone of `master` after the merge.

## Decisions worth knowing

**Packaging.** Plugin-shaped skill pack + global install, chosen by the user.
Skills are progressive-disclosure: the orchestrator is read first, phase skills
only when in that phase.

**Language.** English skill instructions (long-horizon instruction-following),
Traditional Chinese user-facing output. Analysis report in zh-TW per the
`academic-paper-deep-analysis` convention.

**The kernel is not an LLM.** It is a deterministic control plane the agent
drives via Bash. Judgement stays with the model; facts that cannot be talked
around stay with the kernel. That separation is the whole design.

**Corpus provenance.** The fourteen papers are the reference list of Lilian
Weng, "Harness Engineering for Self-Improvement" (2026-07-04),
<https://lilianweng.github.io/posts/2026-07-04-harness/> — which is also the
framing source: the OS analogy and the "near-term RSI runs through the harness,
not the weights" thesis are both hers.

**Two claims in the Gemini notes did not survive checking** against the PDFs;
both would have produced a worse design. Documented in `evidence-ledger.md`.
Most importantly, the notes had the model-tier finding backwards (benefit is
non-monotonic, peaking at mid-tier; the notes said a top-tier model was
required), and omitted AHE's ablation result, which is the most actionable
finding in the corpus: gains come from tools, middleware and memory, **not** the
system prompt.

A third item was flagged as unverified in the first pass and was **wrong to
flag**: the notes' attribution of the framing to Lilian Weng is correct. The
reasoning behind the flag ("not in `Reference/`, not cited by any of the
fourteen PDFs") was structurally impossible to satisfy — the post is the source
of that folder, and papers predating it cannot cite it. Corrected in all four
places, with the lesson recorded: check whether your evidence source *could*
contain the thing you are checking before calling something unverified.

**Seven prototype defects were blocking**, not cosmetic — chief among them that
`spawn_job` used `subprocess.run`, so the "parallel dispatch" feature the whole
architecture rests on did not actually exist. Full list in
`prototype-delta.md`.

## Found and fixed during verification

Two defects surfaced only when the CLI was driven for real, not by the API-level
selftest:

1. **`fork` was a silent no-op via the CLI.** The subparser used `dest="cmd"`
   and the `fork` subcommand defines `--cmd`, so argparse overwrote the
   subcommand name with the command string; dispatch fell through every branch
   and exited 0. Fixed by renaming the dest to `subcommand`. The selftest now
   drives the CLI as well as the API, including a check that no declared
   subcommand silently produces no output — 24 checks became 31.
2. **The documented shell idiom broke on paths with spaces.** `K="python
   /path/…"` then bare `$K` word-splits, which this project's own path triggers.
   The skills and README now use `KP="…"` plus `python "$KP"`.

Worth remembering as a pattern: a green API-level test suite over an untested
interface layer is exactly the false-completion failure this whole project is
built to catch. It was caught here by running the thing, not by reading it.

## Suggested skills for the next session

- `/harness-os` — to actually use the thing on a real deliverable. Start with
  contracts + `assert` + `publish` only; add fork/mine/evolve when needed.
- `/grill-with-docs` — before adding any new kernel subsystem or profile.
- `/blindspot-pass` — before touching the evolve loop specifically.
- `/verify-with-rubric` — with a fresh, non-`fork` sub-agent, if evaluating the
  skill pack's quality.
- `academic-paper-deep-analysis` — for any individual paper needing depth beyond
  the corpus-level report.

## Suggested next steps

Roughly in order of value:

1. **Use it on one real task end to end.** The `research-proposal` or
   `literature-corpus` profile against actual material. Everything here is
   designed from evidence but only selftested — a real run is what will surface
   the gap between the design and the work.
2. ~~Write the profile helper scripts.~~ **Done.** Eight verifiers ship in
   `harness-os/scripts/verifiers/` with a 64-check test suite; every profile
   contract now points at them. Adding one means adding both a must-fail and
   a must-pass case in the same change.
3. **Feed real failures back.** After a run, `mine` the trace and see whether the
   signature taxonomy in the profiles matches what actually goes wrong. The
   mechanism labels are informed guesses until a real corpus of failures exists.
4. **Consider a `harness-resume` skill.** Resuming from `$K status` is currently
   a paragraph inside `harness-boot`; it may deserve its own entry point given
   how often long work spans sessions.

## Open questions for the user

- The six profiles were derived from the goal statement. Are the deliverable
  lists and section names right for your actual NSTC template and your clinic's
  cognitive-test workflow? These are the parts most likely to need your specific
  knowledge rather than a reasonable default.
- ~~Obsidian save?~~ **Done (2026-09-02).** Saved to
  `G:\我的雲端硬碟\Second Brain\知識庫\2026 Claude code\2026-Harness-Engineering-corpus-deep-analysis.md`,
  with a provenance header matching the vault's existing deep-analysis notes, and
  a row added to `知識庫\index.md` (its 最後更新 date bumped to 2026-09-02). The
  working copy in `analysis/` remains the source of truth; the vault copy has
  relative paths rewritten to absolute.

## Environment notes

- Long heredocs fail here (`ENAMETOOLONG`; multi-file heredocs break the shell
  wrapper). Use the Write tool for substantial files.
- `pdftotext` cannot open the DGM PDF — `Ö` in the filename. Use `pypdf`.
  Extracted text from all 14 papers was written to the session scratchpad and is
  gone; re-extract if needed.
- Python 3.9.12, `pypdf` available, `pdftotext` on PATH.
