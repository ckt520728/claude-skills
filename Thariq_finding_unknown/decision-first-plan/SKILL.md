---
name: decision-first-plan
description: Before executing a complex multi-step task, write the implementation plan ordered by how likely the user is to want to change it — decisions and user-facing behavior first, mechanical execution last — instead of a flat linear plan the user has to read end-to-end to find what actually needs their judgment. Use before starting a complex task, when a plan review is likely to get skimmed instead of read carefully, or when the user says "write a plan" / "make an implementation plan" first.
---

# Decision-First Plan

A plan written in execution order (step 1, step 2, step 3...) forces the reviewer to read everything at equal attention to find the few decisions that actually matter — so they skim, and skimming is exactly how a bad call slips through review. Order by **decision volatility** instead: what the user is likely to want to change goes first, what they already trust you to just do goes last.

## The split

**Section 1 — top, full attention.** Anything the user is plausibly going to want to change: data models and schemas, type interfaces, public APIs, anything user-facing (behavior, copy, visible output). These are the load-bearing decisions — get them wrong and everything built on top of them is wrong too.

**Section 2 — bottom, skimmable.** Mechanical execution that follows once section 1 is settled: plumbing, internal wiring, refactors, test scaffolding, anything the user already trusts you to handle without review.

## The sorting test

For each item: would the user plausibly say *"no wait, do that differently"*? If yes, it belongs in section 1 — no matter how small it looks. Would they say *"sure, whatever, you know how to do that"*? If yes, it belongs in section 2 — no matter how large it is. Size and section are not the same axis; a one-line schema change can matter more than a thousand-line mechanical refactor.

## Open questions are questions, not guesses

If something in section 1 is genuinely undecided, say so explicitly as an open question rather than silently picking an answer and hoping it's the one the user wanted. A plan that surfaces "I need a call here" is doing its job; a plan that quietly resolves it and buries the choice in prose is not.

## Where this fits

This is the artifact that closes out pre-implementation discovery, once [[blindspot-pass]] / [[grilling]] / [[reference-anchor]] have already removed most of the unknowns worth removing — it's how what's left gets reviewed efficiently rather than skimmed. Whatever is still undecided when execution actually starts hands off to [[deviation-log]].

Format-agnostic: a markdown doc, an HTML artifact, whatever the project already reviews plans as. The ordering principle is what matters, not the medium.
