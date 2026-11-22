---
name: linked-seminar-deck
description: |
  Build (or revise) a ~30-slide interactive HTML seminar deck plus an editable PPTX that presents one piece of research work
  and links out to its companion web assets: a 3-D interactive site, a homepage blog post, a code repository and demo panels.
  Covers the whole loop: collecting the reference folder, writing the /goal prompt, fetching the SOIL deck skills,
  assembling the deck from slide fragments, a two-version workflow (v1 confidential / v2 shareable) with a leak scan,
  rendering checks, publishing as a private Artifact, and fixing math (KaTeX) on the linked blog.
  Use when the user says "present my work on reading/reviewing a paper", "lab seminar deck with interactive panels",
  "revise the deck so it doesn't reveal the manuscript", "version 2 of my deck for lab members", "HTML + PPTX deck linking my 3-D site and blog",
  「做一份連到我網站與部落格的互動簡報」「審稿心得簡報，但不能透露稿件細節」「改版成可以分享給實驗室的版本」.
  Not for a full research publication pack (use research-3d-publication-pack) or a deck with no companion sites (use soil-html-deck directly).
---

# Linked seminar deck (HTML + PPTX, linked to the companion sites)

This skill orchestrates; slide design comes from the SOIL skills. It adds what the 2026-11 HHSA review-deck run needed:
the reference intake, the /goal contract, a fragment-based build that survives slide removal, a confidentiality pass,
link wiring between the deck, the PPTX and the companion sites, and the verification gates.

Read before starting:
- `references/goal_prompt_template.md`: the /goal prompt to fill in (or to parse the user's one against).
- `references/pitfalls.md`: the failures from the first run, each with the check that catches it.

## 0. Fetch the design skills

The /goal names the SOIL skills by GitHub URL. Read them from the local clone of `ckt520728/claude-skills`
(`git pull` first) instead of web-fetching:
- `soil-deck-pipeline/SKILL.md`: the orchestration and the Windows / python-pptx pitfalls (`docs/windows-build-pitfalls.md`).
- `soil-html-deck/SKILL.md`: the single-file HTML deck contract (keys, overview, `#N` deep links, base64 images).
Follow their SOIL outline (Story / Objective / Insight / Logic) for the narrative. Do not copy their image-generation step
when the user supplies infographics.

## 1. Collect references (data intake)

The user usually gives five kinds of input. Inventory each one into `specs/sources.md` before writing a slide:

| Input | Typical form | What to take from it |
|---|---|---|
| Reference folder | `Reference/Ref for <version>/`: NotebookLM notes (.md), an infographic zip | facts with citations; the infographics (unzip into `assets/`, crop as needed) |
| Case data | CGM AGP export CSV, HRV RR files | recompute every number from the raw file with a script (`make_assets.py`); never from rounded JSON |
| Earlier artifacts | previous deck folder (`Output/<date>_<name>/`) | the v1 template and helpers; **never edit the folder** |
| Companion sites | 3-D site URL, blog URL, code repo URL | link targets; check that each one returns 200 |
| Private sources | NotebookLM notebook, manuscript PDF | background only; **never link them or quote them in a shareable version** |

For every infographic, write one line: use / crop / reject, with the reason. Reject an infographic that shows confidential
numbers, and reject one that contains a factual error (for example a wrong threshold) rather than repeating the error.

## 2. The /goal contract

Restate the user's /goal as a checklist in `specs/outline.md` and keep it ticked as you go:
slides to remove (by original number), concepts to keep, new discussion sections, the case study, the closing sections,
the slide budget (about 30), the outputs (HTML + PPTX, the version label), and "preserve the original artifacts".
Map each original slide number to a stable key **before** removing anything (§3).

## 3. Build: fragments, not slide numbers

```
<new>/build/
  assemble.py        # v1 template + new_slides.html -> deck_template.html   (scripts/assemble_from_template.py)
  new_slides.html    # new slides, each preceded by <!--@key-->, plus <!--@js--> for their INIT code
  build_deck.py      # inline {{IMG:name}} as base64 and data placeholders -> output/<Deck>.html  (scripts/build_deck.py)
  pptx_slides.py     # PPTX slides; reuse the v1 helpers (scripts/pptx_link_helpers.py)
```
- Slice the v1 template by its `<!-- ============ N TITLE` markers into a dict by number.
- Give every interactive slide a `data-key`, and key the JS init table by key (`INIT.mixer=`), **not** by position (`INIT[13]=`).
  After removal, assert that no `INIT[<number>]` remains.
- Text edits on kept slides go through `sub(text, [(old, new), ...])`, which asserts each `old` exists. Silent no-op replaces are the main way leaks survive.
- `ORDER = [...]` is the single place that defines the deck. Mix keys of new slides and v1 numbers.
- Leave the v1 folder byte-identical: write v2 into a new dated folder, and check the v1 modification times at the end.

## 4. Two versions: confidential v1, shareable v2

When the work is a manuscript under review (or otherwise embargoed):
- v1 can carry the manuscript ID, figures and numbers; label it "Confidential" and keep its Artifact private.
- v2 removes the manuscript at-a-glance, its figures, its result numbers (AUCs, p-values, feature-importance shares), the cohort name,
  the author names and the private notebook link. Keep the *concept*; teach it with your own data and synthetic demos.
- Banner: "Lab seminar · unpublished work · please do not redistribute".
- Run `scripts/leak_scan.py` on the HTML **and** the PPTX with a term list (manuscript ID, cohort, journal, author surnames,
  each reported result number, "manuscript's", the case patient's real name). The build must stop on any hit.
- Panels linked from the deck count as part of the deck: scan them too, and drop any that cannot be cleaned.

## 5. Content pattern for "new method vs conventional metrics"

When a talk argues that a new signal feature (for example physiologically constrained frequency bands) beats the conventional metrics:
1. Concept slide: what the feature is, using an infographic.
2. Why these bands: the physiological evidence, with citations.
3. Interactive demo: two synthetic profiles with **identical** conventional metrics (TIR, CV, TAR within 0.1) but different band energy.
   Tune the profiles with a script and assert the match.
4. Conventional metrics: consensus targets vs the case (interactive), then their outcome evidence (tabs: micro- and macrovascular).
5. Classify ≠ predict: the new feature separates groups; only the conventional metrics have outcome evidence. Say it can't replace them.
6. Future work: prospective outcomes, external validation, sampling-rate limits.
7. Then the case study, the extension (HRV), the 3-D site, the care network, and a call-to-action slide with every link.

## 6. Links: deck ⇄ PPTX ⇄ companion sites

- In the HTML deck, use buttons with `target="_blank" rel="noopener"` to the 3-D site, the blog, the repo and the local `panels/*.html`.
  Ship `output/panels/` next to the deck, or upload them with the Artifact `files` map.
- In the PPTX, each interactive slide gets an "▶ Open interactive slide" button pointing to `<artifact URL>#<n>`.
  **Publish the HTML first**, then put its URL and the final slide count into `build_pptx.py`, and rebuild if the order changes.
- The last slide lists every link. Check each link (HTTP 200, and the `#N` lands on the right slide).

## 7. Verify (gates)

| Gate | How |
|---|---|
| Slide count and order | count `<section class="slide`; compare against the /goal checklist |
| Each slide renders | headless Chrome screenshots of `?shot#N` for every N; look at each one |
| Interactive slides work | `--dump-dom` after init; the numbers shown equal the script's output |
| Numbers | every number on a slide comes from `make_assets.py` output on the raw file |
| Leak scan | `leak_scan.py` on HTML, PPTX and panels: 0 hits |
| PPTX | export to PNG through PowerPoint COM (or LibreOffice) and look; no overflow, links clickable |
| v1 preserved | modification times of the v1 folder are unchanged |

## 8. Publish and hand over

- Publish v2 as a **new** private Artifact (never overwrite v1's URL), and tell the user that v1's link still shows the confidential deck.
- Write `README.md` in the v2 folder: the files, the changes from v1, the rebuild commands, the sources and the rejected infographics.
- When a linked blog shows raw `$...$`, add KaTeX auto-render (`templates/katex_head.html`), use `$$` for display math,
  push from a local clone outside Google Drive, and poll the Pages URL until the new version is live.
