---
name: comprehension-quiz
description: Before merging or accepting agent-produced work, have Claude write a short decision report (what changed, why, and which calls were judgment calls) and then quiz you on it — you must answer correctly before the work is considered accepted. Use when a change is nontrivial enough that skimming the diff isn't real review, when you've caught yourself rubber-stamping agent output, or when the user says "quiz me" / "make sure I understand this before I merge".
---

# Comprehension Quiz

This is not a trust mechanism and not a gotcha — it's a knowledge-digestion step. Its purpose is to stop a human from silently losing ownership of code or output they never actually understood, which is the real risk of agent-produced work: not that it's wrong, but that no one who can catch it wrong actually read it.

## When to run it

Right after implementation, before merge / accept / ship. Reserve it for changes complex enough that "did I actually understand this" is a real question — skip it for trivial or purely mechanical changes, where it's just friction. Two reliable triggers: the user explicitly asks for it, or the change turned out substantially bigger than they expected going in — that gap is itself a sign a diff-skim won't be enough. A diff only shows the lines that moved; it doesn't show how much of the actual behavior rides on code paths that didn't change at all, which is exactly what a skim misses and a quiz catches.

## Step 1 — Decision report ("the pitch")

Claude writes a short summary, structured for someone who wasn't in the room:

- **What changed**, in plain terms.
- **The judgment calls first** — front-load anything that required a decision Claude had to make, especially ones logged in a [[deviation-log]] if one exists. This is the part most likely to hide an unwanted assumption; it goes first, not buried at the end.
- **The mechanical parts last** — routine execution the human doesn't need to scrutinize.

Write it as a pitch to a stakeholder, not a changelog: it should make the case for why each judgment call was reasonable, not just list that one was made.

## Step 2 — The quiz

1–3 questions targeting the most consequential or least obvious decisions in the change — never trivia. A good question is one where a wrong answer means the human's mental model of what shipped is actually off, not one where a wrong answer just means they forgot a detail. Multiple-choice or short-answer, whichever makes a wrong answer detectable.

## Step 3 — Grade and gate

- **Correct** → the work is accepted; proceed to merge/ship.
- **Incorrect** → don't just supply the right answer. Explain *why* the human's expectation was off — that's the actual gap this step exists to catch. Re-quiz, or offer to walk through the change before it merges, human's choice.

## Calibrating cost

The report-plus-quiz overhead is worth paying when skimming a diff wouldn't actually tell the human what they need to know. It's not worth paying on a one-line fix or a change with no judgment calls in it at all.
