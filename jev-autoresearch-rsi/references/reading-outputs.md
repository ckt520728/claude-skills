# Reading the outputs (verification ladder, step 6)

Automated checks passing is necessary, not sufficient. Read the run as a reviewer would, and turn every problem into a test or a check before calling the run done.

## Run folder

- `progress.md` and the log: which sources were LIVE, how many loops ran, why the loop ended.
- `checks.md`: every node has a verdict and evidence. A FAIL that was followed by a PASS is normal; that is the replan working.
- `audit_loop*.json`: read the medium findings too. They are usually wording-precision issues worth fixing in the next run's prompts.
- `run_report.json` → `kb`: pages created/updated, fitness before/after, and the reason for any drop.

## Paper

- Each headline number traces to an `[E#]` source. Check the claim's *scope*: same benchmark, same denominator, author-run vs independent.
- Secondary sources (NotebookLM answers) are labelled as secondary and never presented as primary results.
- The reference list has no duplicates, no invented DOIs, and no off-topic sources. The engine excludes sources executors flag as `off_topic`; check what it excluded.

## Deck

- 15 content slides (Hook 2 / Concepts 5 / Evidence 5 / Misconceptions 1 / Conclusion 2) plus references.
- At most 5 bullets per slide.
- The PPTX opens cleanly. The HTML deck navigates with the keyboard.

## Blog (zh-TW)

- Terminology: use Taiwan usage, with no Simplified characters (e.g. speculative decoding = 推測解碼, not 推論解碼). Add each wrong term you find to `terms.forbidden`, and the right one to `terms.preferred`.
- No English left in Chinese UI strings, and no truncated chart labels.
- The slug is cut on a word boundary.
- The notice says that automated checks are not expert review.

## Opening the files

On Windows, links to paths with CJK characters or spaces (e.g. `G:\我的雲端硬碟\...`) often fail to open from a terminal. Give the user `http://127.0.0.1:8090/outputs/runs/<run_id>/<file>` instead, or open them with `Start-Process` (PowerShell) or `open` / `xdg-open`.
