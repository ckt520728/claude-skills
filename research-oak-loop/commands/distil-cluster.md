---
description: Run one FC-STOMP synthesis pass over a corpus cluster (the distil-cluster Oak Option), ending in a self-checked note ready for independent verification.
argument-hint: "<cluster name or folder>"
---

Run the `distil-cluster` Option from the `research-oak-loop` skill on: **$ARGUMENTS**

Follow SKILL Phase 1 (policy v1.1) exactly:

1. **Feature check** — confirm the cluster is thin for the target scope (no covering note, or
   the existing note covers a *different* cluster). If not thin, say so and stop.
2. **Extract** the cluster's sources with PyMuPDF (glob non-ASCII/spaced filenames). Treat a
   thin extract as a slide deck / image PDF and apply the source-quality gate.
3. **pkm-three-levels**: index → synthesis → gaps/experiments → draft `synthesis/<cluster>.md`.
4. **Pre-checker hardening (mandatory before self-check):**
   - confirm each cited filename's actual title (paper-identity);
   - verify every quantitative claim against full-text methods, not the abstract;
   - quotation marks = verbatim only;
   - keep entrainment/modulation, phenomenon/mechanism, causal/correlational distinct.
5. **Self-check** against `references/rigor-rubric.md`.
6. **Record a prediction** in `STATE/option-ledger.md` (p(first-try verify), cost, touched
   paths, failure modes) — before verification, not after.

Do **not** write outside `synthesis/`. Do **not** modify the source library. When done, tell
the user the note is ready and that the next step is `/verify-note synthesis/<cluster>.md`.
