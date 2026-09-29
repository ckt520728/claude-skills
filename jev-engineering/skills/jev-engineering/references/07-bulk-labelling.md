# 07 — Bulk labelling: map-reduce a decision over a huge table

Same decision, N rows. The map step is a decision call per row; the reduce step is aggregation in code. The interesting engineering is not the call — it is throughput, resumability, and the uncertain tail.

## Shape

```
rows ──> [ filter in code ]  ──> map: decide(row) ──> reduce: aggregate / route
             cheap exclusions       batched questions      code owns the thresholds
                                          │
                                    q < tau ──> escalate tail to a frontier model / human
```

Reported reference: 1,018 papers into 24 topics for $0.08 total at 256 ms median per item. A fraud pipeline sorted 100 items in 1.42 s, routed the uncertain tail to a larger model, and reached 96/100 for about 7 cents. **That tail-routing is the shape most production classification should have**: cheap model decides, expensive model handles the tail, and the escalation threshold is a number you tuned rather than a hope.

## Two ways to batch, and they are not equivalent

**Batch the questions** when many judgments read *one* state — 13 questions over one document ran 12.2x cheaper and 10x faster than 13 separate calls, because the state is sent once.

**Batch the rows** only when the rows genuinely share context. Putting 20 independent rows in one state costs the same tokens as 20 calls, loses per-row confidence, and invites the model to let one row's content bleed into another's verdict. Prefer concurrency over row-batching:

```python
from jev.bulk import label_rows

results = label_rows(
    rows=rows,
    state_fn=lambda row: {"title": row["title"], "abstract": row["abstract"][:4000]},
    questions={"topic": Choice(instructions="Which topic does this paper belong to?", criteria=TOPICS)},
    key_fn=lambda row: row["id"],
    checkpoint="runs/topics.jsonl",
    max_workers=16,
    tau=0.90,
)
```

`label_rows` ships in `assets/jev/bulk.py` and handles the four things that actually break a bulk run.

## The four things that break a bulk run

**1. Rate limits.** ~250k tokens/sec and ~1,200 requests/min, adjusted dynamically and without notice. At 1,000 tokens per row that is well under the token ceiling but the request ceiling binds: 1,200/min means 16-20 workers, not 200. Back off on 429 and 529 with jitter; treat a sustained 429 as a signal to lower concurrency, not to retry harder.

**2. No checkpoint.** A 200k-row run that dies at row 180k and starts over has cost you the run, not the money. Append each result to a JSONL keyed by a stable row ID and skip completed keys on restart. `label_rows` does this; if you write your own, do it before the first real run, not after the first failure.

**3. Cost that looked small per row.** 200k rows at 1,200 tokens is 240M input tokens — about $10 at $0.042/M. Fine. The same table at 8,000 tokens per row is 1.6B tokens and roughly $67. Measure tokens on a 100-row pilot and multiply *before* launching, and truncate fields in `state_fn` deliberately rather than letting a long row decide your bill.

**4. The uncertain tail routed nowhere.** Without a tail policy, low-confidence rows get a confident-looking label in your output table and you never learn which ones were guesses.

```python
confident = [r for r in results if r.confidence >= 0.90 and r.label != "other"]
tail      = [r for r in results if r not in confident]
# tail: frontier model, human review queue, or an explicit "unlabelled" value — but never silence
```

Log the full `probabilities` for every row. It costs nothing at write time and it is the only thing that lets you re-threshold the table later without re-running it.

## Reduce in code, always

Counts, sums, group-bys, percentages, date buckets: code. Rule 6 is not a style preference here — the model reads dates as text and miscounts at scale, and a bulk run is exactly where "miscounts at scale" becomes your headline number.

```python
from collections import Counter
distribution = Counter(r.label for r in confident)          # code
share = {k: v / len(confident) for k, v in distribution.items()}   # code
```

## Validate on a pilot, then freeze

1. Label 100 rows by hand. This is the cost of entry; skipping it means you cannot tell a 95%-accurate run from a 70%-accurate one.
2. Run those 100 rows through the pipeline. Compare. Rewrite **criteria text** for every disagreement — that is where the decision lives.
3. Sweep `tau` on the labelled set (`10-threshold-tuning.md`), pick coverage against accuracy.
4. Pin the model version. `jev-1.13.0`, not `jev-latest`: an alias moving mid-run makes the first half of your table incomparable with the second.
5. Then launch.

## When the label set is large

Above ~30 options, a single `Choice` degrades. Two stages instead: `Choice` over 6-10 coarse families in the first call, then `Choice` over the members of the selected family in a second. Costs two calls instead of one and is markedly more accurate. Above 255 options a single `Choice` is not available at all.
