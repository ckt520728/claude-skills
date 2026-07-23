---
name: deviation-log
description: Protocol for letting Claude execute a long or multi-step task autonomously without stalling at every edge case — it writes down the assumption behind each nontrivial step before acting on it, defaults to conservative choices when reality doesn't match the plan, and keeps a running deviation log so you can review the trail afterward instead of being interrupted mid-flight. Use when kicking off a task you want run to completion unattended, when a previous run stalled repeatedly on minor edge cases waiting for confirmation, or when the user says "keep a deviation log" / "don't stop, just log it and keep going".
---

# Deviation Log

The failure mode this fixes: an agent either stops on every minor surprise waiting for a human (destroying the point of running it unattended), or silently picks something and drifts from the actual intent without leaving a trail. The fix is neither — write the assumption down, act on it, keep moving, make it reviewable later.

## Setup

Before execution starts, create (or reuse) a log file — `implementation-notes.md` or `deviation-log.md`, placed next to the code or in a scratch location. Write the goal and, if there is one, the exit condition at the top: what "done" looks like, so mid-run judgment calls can be checked against it.

## While executing

**Before each nontrivial step**, write one line stating the assumption behind it — not a narration of what the code does, the *assumption* ("assuming the API returns UTC timestamps"; "assuming this table is append-only"). This makes a mid-run stop legible: whoever reads the log later can see exactly what was believed to be true at each point, not just what happened.

**When something doesn't match the plan** — an API changed, a type conflict shows up, an input is ambiguous, a dependency is missing:

1. Default to the **conservative** option: smaller blast radius, reversible over irreversible, matches the codebase's existing convention over inventing a new one.
2. Log it: what was expected, what was found, what was chosen, why, and what the discarded alternative was.
3. Keep going. Don't stop and wait for a human by default.

**Exception — stop and ask anyway** when the situation is:

- **Destructive or irreversible** (data loss, a force-push, deleting something not obviously disposable).
- **A genuine judgment call with no safe conservative default** — both options are real changes to the intent, not just an implementation detail.
- Something that would **silently change what the spec actually asked for**, not just how it's achieved.

The log doesn't replace judgment about when to stop; it's what makes it safe to *not* stop everywhere else.

## When done

The deviation log is not throwaway. It becomes:

- Input to [[comprehension-quiz]] or a pitch — the log is exactly the material for "here's what needed judgment calls."
- A trigger to re-spec: if deviations piled up enough that the original plan no longer matches reality, that's a signal to revise the plan, not just patch around it.
- Durable knowledge for next time — each logged deviation is a gap in the original map that's now closed for future tasks in this area.
