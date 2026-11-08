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

## Fitness (measured by code)

```
score = 1 − Σ wᵢ · cᵢ / (cᵢ + 5)
weights: broken_links .30 · unsourced_claims .25 · orphans .20 · duplicate_concepts .10 · single_source_concepts .10 · open_gaps .05
```

## Promotion rule

A proposal is one of `repair_link`, `merge_concepts` or `link_orphan`. It is applied to a scratch copy and measured. It is promoted only if all three hold:
1. its target metric falls,
2. the overall score rises strictly,
3. no other metric gets worse.

Otherwise it is rejected. Either way, the decision is appended to `.rsi/kb_ledger.jsonl`, a SHA-256 hash chain where each entry hashes the one before it.

## Known design issue: absolute counts penalise growth

In the demo, the wiki grew from 31 to 67 pages and the score fell from 0.906 to 0.879:
- open gaps went 6 → 20 and single-source concepts 10 → 21
- the single-source *share* actually improved (71% → 64%)
- broken links, orphans and unsourced claims stayed at 0

A growing wiki scores worse simply because it is bigger. The fix under consideration is to normalise the growth-driven counts by the number of concepts. Decide on it before relying on the score as a trend line.
