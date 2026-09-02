# Profile: academic-writing

撰寫學術論文或部落格文章 — 特別是投稿或發表前的 draft。

## Deliverables

| Name | Target | Split |
|---|---|---|
| `draft` | `draft/paper.md` | held_in |
| `structure` | `draft/paper.md` | held_in |
| `coherence` | coherence check | held_in |
| `citations` | citation resolution | held_out |

## Contracts

```bash
$K contract --name draft --target draft/paper.md --split held_in \
  --checks "exists,min_words:3000,no_placeholder,sections:Abstract|Introduction|Methods|Results|Discussion|Limitations"
$K contract --name coherence --target draft/paper.md --split held_in \
  --checks "cmd:python $V/check_coherence.py --doc draft/paper.md"
$K contract --name terms --target draft/paper.md --split held_in \
  --checks "cmd:python $V/check_glossary.py --doc draft/paper.md --glossary draft/glossary.json"
$K contract --name citations --target draft/paper.md --split held_out \
  --checks "regex_absent:\\[citation needed\\],cmd:python $V/check_citations_resolve.py --doc draft/paper.md --bib draft/refs.bib"
```

> `$V` = `<plugin>/scripts/verifiers/`. These scripts ship with the plugin and are tested (`python scripts/verifiers/test_verifiers.py`). Run any of them with `--help` for the full option list.

`check_coherence.py` (shipped in `scripts/verifiers/`) is a plain script, not a model call. It catches what
section-parallel drafting reliably breaks:

- a paragraph that appears near-verbatim in two sections
- a term defined in Methods and never used again
- a result mentioned in Discussion that appears nowhere in Results
- an abbreviation used before it is expanded

These are mechanical, they are the defects reviewers actually flag, and a script
finds them more reliably than re-reading does.

## Decomposition

`outline` → sections in parallel → `terminology_align` → `coherence` →
`citation_align`.

The outline is a contract in itself. Fix argument structure before any section is
written; restructuring after four sections exist costs all four.

## Known failure mechanisms

| Mechanism | Symptom | Component to fix |
|---|---|---|
| `section_written_in_isolation` | Sections 3 and 4 contradict each other | middleware — every section job reads the outline plus adjacent section summaries |
| `linguistic_redundancy` | Same sentence, two places | tool — the coherence script |
| `referent_drift` | "this approach" points at different things | tool — coherence script, unresolved-referent check |
| `citation_fabricated` | Plausible reference that does not exist | tool — resolve every citation against a real database |
| `hedge_stripped_in_summary` | A tentative finding becomes a claim | write from verbatim quotes, not from paraphrase |
| `abstract_overclaims_results` | Abstract promises more than Results shows | contract — every abstract claim maps to a Results subsection |

`citation_fabricated` is the one that ends careers. A `regex_present` check
confirms a citation marker exists, not that the paper does. Resolve every
reference against an actual database before the draft leaves your machine. This
is not optional and it is not something to delegate to a structural check.

## Boundary condition

Structure, consistency, citation hygiene and redundancy are checkable, and this
loop is genuinely good at them.

**Argument quality, novelty and voice are not.** Use [[verify-with-rubric]] with
a separate context-isolated sub-agent, write the rubric before drafting, and read
its verdict as advice. An automated loop optimising against an LLM judge will
find the judge's blind spots long before it finds good writing.

## Related

For the review-and-critique direction rather than the drafting direction, the
`academic-paper-deep-analysis` skill produces a seven-layer critical read and can
generate targeted follow-up queries from its own limitations section.
