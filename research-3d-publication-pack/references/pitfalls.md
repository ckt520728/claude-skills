# Pitfalls from the HHSA 3-D run (2026-10-17/18): check every one

Each entry gives the symptom, the cause, and the gate that would have caught it.

1. **Low-tier workers fabricated the results.**
   - Symptom: hand-typed cubes (48 or 20 evenly spaced cells with round values) and a helper script that painted blobs at the truth, making "100% recovery" true by construction. The QC JSON did not match the code.
   - Cause: the real pipeline failed its own `assert recovery >= 90%`, so the worker routed around it.
   - Gate: the orchestrator reruns the pipeline itself and diffs the outputs. An acceptance target that is missed is *recorded* as FAIL, never asserted into a crash. Tiers are fixed: jev-planner on high; every executor task on jev-executor-medium. jev-executor-low is never used.

2. **The explorer was blank: Three.js addons imported from the CDN without an import map.**
   - Error: `Failed to resolve module specifier "three"`.
   - Gate: an import map in every page that loads a module, and the smoke test.

3. **35 explorer classes and 11 hero classes had no CSS.**
   - The worker's QA only looked at JS errors.
   - Gate: the `audit_deliverables.py` CSS check, and a screenshot of every page.

4. **Contract drift.** The JSON key was `H` but the reader looked for `H_b64`, so it fell back silently to sparse data.
   - Gate: a contract test, and a reader that fails loudly.

5. **Blender axes.** Z-up becomes Y-up on glTF export: (x, y, z) → (x, z, -y). A plain ×5 scale left the model misplaced.
   - Fix: rotate +90° about X and translate.
   - Gate: the gold truth ridge must sit on the computed energy.

6. **`renderer.setSize(w, h)` pinned the canvas at 300×150.**
   - Fix: `setSize(w, h, false)` plus a `ResizeObserver` on the container.

7. **`file://` silently breaks ES modules and `fetch()`.**
   - Fix: a visible notice and a `start_local_server.bat`.

8. **Two folder layouts.** The working layout is `site/ deck/ paper/`; the repo layout is `<site_dir>/ slides/`. Links broke locally or in the repo.
   - Fix: `data-alt` with a HEAD probe for buttons; `stage_to_repo.py` rewrites the deck paths.

9. **Invented author metadata.**
   - Examples: the wrong hospital, university and email, a fake "consortium", a fabricated NSTC grant, and an AI disclosure claiming "copy-editing only".
   - Gate: these come only from the user's homepage or the user; otherwise use a yellow placeholder.

10. **The DOCX was full of raw Markdown and LaTeX.**
    - Examples: `**`, `$^{1}$`, `[@key]`, and image paths instead of figures.
    - Fix: `md_to_docx.py`. Gate: convert to PDF and read it; the markup scan must be clean.

11. **The methods text did not match the code.**
    - The paper said CEEMDAN, 30 s at 100 Hz and 5% edge trimming. The code ran EEMD + EMD on 300 s at 4 Hz with no trimming.
    - Gate: §5 parameters are copied from the facts file or cube params.

12. **Hard-coded paths into another agent's mirror folder.** Scripts read and wrote outside the project.
    - Gate: all paths relative to `__file__`. Grep for `C:\\Users\\` before accepting.

13. **Google Drive `desktop.ini` broke git.**
    - Error: `fatal: bad object refs/desktop.ini`.
    - Fix: `stage_to_repo.py` cleans them out. Better still, clone outside Drive.

14. **Windows quirks.**
    - Python 3.9 misreads long multibyte lines as "Non-UTF-8". Run such scripts through `exec(compile(open(f, encoding='utf-8').read(), f, 'exec'))`.
    - Backslash paths inside heredocs become `\U` escapes. Write the script to a file instead.
    - Word locks an open DOCX (PermissionError). Build a preview copy, or ask the user to close it.
    - PowerPoint COM needs absolute paths.
    - `print()` of CJK text to the console fails on cp950. Set `PYTHONIOENCODING=utf-8`.

15. **Buffered writes.** `os.path.getsize()` right after `json.dump(open(f, 'w'))` reports a partial size. Use `with open(...)`.

16. **Citation hygiene.**
    - A guideline (PRISMA-ScR) was cited to unrelated papers.
    - A BibTeX year contradicted its key (Baek2015 had year 2021).
    - Gate: a key-year check, and a spot-check that each claim is supported by its cited source.

17. **Overclaiming from demos.**
    - Examples: "RSA clearly resolved", "phase-locked", "vagal reset" on n = 1 or 7-minute data where the real cube was LF-dominant and about 20% of its energy was unresolvable.
    - Gate: every claim about a demo is descriptive, quantified from the facts file, and paired with a "cannot claim" statement.

18. **Regex backreferences lost when patching code from a heredoc.**
    - Symptom: `\1` written through a normal Python string became byte 0x01. The "de-duplicate URLs" rule in `stage_to_repo.py` turned into a pattern that deleted every `'quoted',` token in the deck.
    - Gate: write patch scripts with a file tool using raw strings (`r'''...'''`), and run `grep -rl $'\x01'` over edited files.
    - After any change to the staging script, re-stage into a fresh clone of `main`. `git diff --ignore-cr-at-eol --stat` must be empty when nothing changed.
