# Provider pattern: add a CLI provider to an existing LLM layer

Reference implementation: `app/knowledge_agent/llm.py` in the 2026 Autoresearch RSI project (`CliConversation`, `_cli_status`). Eight offline tests are in `tests/test_llm_cli.py` there.

## Config (project.json)

```json
"providers": {
  "claude":     { "type": "claude" },
  "chatgpt":    { "type": "cli", "cli": "codex", "default_effort": "high" },
  "gemini-cli": { "type": "cli", "cli": "gemini" },
  "openai":     { "type": "openai_compatible", "...": "API fallback" },
  "gemini":     { "type": "openai_compatible", "...": "API fallback" }
},
"tiers": {
  "high":   ["claude:claude-opus-5-5", "chatgpt:gpt-6-astra", "gemini-cli:gemini-4-argon", "openai:gpt-6-astra"],
  "medium": ["claude:claude-sonnet-5-5", "chatgpt:gpt-6.1-sol@medium", "openai:gpt-6.1-sol@medium"]
}
```

A model reference is `provider:model[@effort]`. The default auditor is the first high-tier model whose provider differs from the writer's.

## Changes to the LLM layer

1. A `CliConversation(Conversation)` that builds the command, runs it with `subprocess.run(..., input=transcript, cwd=<empty temp dir>)`, and returns `Reply(text, 0.0, tokens)`.
2. `_price_known`: a `cli` provider needs no price (flat cost).
3. `provider_status`: for `cli`, report install and login state from local reads only.
4. `open_conversation`: dispatch `type == "cli"`.

## Tests that must exist (each can fail)

- unknown `cli` raises; missing executable raises (no placeholder);
- the Codex command reads stdin (`-`), sets the effort, and the `@suffix` beats `default_effort`;
- a bad effort suffix is rejected;
- a repair turn's transcript contains the answer being repaired;
- a non-zero exit raises with the CLI's own error text.
