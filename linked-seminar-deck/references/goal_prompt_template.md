# /goal prompt template

Fill this in (or check the user's own /goal against it). Every line becomes an item in `specs/outline.md`.

```
/goal I want to present and introduce my work on <reading / reviewing / building> <the work: title>.
<Constraint, if any: e.g. "Because of the journal's editing policy I cannot talk about the manuscript's details.">
The revised version should remove original slides #<a>, #<b>, ... and keep the concept of <core idea>.
Add a discussion of <conventional practice / metrics> and its role in <outcome>, and justify why <new idea> is better at <task>,
while making clear it cannot replace <conventional practice> and needs future work.
Then use a case study: <method> on <case data file>, extended to <second modality>.
Then <companion asset 1: e.g. the 3-D interactive web page>, and finally <companion asset 2: e.g. the care network>.
Use infographics, core pictures from the reference pages, interactive panels, and links inside the slides to the web pages.
Output: an interactive HTML deck of about <N> slides that can be published and shared with <audience>, plus a PPTX, as version <k>.
Preserve the original artifacts.

Skill:
https://github.com/ckt520728/claude-skills/tree/master/soil-deck-pipeline
https://github.com/ckt520728/claude-skills/tree/master/soil-html-deck
https://github.com/ckt520728/claude-skills/tree/master/linked-seminar-deck
Reference:
"<local path>\Reference\Ref for <version>"
3-D site: <URL>
Blog post: <URL>
Previous decks: "<local path>\Output\<date>_<name>"
Code repo: <URL>
Private notebook (background only, never linked): <URL>
```

## What to ask only if missing

- The audience and whether the result may be redistributed (decides the v1 / v2 split and the banner).
- Which original slides to drop, by number, if the user wants a revision.
- Whether the case patient's name may appear anywhere (default: no; use "Case A").

Everything else has a default in SKILL.md; proceed without asking.
