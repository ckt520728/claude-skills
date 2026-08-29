# Intended Use Statement — Template and Load-Bearing Wording

One page, bilingual. It is the foundation document: the classification ruling,
the technical dossier, the labelling, the advertising review scope, and the
clinical evaluation target all derive from it.

**Write it in Phase 0, before the plan is finalised.** Drafting it forces
answers that a Gantt chart never asks for — and that is its second purpose.

## Template

```
產品 Product:         [name — must be clearly distinct from the wellness SKU]
送審版本 Version:      [FROZEN version id + git tag; must match the version used to build the norms]
製造業者 Manufacturer: [licence-holding company]
文件版本:              [draft version, date]

1. 預期用途 Intended Use
   [What it measures] → [compared against age/education-stratified norms]
   → [outputs standardised scores and percentiles]
   → as ADJUNCTIVE INFORMATION SUPPORTING a healthcare professional's evaluation.

2. 預期使用者 Intended User
   Physicians / clinical psychologists / occupational therapists / trained
   healthcare professionals. The subject performs the tasks but does NOT
   interpret the output.

3. 預期使用族群 Intended Population
   [age range — MUST NOT exceed normative coverage]
   Exclusions: [sensory/motor impairment, inability to comprehend instructions, ...]

4. 使用環境 Use Environment
   Clinical or community settings UNDER HEALTHCARE PROFESSIONAL SUPERVISION.

5. 輸出 Output
   a. Task performance metrics
   b. Standardised scores and percentiles vs. matched norms
   c. [CONDITIONAL — only if ICC supports it] change across administrations and
      whether it exceeds the RCI threshold
   Output contains no disease name, diagnosis, risk stratum, or treatment advice.

6. 明確不宣稱事項 Explicit Limitations
   Does NOT diagnose any disease; is NOT a sole basis for diagnostic or
   treatment decisions; does NOT replace comprehensive neuropsychological
   assessment or clinical examination; does NOT provide therapeutic or
   pharmacological recommendations; is NOT for emergency use; performs NO
   automated triage or notification.

7. 與 Wellness 版之區隔
   [one sentence stating the wellness SKU does not compare against norms,
    does not output percentiles, and does not flag abnormality]
```

## Load-bearing wording — do not casually edit

| Wording | Why it carries weight |
|---|---|
| **"adjunctive information"**, not "diagnosis" | "Interprets subject data to assist diagnosis" lands at Class II. "Diagnoses" or "screens positive/negative" pushes the risk class upward |
| **"for healthcare professionals"**, not for the public | A trained interpreter filters the output, which lowers the risk class. Direct-to-consumer interpretation is a substantive change |
| **"standardised scores and percentiles"**, not "brain age" / "risk score" | Percentiles are descriptive statistics. "Brain age" and "risk" are inferential claims that demand extra clinical validity evidence |
| **Section 6 in full** | This is not a disclaimer — it is *part of the classification argument*. Deleting any line may cause the authority to re-assess the class |
| **"no automated triage or notification"** | Autonomous triage/notification (CADt-type) is treated as higher risk internationally. Explicitly excluding it stabilises the lower class |

## Handling the conditional output (5c)

If reliability data do not yet exist, **submit the version without 5c** for the
consultation and classification ruling. Omitting one output does not change the
class, and it lets Phase 0 start immediately instead of waiting on the
reliability study.

Add 5c only after the ICC is known. **Adding a claim later is far easier than
withdrawing one.**

## Fields people forget to fill

- Product name that cannot be confused with the wellness SKU
- Frozen submission version **and the git tag of the commit used to build the
  norms** — the single item most likely to be unrecoverable a year later
- Licence-holding legal entity
- Age bounds (depends on normative coverage — see normative-study-design.md)
- Task list with the construct each task measures

## Downstream

Consultation → classification ruling → technical documentation → labelling →
advertising pre-approval scope → clinical evaluation target.

**Any edit requires re-checking every downstream document.** Treat this as the
project's second reference-anchor file.
