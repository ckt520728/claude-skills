# Pitfalls (measured, Smart Diabetes Care Network v2 → 0.3, Windows 11, 2026-11-17)

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

30. **The uvicorn server started from an agent session stops when the session ends**, and an in-process scheduler would run once per worker. Document the manual start command; use one worker or move the scheduler out of process. It is also stopped when the machine runs low on memory while the session is idle; that is not a server fault.

## Roles and per-user MCP access (0.3)

33. **`role !== 'admin'` checks gave a new role write buttons.** Adding `dietitian` would have shown it every clinical write button (the server still said 403). Define role groups once on the server and mirror them with named UI helpers (`canWriteClinical`, `canValidateNutrition`).
34. **SQLite cannot widen a CHECK constraint.** `users.role CHECK (... 'admin')` rejected `dietitian`. Rebuild the table in a migration guarded by the stored `sqlite_master.sql`, only when no foreign key references it, and test it on an old-schema database.
35. **The seed runs only on an empty database**, so an upgraded demo had no `demo.dietitian`. In demo mode, call the idempotent `seed_users()` at startup.
36. **Identity must reach MCP tool handlers without a forgeable header.** Store the resolved identity in the ASGI scope under a private key in the bearer gate; read it in an MCP `ServerMiddleware` through `ctx.request.scope`; set a `ContextVar` around `call_next` so handlers can audit `mcp:<username>`. Filter `tools/list`/`prompts/list` after `call_next` (the result may be a model or a dict).
37. **A new tool could be exposed to every role by accident.** Add a test that the union of `ROLE_TOOLS` equals the registered tool names (and the same for prompts), so every tool is placed in the policy on purpose.
38. **Audit telemetry counted agent calls by `role='mcp'`.** Putting the user's role there would have broken the counter. Keep `role='mcp'`, put the person in `actor`, and the role in the detail.

## HIS paste ingress (0.3)

39. **Building the wrong ingress UI.** A calculator form with its own save path was half-built before the user redirected to "paste → CSV → existing import". Ask first which existing write path an ingress should feed; reusing the importer gave validation, audit and bulk import for free.
40. **Python `\b` treats CJK characters as word characters.** `腎功能eGFR 55` never matched `\beGFR\b`. Compile with `re.IGNORECASE | re.ASCII`.
41. **One value per line lost data.** `BP 138/82  BW 76 kg  BH 170 cm` kept only BP. Claim label spans in priority order (UACR before creatinine, HDL/LDL before cholesterol), drop overlapping lower-priority matches, and read each label's number from the segment before the next label. Exclude urine creatinine explicitly.
42. **NFKC folds the micro sign `µ` into Greek `μ`**, which broke `µmol` unit matching after normalising full-width text. Map it back after `normalize("NFKC", ...)`.
43. **The importer crashed without `patients.csv`** (`KeyError: 'patients'` from a hard-coded `["patients"] + ...` order). Follow-up labs for existing patients are the normal case; build the order from the files present.
44. **Partial reports hid older values.** The newest lab row was used as a whole, so pasting only HbA1c made eGFR "missing"; and the *oldest* condition row won, so a later "not smoking" was ignored. Use the latest non-null value per lab field (keep its date) and the newest condition row.
45. **An imported `patients` row overwrites name, birth date and sex.** Generate it from a paste only for a chart number that does not exist yet, and enforce the same on the server for physicians (who get a paste-only import), not just in the UI.
46. **Windows shell tooling mangled generated code.** A Python edit script sent through a Git Bash heredoc turned `"\n"` inside generated source into a real line break (twice), and a heredoc containing `<repo>` with backslashes was blocked by the agent's command safety check as unparseable. Write such scripts to a file with the editor tool and run the file; re-read the exact bytes when a "fixed" file still fails (a synced drive may also lag).

## Sharing and deployment

47. **"How do I share the dashboard? There is no Share button."** The app is a local server, not a hosted page. Explain that, then offer a LAN demo (synthetic data) and an IT deployment. Only published documents have a Share menu, and they stay private until the owner shares them.
48. **A LAN demo needs three settings, not one.** `--host 0.0.0.0` alone serves the dashboard but MCP answers 421 until the LAN IP is in `MCP_ALLOWED_HOSTS` (and origins), and `dashboard_url` links still point at 127.0.0.1 until `PUBLIC_BASE_URL` changes. DHCP may change the IP.
49. **A local request does not prove the firewall is open.** Requests from the same PC skip Windows Firewall. Check inbound rules read-only (never change security settings), report the network profile (Public/Private), and say it was not tested from a second PC.
50. **The shipped compose file hard-coded demo mode** and passed none of the newer settings, so a "production" container would run with demo defaults (shared token on). Give IT a `docker-compose.override.yml` (`env_file: .env`, `DM_DEMO_MODE=false`, ports bound to 127.0.0.1; `ports: !override` needs Compose ≥ 2.24), and fix the compose file in the repo.
51. **First start seeds an empty database with synthetic patients and demo accounts, even outside demo mode**, and there was no user-management tool. Both surface only when writing the deployment guide. Gate seeding on demo mode, add a user CLI, and until then document disabling demo accounts and creating users with a password prompt.
52. **Desktop-AI rollout has a data prerequisite that belongs at the top of its section.** Tool results (patient data) go to the model vendor's cloud. State it first, and make "dashboard only" the default until security and privacy approval.
53. **A document export came back as base64 in the tool result.** Retyping base64 into a file risks a corrupt file. Regenerate the Markdown from the content you wrote, and strip personal details (the user's name in the byline, the developer PC's IP or Wi-Fi name) from the repo copy.
54. **"I can open the link, my teammate cannot."** The link was a private LAN IP (192.168.x); it works only on the same network. Ask where the teammate is before debugging the server. Off-LAN: Tailscale machine share (or a hospital VPN), never a public tunnel while demo passwords are public.
55. **Tailscale worked locally but the remote laptop timed out.** Windows files the Tailscale adapter under the Private profile; the python.exe allow rules covered Public only. Local requests skip the firewall, so every check on the host passed. Read the profile and rules read-only, then give the user a port-8000 rule limited to `100.64.0.0/10` on Private to run themselves.

