# Project wrap-up: Voice2Txt, JEV waves A–D and the browser version (pitfalls and reusable practice)

**Project:** Voice2Txt, a Typeless-like voice input tool with no subscription. Modes: Traditional Chinese, English, Chinese speech → English, and 隨便問 (ask-anything).
- Windows desktop app: Python 3.9, Tkinter, faster-whisper, PyInstaller portable build, optional LLM clean-up (local Ollama first, then opt-in Anthropic / OpenAI / Gemini).
- iPhone / iPad app: SwiftUI + WhisperKit. Still never compiled (no Mac).
- Browser version (PWA): Whisper in a Web Worker via Transformers.js + ONNX Runtime WASM, built by another agent on 2026-11-15.

**Dates:** 2026-11-13 to 2026-11-16, several Claude Code sessions (planner on Fable 5.1 / Opus 5.5, executors on Sonnet 5.5, auditors on Opus 5.5) plus one Codex session on the PWA.

**Outcome:**
- Source, tests, JEV task specs (`queue/`), audit verdicts and evidence: [claude-skills/voice2txt](https://github.com/ckt520728/claude-skills/tree/master/voice2txt). The 8.3 GB portable build, models and the Typeless analysis stay local.
- Desktop: hotkeys (Right Alt hold-to-talk, Right Alt + Right Shift translate, Right Alt + Right Ctrl ask), tray, floating indicator, start at login, single instance, paste-back with clipboard restore, auto dictionary, sounds, mute other apps, insights dashboard, retention, light/dark theme. 142 unit tests pass; final packaged evidence `verification/packaged-waveD3-2026-11-14.json`.
- Browser version: v5 works end-to-end in desktop Chrome (upload and recording). **Not yet confirmed on iPad**, and the deployed site still runs v4.
- Still unverified: real-microphone use, live Anthropic calls, iOS compile, any iPad transcription.

**Confidentiality.** No API key or token appears in the repo or this note; the published tree was pattern-scanned before the push. Site deployment identifiers were removed from the public copy. Typeless was examined statically only; no Typeless code, screenshots or analysis dumps were published.

---

## 0. One-line summary

| # | Lesson | Applies to |
|---|---|---|
| 1 | **"It doesn't work" can mean the server isn't running.** `http://127.0.0.1:8787/recording.html` failed because nothing listened on 8787; a test agent had started `python -m http.server` by hand. Check the port before debugging the app. | Any locally served web app |
| 2 | **An independent adversarial auditor finds real bugs every round.** 12 audits; 7 failed on genuine defects that all unit tests had passed. | Agent workflows with a QA stage |
| 3 | **Every fix creates the next bug at the integration boundary.** Four fix rounds on hotkeys: each fix was correct in isolation and broke something one layer down. | Low-level OS integration |
| 4 | **Never `await` a browser audio API without a timeout.** `AudioContext.resume()` never resolves without a user gesture; the page froze on 「正在啟用麥克風」 with every button disabled. | Web audio / microphone code |
| 5 | **The finish line decides the clock.** The REATypeless demo took 25 minutes: one platform, no tests, a human tapping keys. Ours took days: evidence-based acceptance, Windows, auditor, docs. Both are honest; they are different products. | Scoping AI-built apps |

---

## 1. Workflow that was used (JEV two-phase)

```
Planner (high model)  writes queue/PLAN-*.md + queue/T*.json specs, no code
Executors (Sonnet)    one task each, run their own acceptance commands
Auditor (Opus, high)  re-runs every check, attacks the result, never fixes
FAIL  -> new fix task -> re-audit        PASS -> next task
```

25 tasks (T01–T24 plus rebuild/doc variants), 12 audits (A1, A2, C, C2, C3, C4, D, E, E2, E3, F, G). Specs, verdicts and evidence are all in the repo, so each claim in `STATUS.md` traces to a file.

**What worked:** the auditor caught defects that would have reached the user: Ctrl+Alt+V instead of Ctrl+V when the hotkey was still held, two app instances each with a keyboard hook, a held key dropped after 1.2 s, an idle-timer reset that would have blocked screen lock, Alt+Space opening the system menu, multi-segment paste corruption, and a clipboard left overwritten when a target app answered Ctrl+C late.

**What cost too much:** five usage-limit interruptions (agents resumed from saved transcripts, so no work was lost, but hours were); cross-process key-injection checks that take minutes to write and stay flaky (`check_wave_d.py` failed about 2 in 17 runs, cause not found); and full Opus audits for issues that were only minor.

---

## 2. Pitfalls (with evidence)

### Windows hotkeys and clipboard

1. **A key your hook swallows never updates `GetAsyncKeyState`.** Recovery logic that trusts the physical state then "releases" a key the user is still holding. Fix: only trust physical state for keys observed physically down; for swallowed keys use an auto-repeat timeout, and only after a repeat was seen (keys that never repeat, like mouse-macro F-keys, would otherwise drop after 1.2 s).
2. **A key you release with injected key-ups looks physically up.** Before the selection copy we release held modifiers so Ctrl+C is not Ctrl+Alt+C; that made the hold-to-talk stop after 1.2 s. Fix: mark those keys as synthetically released and ignore sampling until a real key event.
3. **Alt+Space opens every app's system menu.** A hook that never swallows keys cannot use Alt+Space as a hotkey. Fix: default 隨便問 to Right Alt + Right Ctrl, migrate the old default once (versioned setting), and swallow only the non-modifier key that completes a configured Alt combo. Never swallow modifiers (AltGr layouts).
4. **Another app's hook can eat your hotkey.** Typeless was running on the test PC and swallowed Right Alt, which is also our default. The app now warns; real-key tests used Left Alt / F23 / F24.
5. **A liveness probe that injects a key resets the Windows idle timer** and would block screen lock and sleep. Only probe while the user is active and the hook has gone quiet.
6. **Clipboard restore needs an ownership check.** If the target app writes the clipboard after your timeout, the watcher must restore only when the clipboard owner is still the target process, otherwise it overwrites what the user just copied.
7. **`OpenClipboard(NULL)` + `EmptyClipboard` made `SetClipboardData` fail intermittently (error 1418).** Opening with the desktop window as owner fixed 15/15 runs.

### Browser version (PWA)

8. **The local URL needs a running server.** Added `scripts/serve_pwa.py` and a double-click `開啟本機網頁版.cmd`. `127.0.0.1` is only this PC; an iPad cannot open it.
9. **`await audioContext.resume()` without a timeout freezes the page.** Measured: a suspended context's `resume()` was still pending after 3 s without user activation. v5 records without creating an AudioContext and decodes with `OfflineAudioContext`, with timeouts on both steps. This is a plausible but **unconfirmed** cause of the iPad failure.
10. **Decode straight to 16 kHz.** Decoding at 44.1 kHz and box-filtering down changed a word (「戴」 instead of 「帶」); decoding into a 16 kHz `OfflineAudioContext` gave the correct sentence.
11. **Stale caches fake an update.** After rebuilding, Chrome kept serving the old HTML (`python -m http.server` sends no `Cache-Control`). The local server now sends `no-cache` for HTML, `sw.js` and manifests.
12. **A page's "unsaved changes" guard can block test automation.** A `beforeunload` handler kept the old page alive, so two test runs silently tested the previous version. Check the version badge before trusting a result.
13. **Native `confirm()` dialogs freeze browser automation.** Stub `window.confirm` in test pages or avoid leaving pending state between runs.
14. **Whisper tiny is not usable for translation** ("The next four days will be the final report of the day." for a meeting reminder). Use small, or the desktop LLM path.

### Process

15. **Desktop verification is not iPad acceptance.** Synthetic audio, simulated microphones and desktop Chrome cannot rule out Safari, memory or real microphone problems.
16. **Fixing a button is not fixing transcription.** v4 unlocked the record button; the user still could not get transcripts on iPad.
17. **Hand-typed numbers in evidence files go wrong.** One packaged report had a 63-character SHA-256 and a dist size that did not reproduce. Compute every number by script and have the planner re-verify.
18. **Git refuses a folder owned by another Windows account** ("dubious ownership"). The PWA sub-repository was created by the Codex sandbox account, so v5 is not committed there yet.

---

## 3. Reusable practice

- Before debugging "it doesn't work": check the port, the version the browser actually loaded, and whether a dialog or guard is blocking.
- Wrap every browser media promise (`getUserMedia`, `resume`, `decodeAudioData`) in a timeout and keep the UI recoverable.
- For OS-level input code, test with real injected keys in a second process; pure state-machine tests missed every integration bug here.
- Use the full auditor for acceptance; for minor findings, have the planner verify mechanically (hashes, test run) instead of another audit round.
- Freeze features before the human test. The next step for this project is a ten-minute real-microphone test with Typeless closed, then fix only what fails.

---

## 4. Next steps

1. Real-microphone test on Windows (desktop app and `開啟本機網頁版.cmd`), Typeless closed.
2. Redeploy the browser version v5 and test on the iPad with the in-page 「載入診斷」.
3. On iPad today, the phone bridge version (`啟動手機網頁版.cmd`) is the path the user confirmed works.
4. Longer term: an iOS keyboard extension talking to a LAN gateway, the only way an iPhone app can type into other apps.
