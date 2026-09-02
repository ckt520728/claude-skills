# Profile: literature-corpus

把自己電腦裡的 PDF 資料庫做分析、分類、摘要與整理，最後寫成一份報告。

This is the profile where the harness earns its keep most obviously: reading 40
PDFs in one conversation is impossible, and reading them one job at a time is
routine.

## The pattern

```
fork one job per PDF
  → job writes vault/<id>.json (structured summary)
  → main thread reads ONLY the summary
  → one playbook line
  → forget the PDF entirely
then: classify from the vault, write the report from the vault
```

The raw PDF text never enters the main context. That single rule is the
difference between 8 papers and 80.

## Deliverables

| Name | Target | Split |
|---|---|---|
| `vault` | `vault/` | held_in |
| `coverage` | coverage check | held_in |
| `taxonomy` | `vault/taxonomy.json` | held_in |
| `report` | `draft/review.md` | held_in |
| `citations` | `draft/review.md` | held_out |

## Contracts

```bash
$K contract --name coverage --target vault/index.json --split held_in \
  --checks "exists,valid_json,cmd:python $V/check_coverage.py --sources refs/ --vault vault/"
$K contract --name taxonomy --target vault/taxonomy.json --split held_in \
  --checks "exists,valid_json,json_keys:categories;assignments;unassigned"
$K contract --name report --target draft/review.md --split held_in \
  --checks "exists,min_words:2000,no_placeholder,sections:Scope|Method|Findings|Contradictions|Limitations"
$K contract --name citations --target draft/review.md --split held_out \
  --checks "cmd:python $V/check_citations_resolve.py --doc draft/review.md --vault vault/"
```

> `$V` = `<plugin>/scripts/verifiers/`. These scripts ship with the plugin and are tested (`python scripts/verifiers/test_verifiers.py`). Run any of them with `--help` for the full option list.

`check_coverage.py` asserts every PDF in the source directory has a vault entry —
this is what catches the silent skip, which is the most common failure here and
the least visible.

`check_citations_resolve.py` asserts every citation in the report maps to a real
vault entry. Without it, the report can cite papers that were never read.

## Vault entry schema

Fix it before the first job runs, so 40 summaries are comparable:

```json
{
  "id": "lin2026_ahe",
  "citation": "Lin et al., 2026, Agentic Harness Engineering, arXiv:2604.25850",
  "question": "...",
  "method": "...",
  "findings": ["..."],
  "evidence_strength": "high|medium|low",
  "limitations": ["..."],
  "relevance": "...",
  "categories": ["..."],
  "quotes": [{"text": "...", "page": 4}]
}
```

For deep single-paper work, `academic-paper-deep-analysis` produces a far richer
seven-layer report. Use it for the handful of papers that carry the argument;
use this vault schema for the rest. Depth where it matters, coverage everywhere.

## Known failure mechanisms

| Mechanism | Symptom | Component to fix |
|---|---|---|
| `scanned_pdf_no_ocr` | Empty or garbage extraction | tool — detect < 200 chars extracted, route to OCR, log the fallback |
| `silent_skip_on_extract_failure` | Report covers 34 of 40 papers, no error | tool — the coverage check |
| `category_boundary_undefined` | Same paper classified two ways on two runs | memory — write the category definitions down first |
| `context_saturation_hallucination` | Summaries drift, details invented | the fork-and-forget pattern above |
| `citation_not_in_vault` | Report cites a paper never read | tool — the citation resolution check |
| `unicode_filename_breaks_tool` | One paper silently missing | tool — extract via a library, not a shell command, for non-ASCII paths |

That last one is real and easy to miss: a filename containing `Ö` or Chinese
characters can break a command-line PDF tool while everything else succeeds. The
coverage check is what surfaces it.

## Caution

Summarising is lossy in a directional way — nuance, hedging and stated
limitations are what get dropped first, and those are exactly what a critical
review needs. Keep verbatim quotes with page numbers in the vault, and quote
rather than paraphrase for any claim the report leans on.
