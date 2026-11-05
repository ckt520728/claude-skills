# Platform adapters

There are two separate questions: which **model** writes (runtime), and which **agent tool** builds the dashboard using this skill (build time).

## What has been tested

| Item | Status |
|---|---|
| Windows 11, Python 3.12, uv | Tested: offline tests, real browser, live runs |
| Claude through the Agent SDK | Tested live with Haiku. Opus and Sonnet use the same path but have not been run from this template |
| OpenAI-compatible provider | Tested only against a local fake server: history, cost and auth headers. **Not yet run against a real service** |
| macOS and Linux | **Not run.** The code uses `pathlib` and `start_dashboard.sh`; run the verification steps there first |
| NotebookLM through `nlm` | **Never received a real answer.** It reported an expired login on the test machine, even after a successful sign-in |

## Model providers (`provider` in project.json)

### Claude

```json
"provider": {"type": "claude", "models": ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"], "default_model": "claude-opus-5-5"}
```

Uses the Claude Code login, or `ANTHROPIC_API_KEY` if set, which takes priority and is billed to that key. `total_cost_usd` accumulates within a session, so the template charges only the increase.

### OpenAI-compatible

```json
"provider": {
  "type": "openai_compatible",
  "base_url": "https://api.openai.com/v1",
  "api_key_env": "OPENAI_API_KEY",
  "models": ["your-model"],
  "default_model": "your-model",
  "price_per_mtok": {"input": 2.0, "output": 10.0}
}
```

Set current prices from your provider; without them the budget cannot be enforced and the run is refused. For a local model such as Ollama, use `"base_url": "http://localhost:11434/v1"`, omit `api_key_env`, and add `"free": true`. Other services with this interface, including Gemini's OpenAI endpoint and OpenRouter, should work the same way. Confirm the base URL in their current documentation and do a small live run.

Remove `claude-agent-sdk` from `requirements.txt` if you do not need it.

### Another interface

Subclass `Conversation` in `knowledge_agent/llm.py`. It must keep history, so a repair turn can see the answer it is repairing, and must report real cost.

## Agent tools (using this skill to build)

`SKILL.md` is plain Markdown with YAML frontmatter, and `scripts/scaffold.py` needs only Python, so any tool that can read files and run commands can follow it.

| Tool | How to use it |
|---|---|
| **Claude Code** | Copy the folder to `~/.claude/skills/rsi-knowledge-dashboard/`, or install the `.skill` bundle |
| **Codex, OpenCode** | Copy the folder to the project, or to the tool's skills location, and reference `SKILL.md` from `AGENTS.md` |
| **Gemini CLI, Antigravity** | Copy the folder to the tool's skills location, or reference `SKILL.md` from `GEMINI.md` or `AGENTS.md` |
| **ChatGPT and other chat-only tools** | Can help with design and review. Cannot run the local server, so give the user the scaffold commands |

Tool locations change between versions, so check the tool's current documentation.

The finished dashboard does not depend on the tool that built it. `run_agent.py` can also be called by a scheduler or by another agent.

## Moving an existing project

1. Scaffold a fresh project, then copy over `references/`, `terms` and your identifier list.
2. Keep old outputs as they are, and label them clearly as older than the checks.
3. Do not carry over old "verified" claims. Re-check citations by title, and replace static status text.
