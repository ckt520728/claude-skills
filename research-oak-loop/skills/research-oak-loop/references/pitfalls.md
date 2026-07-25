# Pitfalls & Hardening Rules

Each rule below was earned by a real failure. They are the reason the SKILL phases have the
steps they do. Numbered to match the SKILL's failure references.

## Scoping & discovery
1. **Don't guess architecture.** Ambiguous multi-goal folders/questions get their load-bearing
   calls (scope / output form / method-role) resolved by grilling *before* building. → ADRs.
2. **Verify what existing notes cover.** A note that looks reusable may cover a *different*
   cluster. Check before assuming reuse or duplication.

## Source handling
3. **PDFs → PyMuPDF; glob non-ASCII names.** A thin extract (few kB from many pages) = a slide
   deck / image PDF, not a paper.
4. **Source-quality gate.** A file named like a paper may be an unpublished slide deck / draft.
   Never cite non-peer-reviewed material as evidence.
5. **Paper-identity check.** Two same-author/same-year files in one folder → confirm each cited
   filename's *actual title* before citing. (→ Option policy v1.1)

## Accuracy & citations
6. **Numbers vs full text.** Verify every quantitative claim against the methods/results, not
   the abstract. Abstract-level reading introduces silent numeric errors. (→ v1.1)
6b. **Never render a citation from memory — copy it from the PDF.** The model *fabricates*
   coauthors and conflates journals with high confidence, and its own self-check marks these
   green. In one run, 2 of 4 synthesis trials had a self-check-passed citation failure (a
   wrong year, then an invented coauthor + wrong journal). Copy author list + journal + year
   **verbatim from the PDF's title/first page**; treat every citation self-check as UNTRUSTED
   until an independent checker confirms it. (→ policy v1.2)
7. **Citation verify before publish.** Journal + DOI + year checked against a primary source
   before anything reaches a public page.
8. **Quotes = verbatim only.** A paraphrase inside quotation marks is a defect.

## Oak-loop integrity
9. **No self-promotion.** A rubric failure is not a clean pass; score honestly (y=0); let mean
   Brier reflect it; the maker never promotes its own Option.
10. **Independent, non-fork verifier.** Self-checks pass notes the decoupled checker then fails.
    A fork inherits the maker's bias — use a fresh sub-agent that re-extracts sources.
11. **Unresolved ≠ pass.** Pre-checker outcomes are unknown — no Brier update, no promotion
    credit.

## Process & environment
12. **Background-agent discipline.** Don't read the verifier transcript directly; wait for the
    notification; don't predict its result.
13. **Human gates are absolute.** Publish/push, source-library writes, manuscript submission —
    draft to the line, then stop and ask.
14. **Env specifics (Windows).** Push via PowerShell (not Git Bash — credential manager);
    watch en-dashes/CJK in filenames.

## The one-line summary
> The independent checker is where correctness actually lives. Everything else is there to give
> it a fair, honest shot — and to make sure the maker never grades its own work.
