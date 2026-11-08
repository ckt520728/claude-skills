# Providers and tiers

A model reference is `provider:model[@effort]`. The provider must exist in `project.json` → `providers`.

| Tier | Claude | OpenAI | Gemini |
|---|---|---|---|
| high (planner, auditor) | `claude:claude-opus-5-5` | `openai:gpt-6-astra`, `openai:gpt-6.1-sol@high` | `gemini:gemini-4-argon` |
| medium (executors, writer) | `claude:claude-sonnet-5-5`, `claude:claude-haiku-5-5` | `openai:gpt-6.1-sol@medium` | `gemini:gemini-3.8-flash` |

These ids were read with `run_agent.py --models` on 2026-11-08. **Re-read them on every new machine or key.** Never type an id from memory.

## Default roles

`default_roles()` builds the default roles from the tiers:
- **planner:** the first usable high-tier model
- **executor:** the first usable medium-tier model
- **auditor:** the first high-tier model from a *different provider than the executor*

With the template tiers that gives Opus / Sonnet / gpt-6-astra. Any role can be overridden in the dashboard or with `--planner/--executor/--auditor`.

## Effort suffix

`gpt-6.1-sol@high` sends `"reasoning_effort": "high"` to the chat/completions endpoint.
- Allowed values: `none, minimal, low, medium, high, xhigh`.
- An unknown value raises an error; it is never silently dropped.
- Prices are looked up by the base id (`gpt-6.1-sol`).

## Prices (USD per 1M tokens, input / output)

| Model | Price | Source |
|---|---|---|
| gpt-6-astra | 10 / 50 | developers.openai.com/api/docs/pricing |
| gpt-6.1-sol | 2 / 10 | same |
| gemini-4-argon | 4 / 20 | ai.google.dev/gemini-api/docs/pricing, post-introductory rate (from 2026-12-01) |
| gemini-3.8-flash | 1.5 / 7.5 | same, post-introductory rate (from 2027-01-01) |

- Use the *higher* rate when a discount is temporary, so the budget over-estimates rather than under-estimates.
- OpenAI prompts over 272K tokens cost more; the engine's prompts stay far below that.
- Claude cost comes from the Agent SDK's reported cost.

## Checks before a paid run

1. `--check` shows each provider as available, with its key present and every model priced.
2. Ping each model with one tiny prompt (cost is a fraction of a cent). Watch for:
   - **HTTP 429 "exceeded your current quota"**: the key lists the model, but billing or quota is not enabled for it. Don't use that model until it's fixed.
   - **Very slow replies** (205 s observed on a free-tier Flash key). Expect rate limiting on free tiers.
3. Parallel deliverable jobs each get `1/len(jobs)` of the remaining budget, so they can't overspend together.

## Gaps still open

- OpenAI-compatible calls have no per-call token cap. Cost is checked between calls, not within one.
- Prices are hand-entered from public pages. Re-check them when a model's launch pricing ends.
