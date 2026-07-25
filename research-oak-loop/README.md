# research-oak-loop (plugin)

A reusable Claude Code plugin that packages the workflow first run in
`2026 PKM-oak-loop-engineering`: **corpus → verified synthesis → published output**, driven
as an Oak loop with independent maker/checker verification.

It doesn't reinvent the underlying methods — it *orchestrates* them (finding-unknown,
pkm-three-levels, oak-loop-engineering, verify-with-rubric, publish-lab-blog) into one
repeatable pipeline, and bakes in the hardening rules learned from real runs
(`skills/research-oak-loop/references/pitfalls.md`).

## What's inside
```
.claude-plugin/plugin.json          manifest
skills/research-oak-loop/SKILL.md   the master orchestration skill (user-invocable)
skills/research-oak-loop/references/
  pitfalls.md                       the hardening rules (source-quality, paper-identity,
                                    numeric-verify, verbatim-quotes, honest calibration…)
  rigor-rubric.md                   the checklist every synthesis note must pass
  verifier-prompt.md                the decoupled-verifier prompt template
  option-ledger.template.md         the Oak ledger, pre-filled for lit-synthesis
commands/
  distil-cluster.md                 /distil-cluster <cluster>  — one FC-STOMP synthesis pass
  verify-note.md                    /verify-note <path>        — spawn a decoupled checker
```

## Install
Register the plugin's parent directory as a marketplace (or copy the skill folder into
`~/.claude/skills/`). As a `directory` marketplace source:

```
# add plugin/ as a marketplace, then enable research-oak-loop
```

The three referenced local skills it composes (finding-unknown set, pkm-three-levels,
oak-loop-engineering, verify-with-rubric, publish-lab-blog) must also be available; the SKILL
degrades gracefully and tells you which are missing.

## Use
`/research-oak-loop` to start a program from a corpus, or the two commands for the inner
loop. See the SKILL for the full phase map and the non-negotiable human gates.
