---
name: neuropsych-dementia-ddx
description: Educational reference for the neuropsychological differential diagnosis of dementias — how memory/cognitive profiles distinguish Alzheimer's disease from Lewy body, Parkinson's, frontotemporal, primary progressive aphasia, PSP/CBD, and normal-pressure hydrocephalus, and how those paradigms map onto cognitive-training game design. Use when reasoning about dementia subtypes, designing memory/cognition assessments or training tasks, or interpreting neuropsych test patterns. NOT a diagnostic tool — see guardrail.
---

# Neuropsychological Differential Diagnosis of Dementias

Reference distilled from *Neuropsychological Tools for Dementia* (Ch. 1–9,
esp. Ch. 8 short guideline) and cognitive-memory paradigm literature.
Built alongside the NeuroPlay 腦力訓練 training app.

## ⚠️ Guardrail — read first

This is an **educational / design-support** reference, not a diagnostic
instrument. Never output a diagnosis, risk score, or "you/they may have X"
verdict for a real person. Diagnosis requires a licensed clinician plus
history, imaging, and CSF/biomarkers. When applied to an app or any
end-user output, keep the framing **"training + trend tracking, consult a
clinician if concerned."** This mirrors Apple review guideline 1.4 and the
neuropsych literature's own caution that cognitive tests **overlap across
diseases by severity** and lose discriminating power in mid/late stages.

## The core conceptual shift

Modern practice moved from measuring **global cognitive decline** (MMSE/
MoCA totals) to profiling a specific **amnestic syndrome of the
hippocampal type** — because *what fails* discriminates subtypes far
better than *how much* fails. Screening totals (MMSE/MoCA/clock) are
confounded by age/education, have ceiling effects at the MCI stage, and
cannot separate disease mechanisms. Use them to flag, not to differentiate.

## Four memory dimensions that fingerprint AD

The signal for early AD (entorhinal + hippocampal degeneration) is a
**consolidation** failure with a distinctive error signature. These four
dimensions separate AD from the retrieval-type / executive profiles of
other dementias:

1. **Consolidation vs. retrieval dissociation.** AD can't move short-term
   into long-term store, so **cueing and recognition do NOT rescue
   recall**. Frontal-subcortical dementias (PD, vascular) have a retrieval
   deficit — cues/recognition *do* help. → Delayed *free* recall (CVLT,
   RAVLT, CERAD) is highly sensitive vs. controls, but by itself fades as
   a *differential* marker as other dementias progress.
2. **Familiarity over recollection → false positives on lures.** With the
   hippocampus down, AD leans on cortical *familiarity* and over-accepts
   semantically/visually similar **lures**. **AD = false positives; non-AD
   = omissions.** This holds even after correcting for MMSE — one of the
   strongest AD-vs-(PD/LBD) discriminators. Paradigms: DRM (semantic
   intrusions), picture-recognition with similar lures.
3. **Cross-modal paired-associate learning (PAL).** Object–location
   binding (CANTAB PAL) predicts MCI→AD conversion *earlier* than verbal
   delayed recall — a very-early marker.
4. **Serial position shift.** AD = **low primacy** (failed consolidation)
   with relatively **preserved recency** (working memory). LBD/vascular
   often instead drop *recency* (executive/WM load). The qualitative
   pattern, not the total, carries the information; low primacy + high
   recency also helps separate AD from late-onset depression.

Methodological trap: many standard recognition scores collapse hits and
false-alarms into one discrimination index, hiding the AD-specific false-
positive signal. When designing, **record hits and false-positives
separately.**

## Hypothesis-driven differential (Ch. 8 pattern)

Form a hypothesis from history + core tests, then for each suspected
disease run **Ask for / Look for / Add tests for / Red flag**. Condensed
discriminators:

| Suspected | Hallmark signals | Add tests for | Red flag (rethink) |
|---|---|---|---|
| **Alzheimer's (AD)** | Forgets yesterday's talk, no rescue by cueing; spatial disorientation in new places; progressive word-finding; head-turning to relative | Consolidation deficit, PAL, recognition false-positives, reduced primacy | Central motor signs → not mono-causal AD; "walked into room, forgot why" is WM/attention, not episodic |
| **Lewy body / PDD** | Visual hallucinations/illusions, cognitive **fluctuation**, REM sleep behavior disorder, smell loss, parkinsonism | Cognitive speed, ventral+dorsal visuoperception, visuoconstruction, spatial WM; provoke pareidolia (VOSP); TMT-B; **single-trial RT variability** for fluctuation | Hallucinations felt as unreal & non-frightening → Charles Bonnet; dysarthria + axial rigor → PSP |
| **Parkinson's disease** | Resting tremor arresting on movement, small-step gait, cognitive slowing, autonomic dysfunction | Cognitive speed, ventral visuoperception, visuoconstruction, self-ordered pointing (spatial WM), WCST, digit span, RBD questionnaire | Early dysphagia + disinhibition + severe fluency loss → PSP; ataxia + autonomic → MSA |
| **bvFTD** | Social withdrawal, loss of hygiene, risky/disinhibited behavior, apathy; family history | Disinhibition (Go/NoGo, prehension), reading-the-mind-in-the-eyes, object-alternation flexibility, NPI, Boston naming | Convulsions/absences → consider frontal tumor |
| **Semantic dementia** | Impaired comprehension & object recognition; fluent but meaningless speech, semantic paraphasia | Visual object agnosia, word-picture matching (BORB), comprehension; verbal WM should be **intact** | Can't repeat sentences / digit-span problems → logopenic PPA |
| **nfPPA** | Voice/pronunciation change; slow noun-focused speech; speech apraxia, phonematic paraphasia | Word-picture matching, reading irregular/abstract words, mental calculation | Leading visual agnosia → posterior cortical atrophy |
| **PSP** | Backward falls, vertical gaze/saccade palsy, apathy, axial rigidity, "eyes wide open" | Applause sign, Go/NoGo, vertical gaze, square-wave jerks, retropulsion, fluency, WCST/TMT-B, NPI | Onset <40 + psychosis + ataxia → Niemann-Pick C |
| **CBD/CBS** | Limb apraxia, alien-hand, "losing control" of a limb, dyscalculia, asymmetric parkinsonism | Ideomotor apraxia, bimanual coordination, tactile discrimination, dorsal visuoperception, peripersonal pointing | Dorsal+ventral visual deficits without somatosensory loss → PCA |
| **NPH** | Gait disturbance + urinary incontinence + cognitive slowing + memory | Fine motor, fluency, walking speed, WM, and memory **re-tested after spinal tap** (avoid retest inflation) | AD-type memory signature → weigh shunt gains/losses; tremor/rigor → PDD |

General red flag: cognitive impairment far more severe than a *recent*
onset would explain → question the hypothesis.

## Mapping paradigms → cognitive-training game design

Each discriminating paradigm doubles as a training mechanic that yields a
*trend-trackable* metric (the NeuroPlay design principle — emit trial-level
data, never a single score):

- **Recognition-with-lures** → a "spot the real one vs. a similar decoy"
  game; log **false-positives separately** (the AD-relevant signal).
- **Object–location PAL** → a memory-palace grid; track binding accuracy.
- **Partial-report / iconic memory** (Sperling) → flash-and-locate; track
  RT and location error.
- **Category/letter fluency** → timed word production; track unique items
  vs. repetitions (executive monitoring).
- **RT variability on single trials** → any timed task; high intra-task
  variability is an LBD-fluctuation signal.

Design invariants: difficulty may change task parameters but **never** the
scoring/interpretation; record the difficulty level per session so a
stable score at a rising level reads as improvement.

## Caveats on the underlying hypothesis

The "specific pathology → specific cognitive profile" model is strongest
at **MCI/early** stages and correlates with CSF markers (Aβ1-42,
phospho-tau). It weakens with: **floor effects** in mid/late disease (all
subtypes collapse), and **atypical AD** that doesn't start in the
hippocampus (logopenic PPA, posterior cortical atrophy) — over-relying on
"hippocampal amnesia" there causes false negatives. Always hold the
hypothesis loosely and defer to clinical workup.

## Source material

`docs/references/` in the NeuroPlay project: Ch. 1–9 of *Neuropsychological
Tools for Dementia* (esp. Ch. 8 short guideline; Ch. 2 AD; Ch. 3 Lewy/PD;
Ch. 5 PPA; Ch. 6 bvFTD; Ch. 7 NPH) and memory-paradigm notes (Q1–Q4,
Human Memory). These are design/education references, not a validation of
any app as a medical device.
