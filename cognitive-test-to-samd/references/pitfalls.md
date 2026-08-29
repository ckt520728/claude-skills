# Pitfalls

Observed on a real programme (NeuroPlay → NeuroPlay Clinical, Taiwan, 2026-08).

## 1. Search summaries omit the sentence that decides the case

Two rounds of web search on "is medical software a medical device" returned only
general principles. **Not one mentioned "mental acuity"** — the exact phrase that
places brain-training software in the guideline's explicit exclusion list, and
the single most decision-relevant sentence in the whole project.

It was found by downloading the guidance PDF and grepping the extracted text.
Note that PDF-reading tools may refuse the file while still saving it locally.

```bash
python extract.py guide.pdf > g.txt     # pypdf; write a .py file, see §9
grep -n "認知\|健康管理\|排除" g.txt
```

**Rule: for law, standards, and contracts, always obtain the primary text.**
Search is for finding *which* document exists, not for what it says.

## 2. "The data are collected" is not one claim but three

Research-complete, engineering-complete, and regulatory-complete are different
thresholds. See [evidence-conversion.md](evidence-conversion.md).

## 3. The plan cannot see what the submission document sees

Three revisions of a project plan missed that the normative strata covered
schoolchildren, university students, and over-65s — **but not 26–64 year-olds**.
It surfaced within a minute of drafting the intended-use population sentence.

**Rule: draft one section of the final deliverable early and use it as a
planning checklist.** A Gantt chart never asks "who is this for, exactly".

## 4. Removing a 14-month task saved only 6 months

The normative study ran parallel to the QMS track, so removing it mostly exposed
other work rather than shortening the programme. Worse, the saving **moved the
critical path** from the research track to QMS — which changed the hiring
priority (from coordinators to QA/RA and test engineering) and promoted
unit-test work from "eventually" to "every week of delay is a week of launch
delay".

**Rule: after any schedule change, re-derive the critical path before reporting
how much time was saved.**

## 5. When "conditional" becomes "certain", the cost hides in the slack

A confirmed retest study left the launch date unchanged but cut the buffer
before submission from 5 months to 2. Reporting "no schedule impact" would have
been technically true and materially misleading.

**Rule: report remaining slack, not just milestone dates.**

## 6. Treating the wellness product as the starting point of a migration

The instinct is "add norms to the existing app". That silently converts a
lawfully unregulated product into an unapproved medical device. Fork into two
tracks and write the non-contamination rule into the project instructions.

## 7. Academic endorsement is advertising

Advertising for medical devices requires **pre-publication approval** in Taiwan
(管理法 §41). A research centre's name on a launch page, press release, or
conference material can fall within that scope. Academic teams do not expect
this and discover it at marketing time.

**Rule: put an advertising-review clause in the collaboration agreement at
Phase 0**, not at launch.

## 8. Assuming a novel product defaults to low risk

Taiwan's 分類分級管理辦法 §4 classifies anything outside a listed item's
identification scope as **Class III**. A genuinely novel instrument is therefore
*more* burdensome by default, not less. This is precisely why the individual
classification ruling is the highest-value early step.

## 9. Environment traps seen while doing this work

Not domain-specific, but they cost real time:

- **`npx` for an MCP stdio server.** A globally installed package still gets
  re-resolved from the registry on every launch, pushing cold start to the
  health-check timeout and producing intermittent "failed to connect". Invoke
  the installed entry point with `node` directly.
- **Python heredocs on Windows.** Piping source to the interpreter
  (`python - <<'PY'`) reads stdin using the system locale, not UTF-8, so
  non-ASCII source becomes mojibake. Write a `.py` file instead — file reads
  default to UTF-8. Writing *data* files with a quoted heredoc is fine; the trap
  is only piping source code.
- **Anchor-based text patching.** Assert every anchor exists *before* writing
  anything, and never assume an anchor sits at the start of a line.
- **A failing remote service is not necessarily down.** Probe the permission
  ladder — unauthenticated, bad credential, good credential — to localise the
  fault to a layer before concluding anything or editing local config.
