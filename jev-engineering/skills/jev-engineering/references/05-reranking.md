# 05 — Reranking and relevance

Most agents retrieve by embedding similarity and accept a dot product as a proxy for meaning. Two better arrangements, chosen by corpus size.

## Small corpus: the decision layer *is* the similarity metric

Skip embeddings. Score every `(query, doc)` pair and rank by the returned probability.

```
query ──┬──> doc 1 ──┐
        ├──> doc 2 ──┼──> decide(query, doc) -> relevant? p ──> rank by p
        └──> doc N ──┘
```

N calls. No embedding model, no vector store, no index to keep fresh, no chunking strategy to tune. For a few hundred documents this is simpler *and* better, because it catches the document that shares no vocabulary with the query but answers it exactly — the case where a dot product is structurally blind.

```python
from jev import decide, Score
from concurrent.futures import ThreadPoolExecutor

def rank_one(doc):
    r = decide(
        state={"query": query, "document": doc.text[:6000]},
        questions={"relevance": Score(
            instructions="How well does `document` answer `query`?",
            criteria=[
                "Does not address the query at all",
                "Mentions the topic but does not answer the query",
                "Partially answers the query",
                "Directly and completely answers the query",
            ],
        )},
    )
    a = r.answers["relevance"]
    return doc, a.score, a.confidence

with ThreadPoolExecutor(max_workers=16) as pool:
    ranked = sorted(pool.map(rank_one, docs), key=lambda t: -t[1])
```

Rank on `score`; use `confidence` to decide whether the *ranking itself* is trustworthy. A top result at `score=3.0, confidence=0.55` means the model thinks it is relevant and is not sure — worth showing the second result too.

## Large corpus: the decision layer is the reranker

```
query ──> embeddings + dot product ──> top k ──> decide(query, candidate) ──> reranked
          millions of docs              k calls
          cheap, approximate            precision
          recall, not precision
```

Embeddings do what they are good at: cheap high-recall candidate generation. The decision layer does the semantic matching on the shortlist, which is where precision is actually decided and where dot products are weakest.

`k` between 20 and 100 is the usual band. Above that, the reranker cost stops being free relative to the generation it feeds.

## Context compaction is the same operation

Compaction today is a summarisation prompt, which is strange: summarisation is *general* compression, and general compression is hard. Query-aware compression is easy — once you know what you are looking for, deciding what to drop is trivial.

So score the chunks instead of rewriting them. Nothing gets paraphrased, so nothing is lost to a bad paraphrase.

```python
questions = {
    f"chunk_{i}": Score(
        instructions="How relevant is this to the current goal?",
        criteria=["Unrelated to the goal, safe to drop",
                  "Background only, a one-line summary is enough",
                  "Directly needed, keep it in full"],
    )
    for i in range(len(chunks))
}
r = decide(state={"goal": current_goal, "chunks": chunks}, questions=questions)
kept = [c for i, c in enumerate(chunks) if r.answers[f"chunk_{i}"].score >= 1.5]
```

Reported in the wild: a session taken from nearly 1M tokens to 86K in about a second.

Watch the 32k state ceiling — batch chunks in groups that fit, and remember state + the longest single question must also fit 32k. `assets/jev/bulk.py` handles the batching.

The richer version replaces the keep/drop binary with a **display policy** per chunk — `dont_show`, `short_summary`, `long_summary`, `full_text`. At that point context stops being a static log and becomes a query-dependent view, and the same repo state can be presented differently to every step of the loop.

## Score every artery, not just retrieval

The same pass applies to tool-call inputs, tool-call outputs, and blocks of internal reasoning. Anything that accumulates in a context window is a candidate for a relevance score before it is admitted.

## What stays in code

- Deduplication and near-duplicate collapse before scoring — you are paying per pair.
- Hard filters: date ranges, permissions, document type, tenant isolation. Never spend a model call to exclude what a `WHERE` clause excludes.
- The final cut. `score >= 1.5` is a business decision; keep it in your code, not in the criteria text.

## Tuning

Reranking is the one fork with an off-the-shelf metric: build a small labelled set of `(query, doc, relevant?)` triples from your own traffic and track nDCG@10 or MRR against your embedding-only baseline. If the reranker does not beat the baseline on your data, the criteria text is the first thing to rewrite — not the model.
