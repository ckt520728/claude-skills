# Safety layer reference (RAG spine + guardrail + send policy)

## Three-ring constrained RAG

| Ring | Content | Stored as |
|---|---|---|
| Outer: `guideline` | ADA, KDIGO, national guidelines, model papers | `knowledge/*.md` with `ring: guideline` |
| Middle: `wiki` | curated local formulations, pathways, boundaries | `ring: wiki` |
| Inner core | the desktop LLM's own language | not stored; must cite `[wiki:id]` |

Front-matter fields: `id, title_zh, title_en, tags, sources, ring, review_status (draft|verified)`.

- **Human-in-the-loop gate:** a page counts as verified only when the front
  matter says so (curated from a cited guideline) or a physician verifies it in
  the UI (`wiki_reviews`).
- **Unconfirmed content starts as draft.** Examples: a local guideline summary
  or local food values.
- **Patient-facing paths** use `verified_only=True`.

### Hybrid retrieval with no dependencies

- **Score:** the lexical score (token counts, +8 for a title hit, +4 for a tag
  hit) plus a TF-IDF cosine over **character bigrams of CJK runs** and Latin
  words. This handles Chinese without a tokenizer or an embedding model.
- **Ranking:** `hybrid = cos×100 + min(lex, 40)×0.5`.
- **Each result returns** `cite_as: "[wiki:id]"`, `ring` and `review_status`.

## Guardrail: `verify_draft(text, audience, assessment, context)`

Checks run in this order; the strictest result wins. The result is one of `pass`, `needs_review` or `blocked`.

1. **Blocked content.** For each sentence:
   - **Dose instruction:** a number with a dose unit (mg, 毫克, units, 單位,
     IU, U) *and* a change verb (增加, 減少, 調整, increase, start, stop…).
   - **Titration:** "titrat" or 滴定.
   - **Prescribing imperative:** start or stop combined with a drug list, in
     either word order.
   - **Patient audience only:** diagnosis assertions such as 您有/得了 +
     diagnosis or "you have" + diagnosis.
2. **Citations.**
   - Every claim sentence needs `[wiki:id]`. A claim sentence contains a digit
     or a hint word such as 風險/建議/should/risk/target.
   - Headings (`# ...` or a line that is only `【...】`) are not claims.
   - A citation id must exist; an unknown id gets `needs_review`.
   - An unverified page is `blocked` for patients and `needs_review` for
     clinicians.
3. **Number grounding.**
   - Strip citations, clock times (`12:45`) and dates first.
   - Each number must equal a value at the draft's own precision. The value can
     come from the patient's assessment, from extra `context` the caller
     passes, or from the cited pages' text.
   - **Label-aware:** "eGFR 31" must match the eGFR field (likewise UACR, HbA1c,
     LDL, HDL, SBP, FIB-4, KFRE, TIR, GRI, GMI, CV, SCORE2, WATCH-DM). A
     mismatch is `label_value_mismatch`.
   - **Never ground on raw history.** Skip CGM series, AGP bins, lab history,
     diet logs and per-meal results, or coincidental matches will pass.

**Sentence splitting:**
- Split after 。！？!? and `. `, *unless a `[wiki:` citation follows*.
- Do not split on ；.
- Without these two rules, citations get separated from the claims they
  support.

The guardrail is a safety net, not proof. Paraphrased dose advice can slip through, so a human sign-off stays the final control.

## Send policy (`auto_send(patient_id, text, reason=...)`)

```
AUTO_SEND_REASONS = {"safety_rule", "approved_template"}
reason not in set            → PermissionError
no messaging link            → blocked
approved_template, no consent→ row stored as 'blocked'
live mode                    → push; else mark 'sent' (demo)
every row                    → meta.auto_reason
```

- **Templates:**
  - fixed text, with no patient numbers and no doses;
  - a link to a wiki page;
  - physician approval required.
- **Schedules:**
  - an agent or educator *proposes*;
  - a clinician *activates*;
  - the send hour must be 6–21;
  - revoking a template pauses its schedules.
- **What agents can do:** stage a message (the guardrail runs first) and propose
  a schedule. Nothing else.

## Roles

| Action | Physician | Educator | Admin |
|---|---|---|---|
| Read clinical data | ✓ | ✓ | ✓ |
| Stage or confirm a message, acknowledge an alert, record an assessment, propose or activate a schedule | ✓ | ✓ | ✗ |
| Sign a summary, approve a template, verify a wiki page | ✓ | ✗ | ✗ |
| Import, read the audit log | | | ✓ |
