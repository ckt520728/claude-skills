---
name: reference-anchor
description: When describing what you want would be lossy or take forever, hand Claude a concrete reference instead — source code, a library, a URL, a screenshot, a doc — and have it read the reference and reproduce its behavior or semantics in your context, rather than working from a natural-language description. Use when you catch yourself trying to explain "make it work like X" in prose, when you already know of an implementation that does the right thing, or when the target has a taste/style dimension words won't capture.
---

# Reference Anchoring

Natural language is a lossy compression of whatever you actually have in mind. If a concrete reference exists — code, a doc, a live example — pointing at it transmits far more information per word than describing it, and removes an entire round of guessing.

## Pick the highest-density anchor available

In roughly this order of information density:

1. **Source code** — the exact implementation, including the edge cases you'd forget to mention.
2. **Structured docs / API schema** — precise but doesn't show behavior in context.
3. **A live example to fetch** (a webpage, an app) — Claude can read the underlying markup/structure, not just a description of how it looks.
4. **A screenshot** — visual only, loses interaction and structure.
5. **Prose description** — last resort; use it to point at one of the above, not as the anchor itself.

If you're about to write a paragraph describing an algorithm, a UI interaction, or a piece of writing's voice, stop and ask: is there something that already does this I could point at instead?

## Say what should transfer

Be explicit about what to take from the reference and what not to: usually the **semantics** (algorithm, behavior, structure, voice) should transfer, while literal branding, copy, or license-encumbered content should not. "Read `vendor/rate-limiter`'s backoff logic and reimplement the same semantics in our TypeScript client" is precise; without the "same semantics, new implementation" framing, Claude may either copy too literally or drift too far.

This applies past code: a blog's argument structure, a competitor's onboarding flow, a designer's spacing system are all valid references — point Claude at the source (the page, the repo, the doc) rather than trying to describe the pattern yourself.

## Check the read before the build

Before Claude starts implementing against the reference, have it restate back what it extracted — the semantics it thinks it should carry over. This is a cheap comprehension check: it catches a misreading of the reference before that misreading gets built into working code, not after.
