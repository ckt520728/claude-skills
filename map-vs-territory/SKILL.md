---
name: map-vs-territory
description: Diagnose why an agent's output missed the mark, or scope out a fuzzy/unfamiliar task before starting, using the "map is not the territory" framework (Thariq Shihipar, Anthropic). What you tell Claude is the map; the codebase/task/reality is the territory; the gap between them is made of unknowns Claude had to guess at. Use when a task feels underspecified, when you're about to delegate something you don't fully understand yourself, or when a previous attempt came back plausible-but-wrong and you want to find out why instead of just re-prompting harder.
---

# Map vs Territory

Your prompt, context, and instructions are the **map**. The codebase, the task's real constraints, the actual environment are the **territory**. Wherever the map is silent, Claude fills in with a guess — and the quality of that guess is the quality of the output. Most "the model didn't get it" complaints are actually "the map didn't say" complaints. This is the entry point / diagnostic for a small family of skills that each close one kind of gap.

The default posture this implies: don't just take the prompt and grind through it. The job is to actively surface known unknowns, unknown knowns, and unknown unknowns — before, during, and after implementation — not to silently guess through them and hope the guess was right.

## The four quadrants

Sort any gap between your map and the territory into one of four buckets (after Rumsfeld):

| Quadrant | What it is | Symptom | Close it with |
|---|---|---|---|
| **Known knowns** | You said it, Claude has it | Works fine | Nothing to do |
| **Known unknowns** | You know there's a decision, haven't made it | You're stalling before you even prompt | Interactive Q&A → [[grilling]] skill; or generate divergent options and react → [[prototype]] skill |
| **Unknown knowns** | You have a tacit standard (taste, convention, "I'll know it when I see it") but never said it | You keep saying "no, adjust it" without being able to say what "right" is | [[blindspot-pass]] to surface it explicitly, or point at a concrete example → [[reference-anchor]] |
| **Unknown unknowns** | Neither of you has thought of it yet | Output is confidently wrong in a way that surprises you | [[blindspot-pass]] before you start; [[deviation-log]] to catch what surfaces mid-execution |

Quadrants 3 and 4 are the expensive ones — you can't just "write a better prompt" to fix them, because by definition you don't know what's missing. That's the whole point of the techniques below: they're mechanisms for *discovering* the gap, not for writing around it.

## How to use this

**Before starting**, if the task is nontrivial or outside your comfort zone: run a [[blindspot-pass]]. If you know a decision is unresolved, use [[grilling]] (interview — prioritize questions whose answers would change the architecture; don't spend the question budget on trivia) or [[prototype]] (divergent options to react to). If you can point to something that already does what you want, use [[reference-anchor]] instead of describing it in prose. Once the unknowns worth removing are gone, write the plan itself as a [[decision-first-plan]] — ordered by what the user is likely to change, not by execution order — so review doesn't turn into a skim.

**While executing** a long or multi-step task: keep a [[deviation-log]] so edge cases get a conservative default and a paper trail instead of a stall or a silent wrong turn.

**Before accepting the output**: for subjective or non-deterministic work (design, content, anything without a unit test), run [[verify-with-rubric]] instead of trusting the producing agent's own read of its output. For anything you're about to merge or ship, run [[comprehension-quiz]] so acceptance requires you to actually understand what changed, not just skim it.

**When an output came back wrong**, before re-prompting: ask which quadrant failed. "I forgot to mention X" is quadrant 2 — just say X next time. "I didn't even know X mattered" is quadrant 4 — that's the one worth a blindspot pass, because it'll happen again on the next task in this domain until you close it.

**Mid-task tension as a trigger.** If an instruction feels torn between two failure modes — following it too literally when a pivot is clearly warranted, versus treating it as vague and filling the gap with generic "best practice" that may not fit this project — that tension is itself a symptom of an unresolved unknown, not something to silently pick a side on. Stop and surface it (ask, or run the relevant technique above) rather than pushing through in either direction.

## Signs it's actually working

- You're asking one question whose answer would change the architecture, not five questions about trivia.
- You're offering a mock or prototype before touching real code when the direction is genuinely fuzzy — not after guessing wrong once.
- Deviations from a plan show up in a [[deviation-log]], not silently in the diff.
- The user can pass a [[comprehension-quiz]] about a nontrivial change before it merges.
- A plan review takes minutes because the load-bearing decisions are up top ([[decision-first-plan]]), not because there was nothing worth reviewing.

If none of these are showing up on a task that's ambiguous or unfamiliar, the discovery techniques aren't being used — not that they weren't needed.

## Cost discipline

This whole family of techniques has real overhead — a blindspot pass, an interview, a reference lookup all cost time before any work starts. It pays for itself on tasks that are genuinely ambiguous, unfamiliar, or expensive to redo. On a small, deterministic, well-understood task, skip straight to prompting — running the full diagnostic on "rename this variable" is friction for its own sake.

## Why bother

Each unknown you close is permanent: it moves from your blind spot into your map, so the next task in that domain starts with fewer gaps. Ten minutes closing an unknown now is usually cheaper than the hours it costs to discover it after the work is already built the wrong way.
