# Agentic platform bridge: lessons and pitfalls (2026-11-09)

**Project:** connect the Jev autoresearch agent to Claude, ChatGPT (GPT-6 Astra) and Gemini (Gemini 4 Argon) through subscription logins instead of API keys; then run live tests on two topics
**Skill produced:** `agentic-platform-bridge/`
**Environment:** Windows 11, PowerShell 5.1 and Git Bash, uv, Python 3.12, Codex CLI 0.166, Gemini CLI 0.67, Claude Agent SDK

> Methods and lessons only. No keys, no patient data, no private paths beyond placeholders.

## One-line summary

**A subscription login works for the vendor that supports it (ChatGPT through Codex), but it removes the spending cap, and "logged in" is not the same as "this model is on my plan" (Gemini).**

## What was built

| Item | Result | Evidence |
|---|---|---|
| `cli` provider type in the LLM layer | ChatGPT auditor through the Codex CLI, no API key | live two-turn call to `gpt-6-astra`: context kept, US$0, about 7.6k tokens per call |
| Default roles | planner Claude Opus, executor Claude Sonnet, auditor `chatgpt:gpt-6-astra` | `run_agent.py --check` |
| Offline tests | 8 new, each can fail | 221 tests pass in total |
| Standalone script | `cli_bridge.py` with `--status` and `ask()` | status, a live ChatGPT call and a bad-effort failure were run |
| Gemini via CLI | reaches Google, **not usable** for `gemini-4-argon` | HTTP 429, "input tokens per day limit exceeded on Free Tier", limit 0 |

## Live runs (Claude writes, ChatGPT audits)

| Run | Setup | Result |
|---|---|---|
| SGLT2 inhibitors and cognition in CKD | Haiku in all roles, 1 loop | COMPLETED, US$0.06, 6 sources, 0 citation problems; the Haiku planner returned malformed JSON |
| Neuroplay norms, 2 loops | Sonnet planner, Haiku executor, ChatGPT auditor | NEEDS_REVIEW, US$0.36, 12 cited sources, audit score 0.56 then 0.76, 1 high finding left |
| Neuroplay norms, 3 loops, with feedback | same models | NEEDS_REVIEW, US$0.45, only 4 cited sources, audit score 0.60, 0.55, 0.55; worse than the 2-loop run |

## Top lessons

1. **The subscription CLI is a real provider.** Wire it as one more `Conversation` class and the rest of the pipeline does not change.
2. **No cost means no cap.** A subscription call reports US$0, so `--budget` stops binding on those calls. Log the deviation; rely on the plan's own limit.
3. **Logged in is not entitled.** Gemini authenticated but had no quota for the new model. Test the model itself with one call.
4. **Do not trust a login file as a status check.** Gemini worked with no `oauth_creds.json`. My first status check was wrong in the "not signed in" direction.
5. **Headless Gemini needs `--skip-trust`.** In a fresh temp dir it exits 55 otherwise. This was found by running it, not by reading the help.
6. **More loops did not help.** The strict auditor raised its bar each loop (cited sample sizes, numeric seeds), and the sources could not meet it. Add evidence, not loops.
7. **A cross-vendor auditor is worth its latency.** It found real defects (an invented EEG component, hypotheses citing sources that do not test them, a lower age threshold read as an observed age band).

## Pitfalls

The full list of 24 items is in `agentic-platform-bridge/references/pitfalls.md`. The ones most likely to cost time:

- Codex `--ignore-user-config` silently drops the effort to "none"; set it with `-c model_reasoning_effort=high`.
- Pass prompts on stdin; arguments break on long or non-ASCII text.
- Windows: `PYTHONIOENCODING=utf-8`, `shutil.which` for `.cmd` shims, and PowerShell 5.1 shows git's stderr as a failure.
- A run that ends NEEDS_REVIEW exits 1, and the harness shows the task as failed.
- A background dashboard was stopped when memory ran low; restart only when asked.

## Open items

- Gemini: confirm the plan and model with the CLI interactively, or fall back to the API key. NotebookLM also needs `nlm login --force`.
- Neuroplay norms: the 2-loop paper is the better draft. A targeted search on norm construction (sample size, continuous norming, bounded-score floor effects) should come before any further loop.
- The `jev-autoresearch-rsi` template in this repo does not yet include the `cli` provider.
- Not tested: a full run with the Gemini CLI as a role, macOS and Linux, Codex on a non-ChatGPT login.
