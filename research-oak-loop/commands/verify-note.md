---
description: Spawn a fresh, decoupled sub-agent to independently verify a synthesis note against its sources and the rigor rubric, then close the Oak trial honestly.
argument-hint: "<path to synthesis note>"
---

Independently verify: **$ARGUMENTS**

Follow SKILL Phase 2:

1. Build the verifier prompt from `references/verifier-prompt.md` — fill the note path, the
   source PDF paths, and the note's load-bearing quantitative/causal claims.
2. Spawn it with the `Agent` tool, `subagent_type: general-purpose` (or a code-reviewer type) —
   **never a `fork`**. Then wait for the completion notification; do **not** read its transcript
   file or predict its result.
3. On the verdict: apply required fixes to the note.
4. **Close the trial honestly** in `STATE/option-ledger.md`:
   - accepted with only cosmetic fixes and **no rubric failure** → clean pass, y=1;
   - **any rubric failure** (even if the verdict is "accepted") → y=0;
   - update Brier `(p−y)²`, confidence, counters, raw trace, and log any new failure mode.
5. **Promotion is a separate human decision.** Report whether the approved gate is met; the
   maker never promotes its own Option. At L2 the per-note independent verify is retained.

If required fixes touched load-bearing content, note it explicitly to the user.
