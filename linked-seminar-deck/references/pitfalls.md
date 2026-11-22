# Pitfalls (2026-11 review-deck run) and the check that catches each

| # | What went wrong | Why | Fix / gate |
|---|---|---|---|
| 1 | Interactive slides stopped working after slides were removed | JS init was keyed by slide number (`INIT[13]=`), so every later slide shifted | `data-key` on each section, `INIT.key=`; assert no `INIT[\d+]` remains |
| 2 | A text replacement silently did nothing, and the manuscript phrase survived | `str.replace` on a string that had changed upstream | `sub()` asserts each old string is present |
| 3 | Manuscript numbers survived in JS strings (chips, tooltips, quiz feedback) | the leak edit only touched the HTML body | leak scan the whole file, including `<script>`, and the PPTX and panels |
| 4 | Linked panels still carried the manuscript ID, author names and AUCs | panels are separate files, outside the slide scan | scan `panels/`; drop panels that can't be cleaned |
| 5 | Infographics showed confidential AUCs, and one mislabelled TAR (>160 instead of >180 mg/dL) | supplied images were used without reading them | one use/crop/reject line per infographic in `specs/sources.md` |
| 6 | Case metrics on one slide disagreed with another slide | one was computed from rounded JSON, the other from the raw CSV | compute once from the raw file; hard-code from that script's output |
| 7 | The "same TIR, different bands" demo did not actually have the same TIR | profiles were hand-tuned | tune with a script and assert TIR/CV/TAR within 0.1 |
| 8 | The PPTX "open interactive slide" buttons pointed to the wrong slides | the PPTX was built before the HTML order was final | publish the HTML, then set `HTML_URL` and `TOTAL` and rebuild the PPTX |
| 9 | A sed edit mangled a regex in the build script | shell escaping of `\d`, `\[` | edit Python with Python (or the Edit tool), not sed |
| 10 | A `&&` chain stopped halfway, so the output kept the old name | PowerShell 5.1 has no `&&`; Git Bash chains stopped on an earlier failure | run steps separately and check each output file's timestamp |
| 11 | The blog showed raw `$S(t,f_c)=\int...$` | the page had LaTeX but no math renderer | KaTeX 0.16.9 auto-render from cdnjs (`templates/katex_head.html`) |
| 12 | After adding KaTeX, plain parentheses in labels became math | in a JS string literal `"\("` is just `(`, so `(`…`)` became a delimiter | only `$$` and `$` delimiters; or write `"\\("` |
| 13 | `\right]` broke display math | it contains `\]`, the display delimiter | use `$$...$$` for display math |
| 14 | Patching a CRLF file with Python failed to match | `\r\n` line endings, and `\t` inside a normal string became a tab | raw strings, and normalise line endings before matching |
| 15 | git refs broke when pushing from the Google Drive copy | Drive writes `desktop.ini` into `.git/refs` | push from a clone outside Drive; copy the file across |
| 16 | The page looked unchanged after the push | GitHub Pages takes a minute or two, and the browser caches | poll the live URL for a marker string; tell the user to press Ctrl+F5 |
| 17 | The v1 Artifact link still showed the confidential deck | v2 was published as a new artifact (correct), but nobody said so | say so in the hand-over; delete v1 only if the user asks |
| 18 | The private NotebookLM link was in the shareable deck | it was copied over with the slide | add the notebook URL to the leak-scan terms |
