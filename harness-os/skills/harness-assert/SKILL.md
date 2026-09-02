---
name: harness-assert
description: Verification phase of Harness OS — check deliverables physically against contracts written in advance, gate publication so nothing unverified reaches the output directory, and handle the subjective deliverables where no cheap automatic verifier exists. Use before declaring any deliverable complete under [[harness-os]], or when work was previously reported done and turned out empty, truncated, or full of placeholders.
---

# Harness Assert

An agent's word that something is finished is not evidence. This phase replaces
it with a file the verifier either accepts or rejects.

```bash
$K assert --contract proposal --round 1     # exit 0 = pass, 1 = fail
$K assertall --round 1                      # every contract
$K publish --contract proposal              # re-verifies, then copies to out/
```

`publish` will not copy a failing artifact. That refusal is the feature.

## What to do with a failure

1. Read the failing checks from the report — they name the problem precisely.
2. Trace it **with a signature**:
   ```bash
   $K trace --job draft --action assert --detail "sections check failed: 經費預算" \
      --status FAIL --signature "missing_section|direct|section_skipped_on_长文截断"
   ```
3. Fix the artifact. Re-assert.
4. If the same contract fails three rounds running, stop patching and go to
   [[harness-mine]] — you are treating a symptom.

**Never weaken a contract to make it pass.** If a contract is genuinely wrong —
it asks for something the user does not actually want — stop and say so. Moving
the target is the user's decision, not yours. The `guard` exists to make a quiet
edit visible.

## Reporting

Report the verifier's verdict, not your intention:

| Contract | Result | Artifact |
|---|---|---|
| `proposal` | PASS | `out/proposal.md` |
| `budget` | **FAIL** — `json_keys` missing `total` | `draft/budget.json` |

If something failed, say so plainly and say what failed. If a deliverable was
skipped, say that too. A green summary over a red verifier is the single worst
outcome this whole system exists to prevent.

## Subjective deliverables

Papers, proposals, blog posts, designs: there is no cheap faithful automatic
check for "is this good". Split the problem.

**Structural layer — contract it.** More is checkable than people assume:

- required sections present (`sections:`)
- length budget (`min_words:`)
- no placeholders or truncation (`no_placeholder`)
- citation markers present and no `[citation needed]` (`regex_present` /
  `regex_absent`)
- cross-document consistency: every instrument named in Methods appears in the
  budget table — a `cmd:` check running a ten-line script
- no duplicated paragraph across sections — again a `cmd:` script
- terminology consistency against a glossary

These catch most of what actually goes wrong in long-form drafts, and none of
them require judgement.

**Judgement layer — [[verify-with-rubric]].** Write the rubric before generation.
Grade with a **separate, context-isolated sub-agent** (`Agent` tool, fresh, not
`fork`). Feed specific per-item failures back to the producer rather than saying
"try again". Grade candidates one at a time, not in a batch.

Hard limit: **an LLM judge is advice, not ground truth.** Never run an automated
improvement loop that optimises against one unsupervised — it will find the
judge's blind spots long before it finds quality. A human sees the rubric result
before anything ships.

## Before merge or accept

For a change big enough that skimming would not be real review, run
[[comprehension-quiz]]: a short decision report with the judgement calls up
front, then 1–3 questions the user has to answer before it is accepted. This is
about the user keeping ownership of work they will have to defend — not a trust
check on you.

## Anti-gaming checklist

- [ ] `guard check` returns `OK` (if `TAMPERED`, every result since the last
      clean check is void)
- [ ] no contract was edited this round
- [ ] `no_placeholder` is on every prose and code deliverable
- [ ] the held-out contract was never used to steer a fix
- [ ] `cmd:` verifier scripts live outside any directory a sub-agent can write

Passing: [[harness-os]] step 7 is not needed — publish and report.
Failing repeatedly: [[harness-mine]].
