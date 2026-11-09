---
name: agentic-platform-bridge
description: |
  Connect one agent workflow to Claude, ChatGPT (GPT-6 Astra) and Gemini (Gemini 4 Argon) through their own subscription logins, with no API keys. Claude uses the Claude Agent SDK / Claude Code login, ChatGPT uses the Codex CLI (`codex login`), and Gemini uses the Gemini CLI (Google login). Each CLI runs as a stateless subprocess, so a planner, an executor and an independent auditor can sit on three different vendors.
  Includes a stdlib-only script (`scripts/cli_bridge.py`) with a status check and an `ask()` function, a provider-type pattern for an existing LLM layer, and a pitfalls list measured on Windows.
  Use when the user asks to "use my ChatGPT / Gemini subscription instead of an API key", "login to ChatGPT during the workflow", "let GPT audit Claude's work", "cross-vendor auditor", "connect Claude, GPT and Gemini", "Codex CLI as a provider", "Gemini CLI headless", "跨平台 agent 串接", "用訂閱登入代替 API key".
---

# Agentic platform bridge

Run one workflow across Claude, ChatGPT and Gemini using the logins you already pay for.

## When this is worth doing

- An **independent auditor on another vendor** catches what the writer's own vendor misses. This is the main reason.
- You already subscribe to ChatGPT or Gemini and do not want a second, metered API bill.

Not worth it when you need a hard spending cap, low latency, or parallel calls at scale. Use the API for those.

## Quick start

1. Install and log in once (interactive, a human must do this):
   - ChatGPT: `npm install -g @openai/codex`, then `codex login`
   - Gemini: `npm install -g @google/gemini-cli`, then run `gemini` once and choose Login with Google
   - Claude: Claude Code login (the Agent SDK reuses it)
2. Check, spending nothing: `python scripts/cli_bridge.py --status`
3. One real call: `python scripts/cli_bridge.py --provider chatgpt --model gpt-6-astra --effort high --prompt "Reply: PONG"`
4. In code: `from cli_bridge import ask` then `ask("chatgpt", "gpt-6-astra", prompt, system="...")`

## How each platform is called

| Platform | Command shape | Notes |
|---|---|---|
| ChatGPT | `codex exec --skip-git-repo-check --ephemeral --ignore-user-config --sandbox read-only -m MODEL -o FILE -` | Prompt on stdin (`-`). Answer is read from the `-o` file. Effort: `-c model_reasoning_effort=high`. Verified: `gpt-6-astra` answers on a ChatGPT login. |
| Gemini | `gemini -m MODEL -o text --approval-mode plan --skip-trust -p "Answer the message provided on stdin."` | Prompt on stdin. `--skip-trust` is required in a fresh temp dir. |
| Claude | Claude Agent SDK `ClaudeSDKClient`, or `claude -p` | Reuses the Claude Code login. The SDK reports real cost. |

Every CLI call runs in an **empty temp directory** with a read-only or plan-mode sandbox, so the agent has nothing to read or change.

## Design rules for the provider layer

1. **Add a provider type, do not fork the pipeline.** One `Conversation.send(prompt) -> Reply(text, cost, tokens)` interface; a CLI provider is one more class. See `references/provider-pattern.md`.
2. **Stateless turns: resend the transcript.** A repair turn must see the answer it is repairing.
3. **Cost is 0 for a subscription call.** That means a `--budget` limit does **not** bind it. Say so in the project log, and rely on the plan's own usage limit. Keep API-priced providers refused when they have no price.
4. **Never invent success.** A missing CLI, a logged-out CLI, a non-zero exit or empty text raises an error with the CLI's own message. No placeholder text.
5. **Put the new providers ahead of the API ones** in the tier lists, keep the API providers as fallbacks, and prefer an auditor from a different vendor than the writer.
6. **Read model ids from the vendor**, never guess them. A model that works on an API key may not be on the subscription plan.
7. **Status must come from a measurement.** Check install and `codex login status`; for Gemini the login file is not a reliable signal, so one real call is the test.

## Measured status (2026-11-09, Windows 11)

| Platform | Result |
|---|---|
| ChatGPT via Codex 0.166 | Works. `gpt-6-astra` and context across turns verified; cost US$0; about 7.6k tokens per call even for a one-word reply. |
| Claude via Agent SDK | Works. Real cost reported. |
| Gemini via Gemini CLI 0.67 | Reaches Google and authenticates, but `gemini-4-argon` returned HTTP 429, "input tokens per day limit exceeded on Free Tier", quota 0. The account was seen as free tier, so the Gemini subscription was **not** confirmed for this model. Not usable yet. |

Read `references/pitfalls.md` before wiring this into a long-running workflow.
