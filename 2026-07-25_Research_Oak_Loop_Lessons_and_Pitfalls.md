# Wrap-Up — Brain-Oscillations Review, Session 1 (2026-07-25)

Retrospective of the first end-to-end run of the workflow: *empty folder → scoped
research program → three independently-verified synthesis notes → a drafted lab blog*, run
as an Oak loop. Pairs with `handoff.md` (state) and `STATE/option-ledger.md` (calibration).
The reusable distillation of this run is the plugin in `plugin/research-oak-loop/`.

## What got built
- Scaffold + governance: `CLAUDE.md`, `docs/glossary.md`, `docs/ADR/ADR-000{1,2}`.
- Finding-unknown discovery: `research/00`–`03` + `deviation-log.md`.
- Oak loop: `STATE/option-ledger.md` (Feature → SubTask → Option `distil-cluster` → Model →
  Planning), maker/checker gates, Brier calibration.
- 3 verified synthesis notes: `synthesis/temporal-attention.md`, `working-memory.md`,
  `temporal-binding.md` (all independently checker-confirmed).
- L3 output: `synthesis/blog/neural-oscillations-cognition.html` (drafted, **not** published).

## Outcome that matters most
The maker/checker split **caught a real error on every trial** the maker's own self-check had
passed. The independent decoupled verifier is not optional theatre — it is where the actual
defense against a wrong synthesis lives.

---

## Pitfalls encountered (and the rule each one earned)

### Scoping & discovery
1. **Ambiguous multi-goal folder.** The name mixed "PKM + oak-loop + a research question."
   *Rule:* resolve the load-bearing calls (scope / output / method-role) by grilling
   **before** building — never guess architecture. → ADRs.
2. **A "relevant" existing note was a different cluster.** `_Distilled/AD_rhythmic_attention`
   looked reusable but covered spatial-attention (Fiebelkorn), not the temporal-attention
   corpus. *Rule:* verify what an existing note actually covers before assuming reuse or
   duplication.

### Source handling
3. **PDFs don't render.** `Read` can't open PDFs here — use **PyMuPDF**; for non-ASCII / spaced
   filenames, `glob` inside Python rather than shell globbing. *Signal:* a thin extract
   (e.g. 15 kB from 56 pages) means image-heavy or a slide deck, not a paper.
4. **Source-quality trap.** A file named like a paper (`20260223_sifi_…pdf`) was an
   **unpublished student slide deck** (Chou; advisor Prof. Juan). *Rule:* apply a
   source-quality gate — never cite non-peer-reviewed material as evidence; teaching context
   only.
5. **Paper-identity conflation.** Two same-author/same-year files in one folder (Daume 2017
   *visual* vs *audiovisual*; several Hirst 2020/2022). *Rule:* confirm each cited filename's
   **actual title** before citing. (Trial-2 failure mode → Option policy v1.1.)

### Accuracy & citations
6. **Numeric misread at abstract level.** "8-year" vs the source's "10-year" trajectory,
   repeated 4× (trial-3 R3 failure). *Rule:* verify **every quantitative claim against
   full-text methods**, not just the abstract, before the checker. (→ Option policy v1.1.)
6b. **Citation fabrication.** Trial 4 (encoding) *invented a coauthor* ("Wang") and put the
   paper in the wrong journal (*Neuron* vs the actual *Current Biology*) — and the maker's own
   self-check marked "paper-identity ✅". 2 of 4 trials had a self-check-green citation failure.
   *Rule:* never render a citation from memory — **copy author list + journal + year verbatim
   from the PDF's title page**; treat citation self-checks as untrusted. (→ Option policy v1.2;
   plugin pitfalls §6b.) *This is the strongest evidence in the run that the decoupled checker
   is load-bearing, not optional.*
7. **Journal misattribution.** Hirst 2022 is *Aging Brain* (2:100038), not *Cognition* —
   caught only at citation-verify. *Rule:* verify journal + DOI + year against a primary
   source before anything goes on a public page (publish-lab-blog P14).
8. **Pseudo-quote.** "remains equivocal" was set in quotation marks but was a paraphrase, not
   verbatim (trial-1 fix). *Rule:* quotation marks = verbatim only; paraphrase otherwise.

### Oak-loop integrity
9. **Self-promotion temptation.** Trial 3 was accepted-with-fixes, but it had a genuine
   rubric failure. Scoring it a "pass" to hit the promotion gate would be the
   *maker-approves-own-Option* antipattern. *Rule:* a rubric failure is **not** a clean pass;
   score honestly (y=0), let mean Brier reflect it (0.235 > 0.15 bar → promotion **blocked**),
   and never let the maker promote its own Option.
10. **Independent verification is non-negotiable.** Every self-check "passed"; the decoupled
    checker still found a real defect each time. *Rule:* verifier must be a **fresh, non-fork**
    sub-agent that re-extracts sources — a fork inherits the maker's bias.
11. **Unresolved ≠ pass.** Before a checker runs, an outcome is *unknown*, not a success —
    record it as unresolved, no Brier update, no promotion credit.

### Process & environment
12. **Background-agent discipline.** Don't read the verifier's transcript file directly
    (context overflow); wait for the completion notification; don't predict its result.
13. **Human gates are absolute.** Publishing (git push), writing to the source library, and
    submitting a manuscript are hard human gates — draft up to the line, then stop.
14. **Windows/env specifics.** Push via **PowerShell**, not Git Bash (credential-manager);
    watch en-dashes in filenames; `~` = `C:\Users\YangminRoom1`.

## Calibration snapshot (from `STATE/option-ledger.md`)
| Trial | Cluster | Predicted p | Outcome | Brier |
|---|---|---|---|---|
| 1 | temporal-attention | 0.60 | clean pass | 0.160 |
| 2 | working-memory | 0.65 | clean pass | 0.123 |
| 3 | temporal-binding | 0.65 | **fail (R3 numeric)** | 0.423 |
| | | | **mean** | **0.235 → L2 promotion blocked** |

## Still open
- `distil-cluster` L1→L2 promotion (needs mean Brier ≤ 0.15; ~2–3 more clean trials).
- OQ2 (computational-modeling depth), OQ3 (AD case = section vs companion), §1.5 (blog
  audience; manuscript = review vs perspective).
- Blog: human review → publish pipeline (Steps 2, 4–6) → then manuscript escalation.
- Pre-push: spot-check the two "generation" DOIs (Buzsáki & Wang 2012; Sohal 2009).
