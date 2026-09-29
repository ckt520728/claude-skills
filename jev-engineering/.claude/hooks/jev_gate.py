#!/usr/bin/env python3
"""PreToolUse gate: classify every Bash command before it runs.

Registered for the Bash matcher in .claude/settings.json. Reads the hook event
as JSON on stdin and prints allow / deny / ask.

Three properties make this safe to leave running overnight:

  1. Hard rules run in CODE, before the model, because the model trusts whatever
     text is in its state and a command can be written to mislead a classifier.
  2. `external` always lands on a human, whatever the confidence. Money, deploys
     and anything leaving the machine are policy, not classification.
  3. `other` is never auto-approved. The exit option routes the unknown to a
     person; it is not a bucket.

On ANY failure -- no key, timeout, 529, bad JSON -- this asks. A gate that
allows on failure is worse than no gate; one that denies on failure makes the
agent unusable when the network blips.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
PROJECT = HERE.parents[2]
sys.path.insert(0, str(PROJECT / "skills" / "jev-engineering" / "assets"))

# Exact rules. The model never sees these -- they are matched first and win.
HARD_BLOCKS = (
    "rm -rf /",
    "rm -rf ~",
    ":(){",              # fork bomb
    "git push --force",
    "git push -f ",
    "mkfs",
    "dd if=/dev/zero",
    "chmod 777 /",
    "| sh",
    "| bash",
    "curl | ",
    "wget | ",
)

# Labels that never auto-approve, regardless of confidence.
ALWAYS_ASK = {"external", "other"}

TAU = 0.90

RISK = {
    "read_only": "Only reads, lists, searches files or runs tests",
    "local_edit": "Changes files inside the project that git can restore",
    "destructive": "Deletes data, rewrites git history or touches files outside the project",
    "external": "Sends data out, pushes, deploys, installs from the internet or spends money",
    "other": "None of the above fits",
}


def answer(decision: str, why: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": why,
        }
    }))
    sys.exit(0)


def script_body(command: str, cwd: str) -> str | None:
    """Read the file a command is about to execute.

    `bash deploy.sh` tells a classifier nothing. The contents of deploy.sh tell
    it everything, and this catches a class of problem a filename never will.
    """
    match = re.search(r"(?:bash|sh|zsh|python3?|node)\s+([\w./\\-]+)", command)
    if not match:
        return None
    path = Path(cwd or ".") / match.group(1)
    try:
        if path.is_file() and path.stat().st_size < 20_000:
            return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        pass
    return None


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        answer("ask", f"jev-gate: could not parse hook event ({exc})")

    command = (event.get("tool_input") or {}).get("command", "")
    cwd = event.get("cwd") or ""
    if not command.strip():
        answer("allow", "jev-gate: no command to classify")

    for pattern in HARD_BLOCKS:
        if pattern in command:
            answer("deny", f"blocked by deterministic rule: {pattern}")

    try:
        from jev import Choice, Noul, decide
    except ImportError as exc:
        answer("ask", f"jev-gate: decision layer unavailable ({exc})")

    state = {"command": command, "cwd": cwd}
    if body := script_body(command, cwd):
        state["script_contents"] = body

    try:
        result = decide(
            state=state,
            questions={
                "risk": Choice(
                    instructions="What happens if `command` runs inside `cwd`?",
                    criteria=RISK,
                ),
                "reversible": Noul(
                    instructions="This command can be undone without cost.",
                ),
            },
            timeout=5.0,
        )
    except Exception as exc:  # noqa: BLE001 -- any failure must fail to `ask`
        answer("ask", f"jev-gate: {type(exc).__name__}: {exc}")

    risk = result.answers["risk"]
    reversible = result.answers["reversible"].noul or 0.0
    trace = f"jev: {risk.choice} {risk.confidence:.2f} (reversible {reversible:.2f}, {result.latency_ms:.0f}ms)"

    if risk.choice in ALWAYS_ASK:
        answer("ask", f"{trace} -- policy: always confirmed")
    if risk.choice in ("read_only", "local_edit") and (risk.confidence or 0) >= TAU:
        answer("allow", trace)
    if risk.choice == "destructive" and (risk.confidence or 0) >= TAU:
        answer("deny", trace)
    answer("ask", f"{trace} -- below tau {TAU}")


if __name__ == "__main__":
    main()
