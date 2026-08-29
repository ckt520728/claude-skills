---
name: cognitive-test-to-samd
description: Take a lab cognitive/neuropsychological test from research instrument to a regulated Software as a Medical Device (SaMD) — deciding whether to cross the medical-device line at all, building age-stratified norms, converting research data into regulatory evidence, and running the Taiwan TFDA approval path (分類分級判定 → 醫療器材商許可執照 → QMS/製造許可 → 查驗登記). Use when the user wants to commercialise a cognitive test, brain-training app, or psychometric instrument; asks whether their app "counts as a medical device"; plans normative data collection across age groups; or asks about SaMD/醫療器材軟體 registration, intended use statements, or clinical evaluation for a digital cognitive assessment. Trigger on the intent even without the acronym — "our lab test, can we sell it", "認知測驗要申請醫材", "do we need TFDA approval for this app", "we already collected the norms, what now".
---

# Lab Cognitive Test → SaMD

Workflow for turning a research cognitive instrument into a lawfully marketed
medical device software product. Distilled from the NeuroPlay 腦力訓練 →
NeuroPlay Clinical project (2026-08), Taiwan/TFDA pathway.

**Jurisdiction note.** The gates and article numbers below are Taiwan
(《醫療器材管理法》). The *reasoning structure* — claim determines
classification, evidence conversion, critical-path re-derivation — transfers to
FDA/MDR unchanged; the article numbers do not. Read
[taiwan-regulatory-map.md](references/taiwan-regulatory-map.md) for the Taiwan
specifics and swap that file for another jurisdiction.

## The one thing that governs everything

**Classification is decided by the claim, not the technology.** The same code,
the same data, the same screen — change one sentence of output text and the
legal status changes:

| Output shown to the user | Status |
|---|---|
| "Here is your score today, compared with your own last week" | General wellness — **not** a medical device |
| "Your score is at the 12th percentile for your age" | Interprets subject data to aid diagnosis — **medical device** |

So the first question is never "how do we get approved". It is:

> **Do we want to cross the line at all, and which sentence is the crossing?**

Most lab instruments are *already* lawfully outside the regulation. Crossing is
a deliberate business decision that buys clinical credibility at the cost of
2–3 years and a quality system. Say this out loud to the user before planning
anything.

### Always propose the two-track split

Never migrate the existing product across the line. Fork it:

| Track | Product | Claim | Status |
|---|---|---|---|
| **A · Wellness** | existing app, stays on the store | own-score trends only; no norms, no percentile, no "abnormal" | not a medical device |
| **B · Clinical** | new SKU | norm comparison, adjunctive to a clinician | regulated SaMD |

Then write the hard rule into the project's `CLAUDE.md`:

> **Track A's claims must never be contaminated by Track B.** Any change that
> puts norms, percentiles, or "abnormal" wording into Track A is a regulatory
> event, not a UI tweak.

This matters because an unapproved device on the market is a criminal offence
in most jurisdictions (Taiwan: 管理法 §62, up to 3 years imprisonment).

## Route the task

1. **Not yet decided / "should we?"** → run *Phase 0* below. Do not plan
   anything else first.
2. **Decided to cross, nothing built yet** → Phases 0 → 5 in order.
3. **"We already collected the data"** → jump to
   [evidence-conversion.md](references/evidence-conversion.md). Collected ≠
   admissible. Run the five-item audit before rescheduling anything.
4. **Norms design / sample size / reliability** → read
   [normative-study-design.md](references/normative-study-design.md).
5. **Writing the intended use statement** → read
   [intended-use-statement.md](references/intended-use-statement.md). Write it
   *early*; it surfaces gaps the plan cannot see.
6. **Something went wrong / sanity check** → read
   [pitfalls.md](references/pitfalls.md).

## Phases and gates

Each phase exists to **close one uncertainty**, not to complete a batch of
tasks. Order them by "which wrong answer forces the most rework".

| Phase | Closes | Gate |
|---|---|---|
| **0 · Positioning** | What class is this, and who may hold the licence? | Written classification ruling from the regulator |
| **1 · Legal entity** | Who is the applicant? | Manufacturer licence issued |
| **2 · QMS + software file** | Can this codebase carry a quality system? | Manufacturing licence |
| **3 · Evidence** | Do our data qualify as regulatory evidence? | Clinical evaluation report accepted internally |
| **4 · Registration** | Is the dossier complete? | Product licence |
| **5 · Post-market** | — | ongoing |

### Phase 0 — Positioning (do this before anything else)

1. Write a **one-page Intended Use Statement** (bilingual). It decides
   everything downstream. Template in
   [intended-use-statement.md](references/intended-use-statement.md).
2. Draw the **two-track boundary table**: which features and which sentences
   belong to A, which to B.
3. **Call the regulator's free consultation line** with that one page in hand.
4. **File for an individual classification ruling.** In Taiwan this is
   醫療器材管理辦法 §6. It costs little and takes weeks, and it removes the
   single largest uncertainty in the whole programme. *This is the highest-value
   step in the project — never skip it to "save time".*
5. Settle data ownership and endorsement scope with the academic partner **in a
   written agreement**, including an advertising-review clause (see Pitfall 7).

**Gate 0.** If the ruling comes back at the highest risk class — usually
because the product does not fall within any listed item's identification scope
— **stop and narrow the intended use**. Do not push forward.

### Phase 1 — Legal entity

A university lab is not a medical device firm and **cannot be the applicant**.
The research centre can be the technology source, study site, and academic
endorser; the licence holder must be a company. Resolve this early — it gates
everything after it, and technology-transfer negotiation is slow.

### Phase 2 — QMS and the software file

Usually the **critical path** once data collection is done. Expect
ISO 13485-equivalent QMS, IEC 62304 lifecycle, ISO 14971 risk management,
IEC 62366 usability (heavily scrutinised for elderly users), software
validation, and cybersecurity documentation.

**What this does to a research codebase:**

- Every third-party dependency becomes SOUP requiring a listed risk assessment.
  A typical `node_modules` or `requirements.txt` *is* the SOUP list.
- Scoring and interpretation logic needs **100% unit-test coverage with frozen
  golden test data**, plus a requirement→design→test traceability matrix.
- Version pinning forced by tooling (e.g. an SDK locked by a store constraint)
  is acceptable, but must be a **documented, risk-assessed decision**, not a
  README sentence.

Tell the user plainly: if the repo's only quality gate is a type-checker, that
work starts now, not at submission time.

### Phase 3 — Evidence

If norms are not yet collected, read
[normative-study-design.md](references/normative-study-design.md).

If norms *are* collected, do **not** simply subtract that time and cost from
the schedule. Run the five-item audit in
[evidence-conversion.md](references/evidence-conversion.md) first — IRB scope,
version identity, test–retest, traceability, and testing setting. The gap
between "we have the data" and "we have the evidence" is typically 6–9 months.

### Phase 4 — Registration

Assemble the technical dossier, submit, expect multiple rounds of queries.
Review time is **administrative and cannot be compressed with more staff** —
say so when the user asks to accelerate.

### Phase 5 — Post-market

Adverse event reporting, unique device identification, and — the one that
catches academic teams — **pre-approval of advertising**. See Pitfall 7.

## Working rules for this kind of project

1. **Grade every claim.** Tag each statement `[verified]` (primary source
   quoted), `[inferred]`, `[unverified]`, `[estimate]`. Surface the tags
   visually in any slide deck. Downgrading is safer than misleading, and it lets
   a reviewer ask "are you sure about this one" and get an honest answer.
2. **Keep an unknowns register**, not just a task list. It is more honest than
   a Gantt chart. Record what closes each unknown and what it costs if wrong.
   **Keep closed unknowns in the file** — deleting them destroys the record of
   what the team used to believe.
3. **Designate one reference-anchor document** as the single source of truth for
   regulatory statements; every other document defers to it, and updating it
   triggers a downstream review.
4. **Re-derive the critical path after every schedule change.** Removing work
   from a parallel track saves far less than its duration, and it usually
   *moves* the critical path — which changes who you need to hire next.
5. **Report slack, not just milestones.** When a conditional workstream becomes
   certain, the launch date may not move while the buffer collapses. Say
   "buffer went from 5 months to 2", not "no schedule impact".
6. **Get primary sources.** Search summaries reliably miss the one sentence that
   decides the case. Fetch the actual guidance PDF, extract the text, and grep
   it. See Pitfall 1.

## Guardrails

- **This skill is not legal or regulatory advice.** Classification is
  determined only by the competent authority's ruling on the specific product.
  Everything produced here is internal planning material and must say so.
- Never state an article number, fee, or deadline you have not read in the
  primary source. Tag it `[unverified]` instead.
- Never let the user market the wellness track with medical claims while the
  clinical track is in progress — that is the highest-consequence failure mode
  in the whole workflow.
- Do not promise a launch date. Administrative review time is outside anyone's
  control; give ranges and name the assumptions.
