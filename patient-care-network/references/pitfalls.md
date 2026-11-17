# Pitfalls (measured, Smart Diabetes Care Network v2, Windows 11, 2026-11-17)

## Sources and evidence

1. **A private GitHub folder returns 404 to web fetch.** Use `gh api repos/<owner>/<repo>/git/trees/<branch>?recursive=1`. The "preliminary codebase" there was a byte-identical mirror of the local project, so compare file sizes before planning a merge.
2. **Notebook answers can be huge (50 KB) and won't print on cp950.** Parse the saved JSON and print with `PYTHONIOENCODING=utf-8`.
3. **Reference notes contain wrong code.** Examples: KFRE divided eGFR by 10, an old SSE API, and a sync/async DB mismatch. Treat notes as design input, not code.
4. **Never transcribe a published equation from memory alone.** SCORE2-Diabetes coefficients were checked term by term against an independent implementation (RiskScorescvd), and its worked example (8.4 %) is pinned in a test.
5. **The calibration region may not include your country.** Taiwan is not a SCORE2 region, so the region is configurable and every result is labelled.

## Engines and tests

6. **When a test fails, check the test first.** A meal-response test expected the reading 30 minutes before the meal as baseline; the correct baseline is the reading at meal time. Fix the expectation, not the engine.
7. **Mixed timezones break time matching.** CGM devices send naive local time; server events are UTC with an offset. Normalise both with one `to_local_naive()`, used by AGP binning, meal matching and the CGM rules.
8. **A missing smoking status must make SCORE2 `not_calculable`.** Store it as an explicit 0/1 condition row; a missing row means unknown.

## Guardrail

9. **Sentence splitting separated citations from their claims.** Text like "…一次。[wiki:x]" put the citation on the next "sentence". Do not split when a `[wiki:` follows the punctuation, and do not split on ；.
10. **Headings were flagged as uncited claims.** Skip `# ...` lines and lines that are only `【...】`.
11. **Number grounding was too permissive.** "eGFR 31" passed because a past meal's delta was 31.2. Three fixes:
    - label-aware checks against the right field;
    - matching at the draft's own precision;
    - excluding raw history (CGM series, AGP bins, lab history, diet logs, per-meal results) from the pool.
12. **Clock times parsed as numbers.** "12:45" produced an ungrounded "45". Strip times and dates before grounding.
13. **The pipeline cited a draft page and failed its own guardrail.** Auto-generated text must cite verified pages only.
14. **Simulated speech-to-text was auto-accepted.** Cap confidence for any simulated adapter (`mode` or `stt_mode` starting with `demo`) so it always goes to a human.

## MCP

15. **HTTP 421 "Invalid Host header".** MCP SDK DNS-rebinding protection allows only localhost, which blocks the TestClient's `testserver` and LAN agents. Set `allowed_hosts` and `allowed_origins`; keep the protection on.
16. **The MCP session manager can only start once.** Two test modules, each with its own session TestClient, fail. Move the fixture to `conftest.py`.
17. **A helper called as `_audit_mcp(action, chart_number=..., chart_number=...)`** raised "got multiple values for argument". Name the positional parameter differently from detail keys (`patient_ref`).
18. **Dict tool results often arrive as text content, not `structuredContent`.** Clients and panels must fall back to parsing `content[0].text`.
19. **Claude Desktop (Microsoft Store build) does not read `%APPDATA%\Claude`.** It reads `%LOCALAPPDATA%\Packages\Claude_<id>\LocalCache\Roaming\Claude\claude_desktop_config.json`; `main.log` shows the exact path. `Claude-3p` is a different profile.
20. **Claude Desktop needs stdio.** A 100-line httpx bridge avoids an npm download and re-initialises when the server restarts (404 on an unknown session).

## Performance and platform

21. **SQLite on a synced or network drive (Google Drive G:) cost about 60 ms per connection.** `/api/patients` took 5.5 s and the tests took 43 s. A per-thread connection cache plus `close_all()` before reset brought this to under 1 s and 14 s. Windows cannot delete an open database file, so close before reset.
22. **`PRAGMA journal_mode=WAL` on every connect is wasted.** WAL persists in the file; set it once in `init_db`.
23. **Git Bash heredocs with CJK text and quotes failed** ("unexpected EOF while looking for matching `'`"), sometimes after partially running. Write files with the editor tools or a script file. Verify what landed before retrying.
24. **`uv run --with pkg` crashed on a cp950 `.pth` decode.** For a one-off dependency, use `pip install --target <scratch>/libs pkg` and set `PYTHONPATH`; this leaves the project venv untouched.
25. **Copying Windows files into a Linux-authored repo marks every file modified.** Use `git config core.autocrlf true` before `git add`.

## UI verification

26. **The browser window would not resize to 390 px** (maximised window), and an iframe test was blocked by the app's own `frame-ancestors 'none'`. Use headless Chrome over CDP with `Emulation.setDeviceMetricsOverride(390, 844, mobile=True)`, then assert `scrollWidth == clientWidth` per page and save screenshots.
27. **Fixed sleeps captured the previous page.** Renders took longer than 2.5 s on the slow drive. Wait for page-specific content, or fix the latency first.
28. **A mobile CSS rule `.nav-item span:last-child {display:none}` broke** when a badge span was appended: the label reappeared. Hide by a semantic selector (`span[data-i18n]`).
29. **Extend a working vanilla-JS app with hooks, not a rewrite.** Three hooks in the existing `app.js` route, patient-render and LINE-render, plus a separate `app-v2.js`, kept every v1 test green.
31. **A dashboard row rendered twice on a fresh load.** With no `#/` hash, `enterApp()` set `location.hash` (which fires `hashchange` -> `route()`) and then also called `route()`, so an add-on hook inserted its strip twice. Return after setting the hash, and make every insert-style enhancer idempotent: remove what it inserted before re-inserting.
32. **The fix was deployed but Chrome kept running the old JS.** Static files were served with `Last-Modified` and no `Cache-Control`, so Chrome heuristically cached `index.html` and its `?v=` script URLs; plain navigations (transfer size 0) skipped the server. Send `Cache-Control: no-cache` for dashboard files (ETag revalidation is cheap) and `no-store` for `/api`. Bump `?v=` on every JS change. When verifying, check the code that is running (`String(fn).includes(...)`, `performance.getEntriesByType('navigation')[0].transferSize`), not only what the server returns; users who loaded the old page need one Ctrl+Shift+R.

## Operations

30. **The uvicorn server started from an agent session stops when the session ends**, and an in-process scheduler would run once per worker. Document the manual start command; use one worker or move the scheduler out of process.
