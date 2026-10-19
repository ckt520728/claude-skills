"""Bulk labelling: map-reduce one decision over many rows.

The call is the easy part. What breaks a real bulk run is rate limits, no
checkpoint, a per-row cost that looked small, and an uncertain tail routed
nowhere. This handles all four.

    from jev import Choice
    from jev.bulk import estimate, label_rows

    est = estimate(rows[:100], state_fn, questions)   # measure before you launch
    out = label_rows(rows, state_fn, questions, key_fn=lambda r: r["id"],
                     checkpoint="runs/topics.jsonl", tau=0.90)
"""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from .client import JevError, decide
from .types import USD_PER_INPUT_TOKEN, Question

# ~1,200 requests/min is the binding ceiling at typical state sizes, not the
# ~250k tokens/sec one. That means 16-20 workers, not 200.
DEFAULT_WORKERS = 16
DEFAULT_RPM = 1_000  # deliberately under the documented ceiling, which moves


@dataclass
class RowResult:
    key: str
    labels: dict[str, Any] = field(default_factory=dict)
    certainty: dict[str, float] = field(default_factory=dict)
    probabilities: dict[str, dict[str, float]] = field(default_factory=dict)
    input_tokens: int = 0
    latency_ms: float = 0.0
    confident: bool = False
    error: str | None = None

    @property
    def label(self) -> Any:
        """The single label, when there is only one question."""
        return next(iter(self.labels.values())) if len(self.labels) == 1 else None

    @property
    def confidence(self) -> float:
        return min(self.certainty.values()) if self.certainty else 0.0


class _RateLimiter:
    """Simple requests-per-minute throttle shared across worker threads."""

    def __init__(self, rpm: int) -> None:
        self._interval = 60.0 / max(1, rpm)
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            if self._next <= now:
                self._next = now + self._interval
                return
            delay = self._next - now
            self._next += self._interval
        time.sleep(delay)


def estimate(
    sample: Sequence[Any],
    state_fn: Callable[[Any], Mapping[str, Any] | str],
    questions: Mapping[str, Question],
    *,
    total_rows: int | None = None,
    **decide_kwargs: Any,
) -> dict[str, float]:
    """Run a pilot and extrapolate cost. Do this before a large run.

    200k rows at 1,200 tokens is about $10. The same table at 8,000 tokens per
    row is about $67. The difference is a truncation decision in state_fn, and
    it should be yours rather than the longest row's.
    """
    tokens, latencies = [], []
    for row in sample:
        try:
            r = decide(state_fn(row), questions, **decide_kwargs)
        except JevError:
            continue
        tokens.append(r.input_tokens)
        latencies.append(r.latency_ms)

    if not tokens:
        raise JevError("Pilot produced no successful calls; fix the call before estimating.")

    mean_tokens = sum(tokens) / len(tokens)
    n = total_rows if total_rows is not None else len(sample)
    return {
        "sampled": len(tokens),
        "mean_input_tokens": round(mean_tokens, 1),
        "max_input_tokens": max(tokens),
        "median_latency_ms": round(sorted(latencies)[len(latencies) // 2], 1),
        "projected_rows": n,
        "projected_input_tokens": round(mean_tokens * n),
        "projected_usd": round(mean_tokens * n * USD_PER_INPUT_TOKEN, 4),
    }


def label_rows(
    rows: Iterable[Any],
    state_fn: Callable[[Any], Mapping[str, Any] | str],
    questions: Mapping[str, Question],
    *,
    key_fn: Callable[[Any], str],
    checkpoint: str | os.PathLike[str] | None = None,
    tau: float = 0.90,
    exit_option: str = "other",
    max_workers: int = DEFAULT_WORKERS,
    rpm: int = DEFAULT_RPM,
    on_result: Callable[[RowResult], None] | None = None,
    **decide_kwargs: Any,
) -> list[RowResult]:
    """Label every row, resumably.

    Rows are sent as separate calls rather than batched into one state: batching
    independent rows costs the same tokens, loses per-row confidence, and lets
    one row's content bleed into another's verdict. Batch *questions* (they
    share a state, so it is nearly free), not rows.

    Every result carries its full probability distribution, so the table can be
    re-thresholded later without re-running it.
    """
    rows = list(rows)
    done: dict[str, RowResult] = {}
    path = Path(checkpoint) if checkpoint else None

    if path and path.exists():
        done = _load_checkpoint(path)
    elif path:
        path.parent.mkdir(parents=True, exist_ok=True)

    pending = [r for r in rows if key_fn(r) not in done]
    if not pending:
        return [done[key_fn(r)] for r in rows if key_fn(r) in done]

    limiter = _RateLimiter(rpm)
    write_lock = threading.Lock()
    handle = path.open("a", encoding="utf-8") if path else None

    def work(row: Any) -> RowResult:
        key = key_fn(row)
        limiter.wait()
        try:
            r = decide(state_fn(row), questions, **decide_kwargs)
        except JevError as exc:
            return RowResult(key=key, error=f"{type(exc).__name__}: {exc}")

        out = RowResult(
            key=key,
            input_tokens=r.input_tokens,
            latency_ms=r.latency_ms,
        )
        for qid, answer in r.answers.items():
            out.labels[qid] = answer.value
            out.certainty[qid] = answer.certainty
            out.probabilities[qid] = answer.probabilities
        out.confident = (
            bool(out.certainty)
            and min(out.certainty.values()) >= tau
            and exit_option not in {str(v) for v in out.labels.values()}
        )
        return out

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(work, row): row for row in pending}
            for future in as_completed(futures):
                result = future.result()
                done[result.key] = result
                if handle:
                    with write_lock:
                        handle.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
                        handle.flush()
                if on_result:
                    on_result(result)
    finally:
        if handle:
            handle.close()

    return [done[key_fn(r)] for r in rows if key_fn(r) in done]


def _load_checkpoint(path: Path) -> dict[str, RowResult]:
    out: dict[str, RowResult] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue  # a truncated last line from a killed run
            if record.get("error"):
                continue  # retry failures on resume
            out[record["key"]] = RowResult(**record)
    return out


def split_tail(results: Sequence[RowResult]) -> tuple[list[RowResult], list[RowResult]]:
    """Split into the confident majority and the uncertain tail.

    The tail goes to a frontier model, a review queue, or an explicit
    "unlabelled" value -- but never into the output table wearing a confident
    label. Without a tail policy you never learn which rows were guesses.
    """
    confident = [r for r in results if r.confident and not r.error]
    tail = [r for r in results if not r.confident or r.error]
    return confident, tail


def summarise(results: Sequence[RowResult], question_id: str | None = None) -> dict[str, Any]:
    """Reduce in code. Counts, shares and totals are never a model's job (rule 6)."""
    from collections import Counter

    confident, tail = split_tail(results)
    qid = question_id or (next(iter(results[0].labels)) if results and results[0].labels else None)
    distribution = Counter(str(r.labels.get(qid)) for r in confident) if qid else Counter()
    tokens = sum(r.input_tokens for r in results)

    return {
        "rows": len(results),
        "confident": len(confident),
        "tail": len(tail),
        "errors": sum(1 for r in results if r.error),
        "escalation_rate": round(len(tail) / len(results), 4) if results else 0.0,
        "input_tokens": tokens,
        "usd": round(tokens * USD_PER_INPUT_TOKEN, 4),
        "distribution": dict(distribution.most_common()),
    }
