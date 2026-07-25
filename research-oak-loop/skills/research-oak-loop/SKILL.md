---
name: research-oak-loop
description: >
  Reusable pipeline for turning a literature corpus (a folder of PDFs / notes) into an
  independently-verified research synthesis and a staged blog→manuscript output, run as a
  continually-improving Oak loop. Use when starting a research-program workspace from a
  knowledge base, when distilling clusters of papers into notes that must survive
  adversarial checking, or when the user asks to "run the research-oak-loop" / "distil this
  corpus" / "synthesize and verify these papers". Orchestrates finding-unknown discovery,
  pkm-three-levels distillation, oak-loop-engineering, verify-with-rubric, and
  publish-lab-blog — with hardening rules from real runs baked in.
user_invocable: true
---

# Research Oak Loop

Corpus → verified synthesis → shipped output, as an *improving loop* rather than a static
pipeline. Each synthesis move (distil a cluster, verify a claim) is a Feature → SubTask →
Option → Model → Planning row whose predictions are checked against an **independent** checker
and recorded, so later passes get cheaper and better-calibrated.

This skill composes other skills; it does not replace them. Before running, confirm these are
available and say which are missing: `map-vs-territory` / `blindspot-pass` /
`decision-first-plan` / `reference-anchor` / `deviation-log` (finding-unknown set),
`grilling` + `domain-modeling` (for ADRs/glossary), `pkm-three-levels`,
`oak-loop-engineering`, `verify-with-rubric`, `publish-lab-blog`.

## Non-negotiable invariants (read first)
- **Independent verification is mandatory, at every level.** Every synthesis note is graded by
  a **fresh, non-fork** sub-agent that re-extracts the sources. A self-check never substitutes;
  in practice it passes notes that the decoupled checker then fails. See
  `references/verifier-prompt.md`.
- **Honest calibration.** Predict before you run; a rubric failure is **not** a clean pass;
  the maker never promotes its own Option. See `references/pitfalls.md` §9–11.
- **Human gates are absolute:** publishing (git push), writing to the source library, and
  submitting a manuscript. Draft up to the line, then stop and ask.
- **Source library is read-only.** Never modify/rename/overwrite source PDFs or pre-existing
  distilled notes.

## Phase map

### Phase 0 — Scaffold & scope (once per program)
1. Run the finding-unknown entry `map-vs-territory` on the research question; sort the gap
   into the four quadrants.
2. `blindspot-pass` → hand back the load-bearing decisions; **grill the user** on scope,
   output form, and the loop's role *before building* (don't guess architecture).
3. `/grill-with-docs` (grilling + domain-modeling) → `docs/ADR/*` + `docs/glossary.md`.
4. `reference-anchor` → map each sub-question to concrete corpus paths.
5. `decision-first-plan` → plan ordered by decision-volatility (decisions up top).
6. Copy `references/option-ledger.template.md` → `STATE/option-ledger.md`; fill parent
   objective, reward, denylist, and the **promotion gate** (get the human to approve the
   numbers — missing approval blocks promotion).
7. Create `CLAUDE.md` (house Q&A), `handoff.md`, `research/deviation-log.md`.

### Phase 1 — Distil a cluster (the inner FC-STOMP loop; the `distil-cluster` Option)
Run per cluster via `/distil-cluster <cluster>`. Policy **v1.1**:
1. **Feature check:** is the cluster thin for the target scope (no covering note, or an
   existing note covers a *different* cluster)? Confirm before spending effort.
2. Extract sources with **PyMuPDF** (glob for non-ASCII/spaced filenames). A thin extract
   signals a slide deck / image PDF → apply the **source-quality gate**.
3. `pkm-three-levels`: index → synthesis → gaps/experiments. Write only under `synthesis/`.
4. **Pre-checker hardening (do these before self-check):**
   - confirm each cited filename's **actual title** (paper-identity check);
   - **copy every citation's author list + journal + year verbatim from the PDF's title page —
     never render them from memory** (the model fabricates coauthors/journals with confidence,
     and its self-check will not catch it — treat citation self-checks as untrusted);
   - verify **every quantitative claim against full-text methods**, not just the abstract;
   - **quotation marks = verbatim only**; paraphrase otherwise;
   - keep entrainment vs modulation, phenomenon vs mechanism, and causal vs correlational
     distinct; flag reverse-inference.
5. Self-check against `references/rigor-rubric.md`, then **record a prediction** (p(first-try
   verify), cost, touched paths, failure modes) in the ledger.

### Phase 2 — Verify (the maker/checker gate)
`/verify-note <path>` → spawn a **fresh general-purpose (non-fork) sub-agent** with
`references/verifier-prompt.md`. It re-extracts the PDFs, checks load-bearing claims verbatim,
grades the rubric, and returns ACCEPT / ACCEPT-WITH-FIXES / REVISE. Apply required fixes.
Then close the trial honestly:
- outcome unresolved before the checker = **unknown** (no Brier update);
- accepted with only cosmetic fixes and **no rubric failure** = clean pass (y=1);
- any **rubric failure** = not a clean pass (y=0), even if the verdict is "accepted";
- update Brier `(p−y)²`, the confidence, counters, and the raw trace in the same cycle.

### Phase 3 — Promote (only when earned)
When the approved gate is met (e.g. ≥3 checker-confirmed clean trials AND mean Brier ≤ 0.15 +
regression union + human digest), a human — not the maker — may move `distil-cluster` L1→L2.
**L2 still keeps the per-note independent verify;** promotion only lightens human review.

### Phase 4 — Ship (L3, staged, human-gated)
1. `publish-lab-blog`: assemble the argument from the verified notes; **verify every citation
   (journal/DOI/year) against a primary source** before it goes on a public page; build the
   self-contained post; **draft only — stop before git push** (human gate).
2. After human approval: register + push + verify deploy + mirror.
3. Escalate the same synthesis to a manuscript (`research-to-publication`) — human-gated.

## The PKM spine underneath
L1 = the corpus (read-only) · L2 = the synthesis notes + their links · **L3 = ship** (blog →
manuscript). The whole point is L3: don't stall in L2. Knowledge only counts when reality
pushes back.

## References
- `references/pitfalls.md` — the hardening rules (why each phase step exists).
- `references/rigor-rubric.md` — the pass/fail checklist for every note.
- `references/verifier-prompt.md` — the decoupled-checker prompt template.
- `references/option-ledger.template.md` — the Oak ledger, pre-filled for lit-synthesis.

## Failure patterns (do not do)
- Self-check in place of an independent checker · scoring a rubric failure as a pass ·
  maker promoting its own Option · citing a slide deck / preprint-as-independent · a number
  from the abstract not checked against the methods · a paraphrase set in quotation marks ·
  pushing/publishing without the human gate · writing to the source library.
