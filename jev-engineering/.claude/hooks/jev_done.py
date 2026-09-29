#!/usr/bin/env python3
"""Stop hook: judge completion against printed evidence, not against belief.

Runs every time the agent tries to finish. Printing {"decision":"block"} with a
reason sends it back to work.

The ordering is the whole design:

  1. A turn cap, in CODE. No model can talk its way past a loop limit.
  2. .claude/checks.sh, in CODE. Failing tests need no model to adjudicate.
  3. The model judges ONLY what checks.sh printed -- an agent grading its own
     work tends to praise it, so the evidence has to come from somewhere else.

The middle band matters: unsure does not mean keep going forever. It writes
REVIEW.md and stops, which surfaces the ambiguity to a person instead of
burning turns on it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
PROJECT = HERE.parents[2]
sys.path.insert(0, str(PROJECT / "skills" / "jev-engineering" / "assets"))

MAX_PUSHES = 5          # turn cap lives in code
TAU_DONE = 0.90         # confident enough to stop
TAU_UNSURE = 0.50       # below this, send it back; between, stop and flag

COUNTER = PROJECT / ".claude" / ".pushes"
CHECKS = PROJECT / ".claude" / "checks.sh"
GOAL = PROJECT / "GOAL.md"
REVIEW = PROJECT / "REVIEW.md"


def let_stop(note: str = "") -> None:
    COUNTER.unlink(missing_ok=True)
    if note:
        print(json.dumps({"systemMessage": note}))
    sys.exit(0)


def keep_going(reason: str, pushes: int) -> None:
    COUNTER.write_text(str(pushes + 1), encoding="utf-8")
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def main() -> None:
    pushes = int(COUNTER.read_text(encoding="utf-8").strip()) if COUNTER.exists() else 0
    if pushes >= MAX_PUSHES:
        let_stop(f"jev-done: turn cap of {MAX_PUSHES} reached; stopping regardless of goal state.")

    if not CHECKS.exists():
        let_stop()  # nothing to verify against; do not invent a gate

    try:
        # Export our own interpreter: a shell launched from here inherits this
        # process's PATH, which on Windows often does not contain the python
        # running it. checks.sh honours $PYTHON.
        env = {**os.environ, "PYTHON": sys.executable}
        checks = subprocess.run(
            # A path RELATIVE to cwd, not str(CHECKS): on Windows an absolute
            # path is backslash-separated and Git Bash cannot resolve it, which
            # exits 127 and looks exactly like a failing test suite.
            ["bash", CHECKS.relative_to(PROJECT).as_posix()],
            capture_output=True, text=True,
            cwd=str(PROJECT), timeout=600, env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        let_stop(f"jev-done: could not run checks.sh ({exc}); stopping without a verdict.")

    # 126/127 mean the shell could not execute the script at all. That is not a
    # failing check, and reporting it as one sends the agent off to fix tests
    # that never ran.
    if checks.returncode in (126, 127):
        let_stop(
            f"jev-done: could not execute checks.sh (exit {checks.returncode}: "
            f"{checks.stderr.strip()[:200]}); stopping without a verdict."
        )

    if checks.returncode != 0:
        keep_going(
            "`.claude/checks.sh` exited non-zero. Fix the failing checks, then try to finish "
            f"again.\n\n{(checks.stdout + checks.stderr)[-4000:]}",
            pushes,
        )

    if not GOAL.exists():
        let_stop()  # no goal to judge against; the checks passing is the whole bar

    try:
        from jev import Noul, decide
        result = decide(
            state={"goal": GOAL.read_text(encoding="utf-8"), "checks": checks.stdout[-20_000:]},
            questions={"done": Noul(
                instructions="`checks` shows evidence for every condition listed in `goal`.",
            )},
            timeout=8.0,
        )
    except Exception as exc:  # noqa: BLE001
        # No verdict available. The checks passed, so stop -- but say why there
        # is no judgement, rather than silently implying one.
        let_stop(f"jev-done: checks passed but no verdict available ({type(exc).__name__}: {exc}).")

    done = result.answers["done"].noul or 0.0

    if done >= TAU_DONE:
        let_stop(f"jev-done: goal met (jev {done:.2f}, {result.latency_ms:.0f}ms).")

    if done >= TAU_UNSURE:
        REVIEW.write_text(
            f"jev put `done` at {done:.2f} -- confident enough not to loop, not confident "
            f"enough to call it finished.\n\nGoal:\n{GOAL.read_text(encoding='utf-8')}\n\n"
            f"Evidence (tail of checks.sh):\n{checks.stdout[-3000:]}\n",
            encoding="utf-8",
        )
        let_stop(f"jev-done: unsure ({done:.2f}). Stopped and wrote REVIEW.md for a human.")

    keep_going(
        f"Goal not met (jev: {done:.2f}). Compare GOAL.md with the output of "
        f".claude/checks.sh and finish the missing conditions.",
        pushes,
    )


if __name__ == "__main__":
    main()
