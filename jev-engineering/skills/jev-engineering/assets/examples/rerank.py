#!/usr/bin/env python3
"""Reranking and query-aware compaction.

Two functions, chosen by corpus size:

    rerank(query, docs)   -- the decision layer IS the similarity metric (small corpus)
                             or the reranker over an embedding shortlist (large corpus)
    compact(goal, chunks) -- score chunks and drop what does not clear the bar,
                             instead of paraphrasing them into a summary

Nothing is rewritten, so nothing is lost to a bad paraphrase -- which is the
whole argument for scoring over summarisation.

    python examples/rerank.py --query "how do I rotate the signing key" --docs docs.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jev import JevError, Score, decide  # noqa: E402

RELEVANCE = [
    "Does not address the query at all",
    "Mentions the topic but does not answer the query",
    "Partially answers the query",
    "Directly and completely answers the query",
]

DISPLAY_POLICY = [
    "Unrelated to the goal, do not show it",
    "Background only, a one-line summary is enough",
    "Useful detail, a short summary is enough",
    "Directly needed, keep it in full",
]


def rerank(
    query: str,
    docs: Sequence[Any],
    *,
    text_of: Callable[[Any], str] = str,
    max_chars: int = 6000,
    workers: int = 16,
) -> list[tuple[Any, float, float]]:
    """Score every (query, doc) pair and rank by score. Returns (doc, score, confidence).

    Rank on `score`. Use `confidence` to judge whether the ranking itself is
    trustworthy: a top result at score 3.0 with confidence 0.55 means the model
    thinks it is relevant and is not sure, which is a reason to show two results.
    """

    def one(doc: Any) -> tuple[Any, float, float]:
        try:
            r = decide(
                state={"query": query, "document": text_of(doc)[:max_chars]},
                questions={"relevance": Score(
                    instructions="How well does `document` answer `query`?",
                    criteria=RELEVANCE,
                )},
            )
        except JevError:
            return doc, -1.0, 0.0        # an invalid answer is an error, not a zero
        a = r.answers["relevance"]
        return doc, float(a.score or 0.0), float(a.confidence or 0.0)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        scored = list(pool.map(one, docs))
    return sorted(scored, key=lambda t: -t[1])


def compact(
    goal: str,
    chunks: Sequence[str],
    *,
    keep_at: float = 1.5,
    batch: int = 40,
) -> tuple[list[str], list[float]]:
    """Query-aware compaction: score chunks against the goal, keep what clears the bar.

    Chunks are batched because questions in one call share one state, so asking
    40 at once costs one state transfer instead of 40 (rule 5). The batch size is
    bounded by the 32k state ceiling, not by the question count.
    """
    kept: list[str] = []
    scores: list[float] = []

    for start in range(0, len(chunks), batch):
        window = list(chunks[start : start + batch])
        questions = {
            f"chunk_{i}": Score(
                instructions=f"How relevant is chunk {i} to the current goal?",
                criteria=DISPLAY_POLICY,
            )
            for i in range(len(window))
        }
        r = decide(state={"goal": goal, "chunks": window}, questions=questions)
        for i, chunk in enumerate(window):
            score = float(r.answers[f"chunk_{i}"].score or 0.0)
            scores.append(score)
            if score >= keep_at:
                kept.append(chunk)

    return kept, scores


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--query", required=True)
    ap.add_argument("--docs", type=Path, required=True, help='JSONL with {"id":..., "text":...}')
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()

    docs = [json.loads(l) for l in args.docs.read_text(encoding="utf-8").splitlines() if l.strip()]
    ranked = rerank(args.query, docs, text_of=lambda d: d.get("text", ""))

    print(f"{len(docs)} documents ranked for: {args.query!r}\n")
    for doc, score, confidence in ranked[: args.top]:
        flag = "" if confidence >= 0.80 else "   <- low confidence, ranking uncertain"
        print(f"  {score:4.2f}  (conf {confidence:4.2f})  {doc.get('id','?')}{flag}")

    dropped = sum(1 for _, s, _ in ranked if s < 1.5)
    print(f"\n{dropped}/{len(docs)} would be dropped at a keep bar of 1.5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
