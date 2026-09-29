#!/usr/bin/env python3
"""Standalone task router. Build this before touching your agent.

Run it twenty times on real goals from your backlog and read the saved files.
You will find bad criteria text before it costs you anything -- which is the
entire point of building the dispatcher as its own script first.

    python examples/router.py
    python examples/router.py --goal "Compare three agent tools" --notes "No sources yet"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from getpass import getpass
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jev import Choice, JevError, Score, decide  # noqa: E402

# Uncertainty defaults here. In automation the failure you can recover from is
# stopping too often, so `review` is the default and a confident answer is
# required to override it.
DEFAULT_DESTINATION = "review"
TAU = 0.85  # placeholder -- tune against labelled examples from your own traffic

WORKERS = {
    "research": "Collect evidence still needed for the goal.",
    "write": "Draft the briefing from sufficient evidence.",
    "review": "Goal unclear, outside scope, or work complete.",
    "other": "None of the above fits.",
}


def route(goal: str, notes: str, *, available=None) -> dict:
    # Rebuild the menu from what exists and is free right now, not from a list
    # built at startup. A confident answer is useless when the option it picked
    # is unavailable.
    criteria = {k: v for k, v in WORKERS.items() if available is None or k in available or k == "other"}

    result = decide(
        state={
            "goal": goal,
            "completed_work": notes or "Nothing yet.",
            "available_workers": sorted(k for k in criteria if k != "other"),
            "constraint": "Save drafts for review. Do not publish.",
        },
        questions={
            "next_worker": Choice(
                instructions="Choose the next step for a research briefing.",
                criteria=criteria,
            ),
            "urgency": Score(
                instructions="How soon does this goal need to be completed?",
                criteria=["No deadline implied", "This week", "Today", "Blocking someone right now"],
            ),
        },
    )

    answer = result.answers["next_worker"]
    destination = DEFAULT_DESTINATION
    if answer.choice in {"research", "write"} and answer.confidence >= TAU:
        destination = answer.choice

    return {
        "goal": goal,
        "completed_work": notes,
        "choice": answer.choice,
        "confidence": round(answer.confidence or 0.0, 4),
        "probabilities": {k: round(v, 4) for k, v in answer.probabilities.items()},
        "urgency": round(result.answers["urgency"].score or 0.0, 2),
        "destination": destination,
        "escalated": destination != answer.choice,
        "model": result.model,
        "latency_ms": round(result.latency_ms, 1),
        "cost_usd": round(result.cost_usd, 8),
        "status": "queued",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Route a job to a worker queue.")
    parser.add_argument("--goal")
    parser.add_argument("--notes", default="")
    parser.add_argument("--queue", default="queue", help="directory for the local task queues")
    args = parser.parse_args()

    if not os.environ.get("TYPESAFE_API_KEY") and os.environ.get("JEV_PROVIDER", "jev") == "jev":
        os.environ["TYPESAFE_API_KEY"] = getpass("TypeSafe API key: ").strip()

    goal = args.goal or input("Goal: ").strip()
    if not goal:
        print("Enter a goal.", file=sys.stderr)
        return 2
    notes = args.notes or input("Completed work: ").strip()

    try:
        payload = route(goal, notes)
    except JevError as exc:
        print(f"Decision call failed ({exc.status}): {exc}", file=sys.stderr)
        return 1

    folder = Path(args.queue) / payload["destination"]
    folder.mkdir(parents=True, exist_ok=True)
    job = folder / f"{uuid4().hex}.json"
    job.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Saved handoff: {job}")
    print(f"  choice={payload['choice']} confidence={payload['confidence']} "
          f"-> {payload['destination']}{'  (escalated)' if payload['escalated'] else ''}")
    print(f"  {payload['latency_ms']} ms, ${payload['cost_usd']:.8f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
