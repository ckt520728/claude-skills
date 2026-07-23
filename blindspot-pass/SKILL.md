---
name: blindspot-pass
description: Before starting a nontrivial or unfamiliar task, have Claude scan for the gaps in your own prompt — the assumptions, undefined edges, and tacit standards you didn't think to mention — calibrated to what you actually already know. Use before delegating a task you're not confident is fully specified, when you keep needing to say "no, adjust it" without being able to say what "right" looks like, or when the user says "blindspot pass" / "find my blind spots" / "what am I not seeing here".
---

# Blindspot Pass

A blindspot pass is a **scan for gaps, not a first attempt at the work**. Its output is a list Claude hands back to the human — never code, never a draft. Run it before generation starts, not as a rescue after a bad first attempt.

The goal is to teach the person to prompt better, not to make the decisions for them — a good blindspot pass hands back questions and named risks, not a set of choices already made on their behalf.

## Step 1 — Get the human's starting point

Ask (or note, if already stated) what the person already knows and doesn't know about the domain — not the task, the *domain*. "I've never edited video before, but I know code" changes what's worth flagging versus what's already obvious to them. Skipping this step produces a generic list of things the person already knows, which wastes the pass.

## Step 2 — Scan the target

The target is the prompt/spec plus whatever it touches (codebase area, unfamiliar library, tool, format). Look for two different kinds of gap and label which is which:

- **Ambiguities in the instructions themselves** — places where the prompt could reasonably be read two ways, or leaves a decision unmade. (Quadrant 2, known unknowns, once surfaced.)
- **Domain edge cases the person likely hasn't considered** — teach these back, don't just list them. Explain the underlying mechanism and where it actually breaks, concretely: e.g. "Whisper transcription will render long silences as hallucinated phrases like 'thanks for watching', splits single words across two segments sometimes, and has no speaker diarization" — not "transcription may have errors." A named failure mode is checkable; a vague warning isn't.
- **Tacit standards that exist only in the person's head** — taste, house style, "we always do it this way." These aren't bugs in the prompt; they're unknown knowns. Don't guess at them — ask the person to state the standard explicitly, or if it's genuinely a "know it when I see it" case, route to [[prototype]] instead (generate divergent options, let them react) rather than trying to extract a verbal description of an aesthetic.

## Step 3 — Report, don't act

Hand back a short list, grouped by the labels above. Do not start implementing anything the list surfaces.

## Step 4 — Human filters it

The human confirms which findings are real and which are noise. This step is not optional: a blindspot pass can hallucinate a plausible-sounding gap that isn't actually a gap. Baseline domain judgment from the human is still required — this tool finds candidates, it doesn't replace review.

## Step 5 — Fold confirmed items back into the spec

Only the confirmed items become explicit instructions for the actual work. Everything else is discarded.

## When not to bother

Deterministic, well-understood, low-stakes tasks. A blindspot pass on "add a null check" is friction, not signal.
