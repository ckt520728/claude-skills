---
name: verify-with-rubric
description: Spin up a separate, context-isolated sub-agent to verify agent-produced work against an explicit rubric, instead of asking the same agent (or a quick glance) to grade its own work. Use when the output is subjective or non-deterministic — a video clip, a design direction, a piece of writing — and "is this good?" has no unit test, when you're about to trust an agent's self-assessment of its own output, or when the user says "verify this against a rubric" / "check this independently".
---

# Verify With Rubric

Models grading their own output are lenient on it — self-referential bias. The fix isn't a better self-check prompt; it's decoupling the grader from the producer entirely, so the grader has no context that makes it want the output to be good.

## Step 1 — Write the rubric before generation

Define what "good" looks like in checkable terms, even for subjective work — "clip is under 60s," "hook lands in the first 3 seconds," "no mid-sentence jump cuts," "matches the reference site's spacing scale within X." Write this *before* the work is produced. A rubric assembled after the fact tends to get shaped around whatever the output already is, which defeats the point.

## Step 2 — Producer generates

One or more agents produce the candidate work as normal.

## Step 3 — Independent grading, decoupled context

A **separate sub-agent with no shared context with the producer** grades strictly against the rubric and returns pass/fail per item plus specific feedback — not a vibe score, not "looks good to me." Concretely, in this harness: use the `Agent` tool with a fresh (non-`fork`) subagent for the verifier, or the `Workflow` tool's adversarial-verify pattern when grading several candidates in parallel — a `fork` inherits the producer's context and reintroduces the exact bias this is meant to remove.

## Step 4 — Feed feedback back, don't regenerate blind

On a fail, hand the producer the specific per-item feedback for another pass. Don't just say "try again" — that wastes the verifier's diagnostic work.

## Step 5 — Scale to N candidates when it's a selection problem

If the task is "generate several options and pick the best" (a handful of short-clip cuts, a few design directions), give each candidate its own verification pass against the same rubric rather than grading them all in one shot — each gets full, uncontaminated judgment and a fair share of compute, instead of the grader getting lenient by the third one.

## Where this applies

Not just code review — anything non-deterministic: video edits, copy, design directions, content generation. The rubric is the part that makes "good" checkable; the decoupled context is the part that makes the check honest.
