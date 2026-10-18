# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Voice2Txt: a Typeless-like, subscription-free voice input tool with three modes — Traditional Chinese transcription (`zh`), English transcription (`en`), and Chinese speech → English (`translate`). Two deliverables:

- **Windows desktop** (Python 3.9, Tkinter, faster-whisper/CTranslate2) — `voice2txt/`, packaged with PyInstaller into `dist/Voice2Txt/`.
- **iPhone** (SwiftUI + WhisperKit 0.9.4, on-device CoreML) — `ios/`. Never compiled yet: no Mac/Xcode in this environment.

User-facing docs (`README.md`, `STATUS.md`, `ios/README.md`) are in Traditional Chinese; keep them in Chinese. `STATUS.md` is the acceptance ledger; `handoffs.md` is the session-to-session handoff log. Original goal prompt: `2026 voice2txt_r1.md`.

## Commands

Use `.build-venv` (full deps + PyInstaller). `.venv` is a minimal leftover env.

```powershell
.\.build-venv\Scripts\python.exe -m unittest discover -s tests -v              # all tests (~0.2s, no model needed)
.\.build-venv\Scripts\python.exe -m unittest tests.test_core.CoreTests.test_chunker_preserves_every_sample_and_flushes_tail   # single test
.\.build-venv\Scripts\python.exe run_desktop.py                                # run desktop app from source
.\.build-venv\Scripts\python.exe run_desktop.py --self-test out.json --audio tests\fixtures\chinese.wav --mode translate --model small [--device cuda] [--llm-model gemma4:latest] [--cloud OpenAI:high --cloud Gemini:low] [--vocabulary "..."]   # keys from OPENAI_API_KEY/GEMINI_API_KEY; missing key = skipped
PYTHONPATH=. .\.build-venv\Scripts\python.exe scripts\benchmark_refine.py small   # Whisper-only vs each LLM on tests/fixtures/disfluent-*.wav -> verification/refine-*.json
powershell -NoProfile -File scripts\build_windows.ps1 [-IncludeGpu] > build.log 2>&1   # PyInstaller onedir build -> dist\Voice2Txt (don't use PowerShell *> redirection: stderr + ErrorActionPreference=Stop aborts it)
.\.build-venv\Scripts\python.exe scripts\download_models.py small medium       # Systran/faster-whisper-* -> models\whisper-<size>
```

`--self-test` is how packaged builds are verified: it writes a JSON report with `stage` checkpoints, `desktop_ui`, `ok`. A failed run leaves `stage` at the last reached step — use it to locate crashes (e.g. native DLL faults). Run it against `dist\Voice2Txt\Voice2Txt.exe` too, not just source.

`scripts/benchmark_*.py` / `smoke_*.py` run real inference on `tests/fixtures/*.wav` and write results into `verification/*.json`. `tests/fixtures/quality-corpus.json` holds the zh→en quality cases with keyword checks (times, negations, quantities).

There is no linter or formatter configured.

## Architecture (desktop)

- `voice2txt/core.py` — engine-agnostic pieces:
  - `Chunker`: turns the mic stream into segments; cuts at ~0.5 s pauses (RMS < 0.006) with a hard max length, and `flush()` must return the tail so no sample is lost (tests assert exact sample conservation).
  - `WhisperEngine`: wraps `faster_whisper.WhisperModel`. `translate` mode uses Whisper's built-in `task='translate'`; `zh` output goes through OpenCC `s2twp`. The user dictionary is passed as `initial_prompt` (≤1000 chars). Accepts an injected `model` for tests.
  - `bundled_model()` / `preferred_settings()` resolve models relative to `sys._MEIPASS` (PyInstaller) or repo root; `models/whisper-<size>` is used if `model.bin` exists, otherwise faster-whisper downloads it. CUDA auto-selects medium/large-v3 only when `gpu/nvidia` exists and a GPU is detected.
  - `configure_cuda()` adds `gpu/nvidia/*/bin` (pip-installed cuBLAS/cuDNN from `requirements-gpu.txt`) to the DLL search path for this process only.
  - `Store`: SQLite history at `%LOCALAPPDATA%\Voice2Txt\history.sqlite3`, with an in-place `source` column migration.
- **Core design (user-specified, 2026-10-18): two stages.** Stage 1 is Whisper speech→text. Stage 2 is an LLM that organizes and denoises the transcript in *every* mode: it removes fillers and repeats, applies explicit self-corrections, fixes misheard words, and adds punctuation. In `translate` mode it also translates. The raw Whisper transcript is always kept as `source`. Prompt rules live in `RULES`/`TASKS` in `translation.py`. Keep the rule that a contrast or negation ("Monday, not Tuesday") is information, not a self-correction: both cloud models dropped it before that rule was added.
- `voice2txt/translation.py` — stage 2, with fallbacks. Every backend exposes `refine(text, mode, vocabulary)`. Fixed order: Ollama → OpenAI (`high`) → Gemini (`low`) → Whisper only. Order and defaults are in `CLOUD`. `LocalTranslator` talks to **local Ollama only** (`127.0.0.1:11434`, proxies disabled, 20 s translate timeout) and rejects cloud/remote models. `CloudTranslator` is the opt-in backup: Gemini `generateContent` (`thinkingConfig.thinkingLevel`) or OpenAI Responses (`reasoning.effort`); defaults are in `CLOUD`. `TranslatorChain` tries each translator in order and pauses a failed one for 60 s. `build_translator(ollama_model, clouds)` sorts the clouds into the `CLOUD` order, and a failed Ollama `prepare()` pauses Ollama instead of failing the model load. `decode_segment()` is the single place mode routing happens. With a chain, Whisper transcribes (`zh` for zh/translate, `en` for en) and the chain refines. `zh` output is re-run through OpenCC. If every LLM fails: zh/en return the raw transcript, and translate falls back to Whisper `task='translate'`. `DecodeResult.error` is set only if that fails too.
- `voice2txt/keystore.py` — Windows DPAPI (`CryptProtectData`) wrapper so cloud API keys are not stored as plain text in `settings.json`; env vars `GEMINI_API_KEY`/`OPENAI_API_KEY` are used when the field is empty.
- `voice2txt/desktop.py` — Tk `App`. Threads: sounddevice callback → `audio` queue (bounded; overflow stops recording explicitly rather than dropping audio) → collector feeds `Chunker` → `jobs` queue → single `_decode` worker → `events` queue → `_poll` on the Tk thread (only place UI is touched). Global hotkey `Alt+Shift+Space` uses a Win32 `RegisterHotKey` message loop thread; optional paste-back only fires if the original window still has focus. Settings in `%LOCALAPPDATA%\Voice2Txt\settings.json`. The engine choice is saved as `translation_backend_v2`. Its values are `LLM_REFINE`/`WHISPER_ONLY`; the earlier saved values `本機 Ollama`/`Whisper` are mapped through `LEGACY_BACKENDS`. While no choice is saved, startup probes Ollama `/api/tags` and defaults to `LLM_REFINE` (the older `translation_backend` key is intentionally ignored). Cloud settings are stored per provider under `cloud`, with DPAPI-encrypted keys; the old single `cloud_provider` keys are migrated on load. `LLM_REFINE` forces CPU Whisper.
- `run_desktop.py` — entry point for both the app and `--self-test`.

## Architecture (iOS)

`ios/Voice2Txt/`: `AudioChunker.swift` (≈5 s segments, tail flush), `Transcriber.swift` (WhisperKit; model downloaded on first use, then on-device), `ContentView.swift`, `Voice2TxtApp.swift`. `ios/Voice2Txt.xcodeproj` is hand-generated by `scripts/generate_xcode_project.py`; `ios/project.yml` is an XcodeGen alternative. Build commands for a Mac are in `ios/README.md`. Do not claim the iOS app builds or works until `xcodebuild` and on-device evidence exist.

## Build gotchas

- `scripts/build_windows.ps1` overwrites `msvcp140*.dll`/`vcruntime140*.dll` inside `dist\Voice2Txt\_internal` with the System32 copies. An Anaconda-sourced 14.27 runtime caused `0xc0000005` when CTranslate2 loaded the model. Keep this step.
- The build bundles `models\whisper-small` (needs `config.json`, `model.bin`, `tokenizer.json`, `vocabulary.txt`); `-IncludeGpu` also bundles `gpu\nvidia` and medium/large-v3 if present. `dist\Voice2Txt` must be moved as a whole folder.
- `models/`, `gpu/`, `tools/`, `build/`, `dist/`, `*.spec`, `*.wav` are gitignored (the test fixture `.wav` files are not tracked by git either). `Voice2Txt.spec` is generated; the build script passes flags directly.

## Project rules (from STATUS.md / README.md)

- No subscription. The default path is fully local (Whisper + Ollama). Cloud LLMs are only an opt-in backup that the user explicitly requested (2026-10-18), with a user-supplied, pay-per-use key. They send transcript text, never audio. Don't make cloud the default or send audio.
- User-facing manual: `USER_MANUAL.md` (shipped as `使用者手冊.md` in `dist`). Update it when UI or behavior changes.
- Typeless (`D:\Downloads\Typeless-2.8.2-x64-Setup.exe`) is reference only. It was unpacked statically with 7-Zip and its `app.asar` analyzed with the REA CLI (`tools/rea`, results in `verification/typeless-*.json`, `verification/typeless-reference.md`). Never run the installer or copy its code, icons, or servers.
- Acceptance is evidence-based: a successful build is not proof that it works. Record real inference/UI results in `verification/` and update `STATUS.md`. Still open: real-microphone and 30-min tests, cross-app paste, translation quality on small/CPU, and everything on iOS.
