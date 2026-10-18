# Handoffs

Session-to-session handoff log. Newest entry first. Each entry: date, what was done, current state, next steps, open risks.

---

## 2026-10-18 (later) — Two-stage redesign: Whisper → LLM refine, chain Ollama → OpenAI → Gemini → Whisper

**User direction (verbatim intent):** "Whisper do the voice to text work first, plus the effort by LLM to organize and denoise the transcripts." Chain: Ollama → OpenAI high → Gemini low → Whisper.

**Done**
- `translation.py`: every backend now has `refine(text, mode, vocabulary)`, and the LLM runs in all three modes, not only translate. Prompt rules are in `RULES`/`TASKS`. `CLOUD` holds the fixed order and defaults (OpenAI `gpt-6-luna` high, Gemini `gemini-3.8-flash` low). `build_translator(ollama, clouds)`. In zh/en mode, a failed LLM returns the raw Whisper text; translate falls back to Whisper translate.
- Desktop settings: `Whisper + LLM 整理` / `僅 Whisper`, with rows ① Ollama, ② OpenAI, ③ Gemini (each has a checkbox, model, effort and DPAPI-encrypted key; old settings migrate). The source panel is now labelled "Whisper 原始轉錄".
- `run_desktop.py --self-test`: `--cloud PROVIDER:EFFORT` (repeatable) and `--vocabulary`.
- New fixtures `tests/fixtures/disfluent-*` (made with `scripts/create_quality_audio.ps1 -Corpus disfluent`) and `scripts/benchmark_refine.py`.
- 24 unit tests and `scripts/smoke_desktop.py` (run with `PYTHONPATH=.`) pass. Rebuilt `dist` (`-IncludeGpu`).
- Evidence: `verification/refine-small-2026-10-18.json`, `verification/packaged-chain-2026-10-18.json`.
- USER_MANUAL (design section, chain, settings), README, CLAUDE.md and STATUS updated.

**Findings**
- Whisper alone 0/5 on the messy clips; Ollama 5/5 (about 0.6 s); OpenAI high 5/5 (2–3.3 s). Whisper "translate" once returned Simplified Chinese instead of English.
- The first prompt let OpenAI and Gemini drop 「不是禮拜二」, treating it as a self-correction. Fixed with explicit rules: only treat signalled corrections as corrections, and keep contrasts and negations.
- Gemini latency swung from 2.6 s to over 60 s on the same day, then the account returned HTTP 429 "exceeded your current quota". The user needs to check Gemini billing or plan in AI Studio.

**Next**
- The user should check the Gemini quota, then rerun `scripts/benchmark_refine.py` with keys to get a full Gemini 5/5 result.
- Real-microphone testing of the refine latency: Ollama adds about 0.6 s per segment on CPU Whisper small.
- Possible addition: let the LLM drop Whisper hallucinations on silence (e.g. 「字幕由…提供」). Not done; it needs an "empty output is valid" path.
- iOS still has stage 1 only.

---

## 2026-10-18 — Session: /init + goal restatement

**Done**
- Ran `/init`: created `CLAUDE.md` (commands, desktop/iOS architecture, build gotchas, project rules).
- Created this `handoffs.md`.
- Confirmed the existing state: `.\.build-venv\Scripts\python.exe -m unittest discover -s tests` → 12 tests OK.

**State inherited from earlier sessions** (details in `STATUS.md`, `verification/`)
- Windows desktop app exists (`voice2txt/`, `dist/Voice2Txt/Voice2Txt.exe`) with three modes (zh / en / zh→en), pause-based chunking, dictionary prompt, history, export, `Alt+Shift+Space` hotkey, optional paste-back.
- Optional CUDA (medium / large-v3) and local Ollama LLM translation (`gemma4:latest` default) are in the code and have benchmark JSON in `verification/`. `README.md` and `STATUS.md` were written before these and do not fully describe them yet.
- iOS SwiftUI + WhisperKit project in `ios/`. **Never compiled.** No Mac available.
- Typeless analyzed statically (7-Zip + REA on `app.asar`). Ghidra was not used: there was no native target that needed it.

**Done later this session**
- Rebuilt `dist` with `scripts/build_windows.ps1 -IncludeGpu` (7.8 GB). Note: running it via PowerShell `*>` redirection fails spuriously (stderr + `ErrorActionPreference=Stop`); run `powershell -File scripts/build_windows.ps1 -IncludeGpu > log 2>&1` instead.
- Packaged `--self-test`: 6/6 ok → `verification/packaged-2026-10-18.json`; STATUS.md row added.
- User request: make Ollama the default when it is installed, add a cloud backup (Gemini Flash 3.8 / GPT Luna), and write a user manual. Done:
  - `translation.py`: `ollama_models()`, `CloudTranslator` (Gemini `gemini-3.8-flash` via generateContent + `thinkingLevel`; OpenAI `gpt-6-luna` via Responses + `reasoning.effort`; default effort `high`), `TranslatorChain` (60 s pause on failure), `build_translator()`. Last resort is Whisper `translate`.
  - `keystore.py`: DPAPI-encrypted API key. Desktop has a new 雲端備援 LLM settings section. The engine choice is now saved as `translation_backend_v2`, so the Ollama default applies once to users who had saved the old key.
  - `run_desktop.py --self-test` accepts `--fallback-provider/--fallback-model/--fallback-effort`.
  - `USER_MANUAL.md` (Traditional Chinese), shipped as `dist/Voice2Txt/使用者手冊.md`.
  - Rebuilt `dist`; 7/7 packaged self-tests ok → `verification/packaged-fallback-2026-10-18.json`.
  - Model IDs come from the official docs as of 2026-10-18: ai.google.dev "latest-model" / "thinking" pages and developers.openai.com models + reasoning guides. Neither model is on a free tier.

**Next steps**
1. (done 2026-10-18) README.md updated: model/compute/translation-engine table, quality comparison, GPU build and packaged self-test commands.
2. (done 2026-10-18) Rebuild + packaged self-test.
3. Real-microphone acceptance on Windows: all modes, hotkey, paste-back, 30-minute run. The user has to speak for this.
4. iOS: needs a Mac with Xcode 16+ to resolve WhisperKit, build, sign with a Personal Team, and test on a device.
5. Optional: a Typeless-style LLM polish step (cleaning up self-corrections and filler words), local-only.

**Risks / constraints**
- Whisper built-in zh→en drops meaning at every size on the 3-sentence corpus (small 1/3, medium 2/3 drops 「明天」, large-v3 2/3 drops 「開會」). Only small + local Ollama gemma4 got 3/3. Ollama is now the default when installed.
- Cloud backup was verified with real keys (supplied by the user in a key file outside the repo; never copy keys into the repo or into reports). Results: `verification/cloud-fallback-2026-10-18.json`. OpenAI took 3.5–5.6 s at every effort level. Gemini took 8–12 s at low/medium; at `high` it took 28 s once and hit the 30 s timeout once. Decided: OpenAI high, Gemini low.
- Cloud backup is opt-in, pay-per-use, and sends transcript text (never audio). Keep it off by default.
