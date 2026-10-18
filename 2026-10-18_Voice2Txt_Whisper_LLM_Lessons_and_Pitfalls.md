# Project wrap-up: pitfalls and reusable practice

**Project:** Voice2Txt, a Typeless-like voice input app with no subscription.
- Windows desktop app (Python 3.9, Tkinter, faster-whisper / CTranslate2, PyInstaller portable build).
- iPhone app (SwiftUI + WhisperKit 0.9.4, on-device CoreML). Not yet compiled; needs a Mac.
- Three modes: Traditional Chinese, English, and Chinese speech → English.

**Date:** 2026-10-18 (one Claude Code session, which continued an earlier agent's build).

**Outcome:**
- Source, iOS project, tests, user manual and verification evidence are in [claude-skills/voice2txt](https://github.com/ckt520728/claude-skills/tree/master/voice2txt).
- The portable Windows build (7.8 GB with GPU libraries and three Whisper models) stays local: it is too large for git and contains third-party binaries.

**Environment:** Windows 11, RTX 3060 12 GB, Git Bash / PowerShell 5.1, Python 3.9, Ollama with `gemma4:latest` (8B Q4), OpenAI `gpt-6-luna`, Gemini `gemini-3.8-flash`, REA CLI, Claude Code.

> **Confidentiality.**
> - The user's API keys were read from a local key file only through a wrapper that put them into a child process's environment and redacted them from all output.
> - No key appears in this note, the repo or any report; every published file was pattern-scanned before the push.
> - Typeless was examined statically only: the installer was never run and none of its code, icons or screenshots were published.

---

## 0. One-line summary

| # | Lesson | Applies to |
|---|---|---|
| 1 | **Speech-to-text and text cleanup are two different jobs.** Whisper "hears"; an LLM "organizes and denoises". On five messy clips, Whisper alone passed 0/5 and Whisper + LLM passed 5/5. | Any dictation or transcription product |
| 2 | **"Remove self-corrections" will silently delete negations.** Both cloud LLMs read 「禮拜一，不是禮拜二」 as a slip and deleted it, and Gemini reversed it to Tuesday. The prompt must separate signalled corrections from contrasts, and there must be a test case for it. | Any LLM cleanup or summarizing prompt |
| 3 | **Never generalize quality from one clip.** One test clip per model made medium and large-v3 look "correct"; the 4-case corpus showed both still drop meaning. | Model comparisons |
| 4 | **A backup chain needs pause-on-failure, not just order.** Without a 60 s pause, a dead Ollama or a 30 s Gemini timeout would be paid on every segment. | Multi-provider LLM fallbacks |

---

## 1. Design that worked

```
Stage 1  Whisper (local)  speech → raw transcript   「嗯，那個，明天下午三點，不對，是四點開會」
Stage 2  LLM              organize + denoise        「明天下午四點開會。」
                          (+ translate in zh→en)    "We have a meeting tomorrow at 4 p.m."
Chain    Ollama gemma4 → OpenAI gpt-6-luna (high) → Gemini gemini-3.8-flash (low) → Whisper only
```

- The raw Whisper transcript is always kept on screen and in history, so a user can check what the LLM changed.
- The final step never needs the network. If every LLM fails, zh/en use the raw transcript and zh→en uses Whisper's own translation.
- Ollama is the default when the app detects it. Cloud models are opt-in, pay-per-use and use the user's own key. They receive transcript text, never audio.
- API keys are stored with Windows DPAPI (`CryptProtectData`), not as plain text in `settings.json`.

| Approach (5 disfluent clips) | Correct | LLM time per clip |
|---|---|---|
| Whisper only | 0/5 | — |
| + Ollama gemma4 | 5/5 | ~0.6 s |
| + OpenAI gpt-6-luna (high) | 5/5 | 2–3.3 s |
| + Gemini gemini-3.8-flash (low) | 2/2 answered (3 got HTTP 429) | ~2.6 s |

---

## 2. Pitfalls

### Quality and evaluation

**P1. One test clip was taken as proof of quality.**
- *What happened:* after the rebuild, the medium and large-v3 models each translated one clip correctly, and I reported zh→en as "correct". The earlier 4-case benchmark files showed medium drops 「明天」 and large-v3 drops 「開會」. I retracted the claim.
- *Check:* any quality claim must cite the corpus result file, not a smoke run.

**P2. Whisper's built-in translation is unreliable at every size.**
- *What happened:* on the clean corpus, small passed 1/3 and medium and large-v3 each 2/3. On one disfluent clip Whisper's `task='translate'` returned **Simplified Chinese instead of English**.
- *Fix:* the LLM stage. Whisper translation is now only the last offline backup.

**P3. The cleanup prompt deleted a negation.**
- *What happened:* the first rule said "on self-correction, keep only the final version". Both cloud models applied it to 「預約下禮拜一的門診，不是禮拜二」 and dropped the second half; Gemini returned 「下禮拜二」, the opposite meaning. The local gemma4 got it right.
- *Fix:*
  - Treat something as a correction only when it is explicitly signalled (不對、我是說、更正; sorry, I mean).
  - State that "A, not B" is information to keep, with examples in both languages.
  - Add a disfluent corpus case that fails if 「不是」 or "Tuesday" goes missing.
- *Check:* `scripts/benchmark_refine.py`, which uses `zh_present`/`zh_absent` and `en_present`/`en_absent` keyword groups.

**P4. Whisper wrote a filler sound as a stray letter.**
- *What happened:* 嗯 came out as "N,". OpenAI kept it until the prompt explicitly said to drop stray letters from filler sounds.

**P5. Clean TTS clips cannot test cleanup.**
- *What happened:* the existing fixtures had no fillers, so they could not show what stage 2 adds.
- *Fix:* a separate `disfluent-corpus.json`, voiced with Windows TTS through `create_quality_audio.ps1 -Corpus disfluent`.

### Cloud LLMs

**P6. Third-party pages gave conflicting model IDs.**
- *What happened:* web results listed `gpt-5.6-luna`, `gpt-6-luna` and different effort scales.
- *Fix:* use only the official docs (developers.openai.com models and reasoning guide; ai.google.dev latest-model and thinking pages). Neither model has a free tier, so the backup is pay-per-use, not free.

**P7. Gemini `high` is too slow for live dictation, and its speed varies.**
- *What happened:* `high` took 28 s and then hit the 30 s timeout. Later the same day even a 26-token request took 56–89 s, then dropped back to 2.6 s, then the account returned **HTTP 429 "exceeded your current quota"**.
- *Fix:*
  - Gemini is the last cloud step and runs at `low`.
  - Every failure pauses that provider for 60 s.
  - The status bar names the engine used for each segment.

**P8. An invalid key proves only that the endpoint is reachable.**
- *What happened:* bad-key tests confirmed the URL, auth header and error path (HTTP 400 / 401 → Whisper). The real response parsing and latency were unknown until the user supplied working keys.
- *Check:* report the two separately ("reachable" vs "translates").

### Keys and publishing

**P9. A plain-text key file also held unrelated keys.**
- *What happened:* the user's file mixed Voice2Txt keys with biomedicine API keys, and it was not in `KEY=value` format.
- *Fix:*
  - Inspect it only through a masked view (`AIza…[39 chars]`).
  - Pick the two needed lines by their label.
  - Pass them to child processes through environment variables.
  - Redact the key values from captured output.
  - Assert that no key appears in any report.

**P10. A handoff note recorded where the keys were kept.**
- *What happened:* the note was fine locally but not for a public repo. Before the push it was rewritten to say "a key file outside the repo".
- *Check:* grep every file being published for key patterns (`sk-`, `AIza`, `AQ.`, `gho_`), file paths and email addresses.

**P11. A public repo is not the place for reverse-engineering output.**
- *Fix:* published only aggregate REA statistics, SHA-256 hashes and a method note. Left out:
  - the 1 GB REA JSON dump;
  - the design `.docx` and its OCR, which contain Typeless screenshots;
  - personal research notes;
  - the copied WhisperKit source;
  - models, `dist` and GPU DLLs.

### Windows build and tooling

**P12. PowerShell `*>` redirection aborted the PyInstaller build.**
- *What happened:* the build script sets `$ErrorActionPreference = 'Stop'`. Redirecting with `*>` inside PowerShell turned PyInstaller's harmless stderr warning into a terminating error, so the build looked failed.
- *Fix:* `powershell -NoProfile -File scripts\build_windows.ps1 -IncludeGpu > build.log 2>&1`.

**P13. An old Visual C++ runtime crashed CTranslate2 (found by the earlier agent).**
- *What happened:* an Anaconda-supplied `MSVCP140.dll 14.27` caused `0xc0000005` when the model loaded.
- *Fix:* the build script copies the newer System32 runtime into `dist` only, without touching system DLLs.

**P14. Bash heredocs containing CJK text and mixed quotes failed.**
- *What happened:* `unexpected EOF while looking for matching '` appeared twice on long patch scripts.
- *Fix:* write the script to a file with the Write tool, then run it.

**P15. `python -I` ignores `PYTHONIOENCODING`.**
- *What happened:* printing Chinese raised `UnicodeEncodeError: 'cp950'`. Garbled console Chinese also looked like a model failure until the JSON was read back as UTF-8.
- *Fix:* `sys.stdout.reconfigure(encoding='utf-8')` inside the script, and judge results from the UTF-8 JSON files, never from the console.

**P16. `sed` with Windows backslash paths did nothing, silently.**
- *What happened:* the fixture generator kept writing `quality-*.wav`, and the new clips had to be renamed.
- *Check:* grep the edited line after every `sed`.

**P17. A smoke script could not import the package.**
- *What happened:* `scripts/smoke_desktop.py` failed with `ModuleNotFoundError: voice2txt`.
- *Fix:* run it with `PYTHONPATH=.`.

**P18. A saved setting would have blocked the new default.**
- *What happened:* making Ollama the default would never reach users who had already saved "Whisper".
- *Fix:* store the choice under a versioned key (`translation_backend_v2`) and map old values (`LEGACY_BACKENDS`).

**P19. Tk "invalid command name …_poll" on exit.**
- *What happened:* it appears when a test destroys the window while an `after` timer is queued. It is harmless; don't chase it.

### Working with an earlier agent's output

**P20. The documents lagged behind the code.**
- *What happened:* `README.md` and `STATUS.md` did not mention the GPU models or the Ollama path, both already in the code and benchmarked.
- *Fix:* read the code and the `verification/` JSON before trusting prose. `STATUS.md` is kept as an evidence ledger in which every row cites a file.

---

## 3. Verification at hand-off

- 24 unit tests and the real-Tk desktop smoke test pass.
- The packaged app passed 12 end-to-end runs (3 modes × 4 failure scenarios) with the chain order confirmed. In the "Ollama down, no OpenAI key" scenario, Gemini returned HTTP 429, so those runs fell through to Whisper as designed.
- Evidence files: `verification/refine-small-2026-10-18.json`, `packaged-chain-2026-10-18.json` and `cloud-fallback-2026-10-18.json`.

## 4. Still open

1. Real-microphone test by the user (in progress): all modes, hotkey, paste-back, 30-minute run, and whether stage-2 latency is acceptable.
2. The user's Gemini account quota (HTTP 429). After it is fixed, rerun `benchmark_refine.py` to get a full Gemini 5/5.
3. iPhone: compile, sign and test on a device on a Mac. It currently has stage 1 only.
4. Possible addition: let stage 2 drop Whisper's silence hallucinations (e.g. 「字幕由…提供」). This needs a path where an empty output counts as valid.
