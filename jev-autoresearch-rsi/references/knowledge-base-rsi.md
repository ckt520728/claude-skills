# Knowledge base and RSI

## Layout (inside `knowledge_base.root`)

```
<root>/
  index.md            topic index (managed block)
  RSI ledger.md       human-readable mirror of the SHA-256 ledger
  主題/<topic>.md      one page per research topic, with a Mermaid mind map
  概念/<concept>.md    one page per concept: definition, claims with [[來源/...]] links
  來源/<id>.md         one page per source (doi-…, arxiv-…, pmid-…, Notebook answer …)
  缺口/gaps.md         open questions; the planner turns them into queries next run
```

Every page has frontmatter (`title`, `date`, `tags`, `sources`, `run_id`, `confidence`) and `[[wiki-links]]`.
- The engine writes only between `<!-- autoresearch:begin -->` and `<!-- autoresearch:end -->`. Text you add outside those markers is never touched.
- Link rewrites (merge, repair) are also limited to managed blocks.

Vault-level rules (Obsidian "Second Brain" convention):
- New pages append one line to the vault's `知識庫/index.md`. Reorganizations append to `知識庫/log.md`. Both are append-only.
- Optionally, RSI decisions are mirrored to a queue page (`knowledge_base.queue_md`).
- Input folders such as `Clippings/` are never modified.

## Fitness (measured by code, `score_basis: normalised-v2`)

Each defect count is divided by the thing it can occur in:

```
score = 1 − Σ wᵢ · rateᵢ        rate = count / denominator (capped at 1)

broken_links            / links (unique page→target pairs)   w .30
unsourced_claims        / claims                             w .25
orphans                 / linkable pages                     w .20
duplicate_concepts      / concepts                           w .10
single_source_concepts  / concepts                           w .10
open_gaps               / all gaps listed (open + ticked)    w .05
```

- A perfect wiki scores 1.0, and an empty one scores 0.
- With the denominators held fixed, the score falls strictly as any count rises.
- The same proportions at twice the size give the identical score.
- `--kb-fitness` reports `totals` and `rates` alongside the raw counts.
- Open gaps are measured as the share still open, not per concept. Otherwise a good merge, which removes a concept, would look worse.
- Gaps close by hand (tick `- [x]` in `缺口/gaps.md`) or automatically when a later run answers them; see below.

## Auto-closing gaps (the model proposes, code decides)

1. Loop 1's planner and every auditor see the topic's open gaps, numbered `G1…Gn` (at most 30).
2. The auditor may return `"answered_gaps": [{"gap": "G#", "answer": "...", "keys": ["E#", "E#"]}]`.
3. Code closes a gap only if **all** of these hold:
   - the run's final audit verdict is PASS (after code overrides); a failing audit closes nothing
   - the gap id exists, and each gap is answered once
   - the answer is non-empty and at most 600 characters
   - it cites at least **2 distinct collected, on-topic sources**
   - at least one of them is primary; secondary summaries such as NotebookLM answers cannot close a gap alone
   - every figure in the answer appears in the cited sources (the same NumericGrounding check as the paper)
4. The gap line becomes `- [x]` with its text unchanged, so de-duplication still works. The answer goes on an indented line beneath it: `  - 已回答（run <id>，<date>）：<answer>（[[來源/…]]、…）`.
5. Rejected answers and their reasons are kept in `run_report.json` → `gap_rejections`; verified ones in `gaps_closed`.

If you disagree with an answer, untick it (`- [ ]`). Matching is by gap text, so a gap is never closed twice.

## Promotion rule

A proposal is one of `repair_link`, `merge_concepts` or `link_orphan`. It is applied to a scratch copy and measured. It is promoted only if all three hold:
1. its target metric falls,
2. the overall score rises strictly,
3. no other metric gets worse.

Otherwise it is rejected. Either way, the decision is appended to `.rsi/kb_ledger.jsonl`, a SHA-256 hash chain where each entry hashes the one before it.

## History: why v1 was replaced

v1 used absolute counts, `1 − Σ w·c/(c+5)`, so a growing wiki scored worse simply for being bigger. In the 2026-11-08 demo the wiki grew from 31 to 67 pages, and v1 fell from 0.906 to 0.879 even though every share improved. The same wiki scores 0.886 under v2.

Scores from v1 and v2 are not comparable. Ledger entries written before the switch use the v1 scale.
