# AGENTS.md — running this skill outside Claude Code

The skill is plain markdown plus a Python engine, so any coding agent that can read files and run a shell can use it. Read `SKILL.md` first; this file only maps the Claude Code specifics onto other tools.

## The engine path works everywhere

The dashboard and `run_agent.py` do the planning, the parallel swarm, the audit, the replan, the deliverables and the KB RSI themselves. Your agent only has to:
1. scaffold (`scripts/scaffold.py`)
2. run the verification ladder
3. start a run
4. read the outputs
5. ask before publishing

That path is identical in Claude Code, Codex, Gemini CLI, Antigravity and OpenCode.

```bash
cd <project>
uv run --no-project --python 3.12 --with-requirements requirements.txt python run_agent.py --check
uv run --no-project --python 3.12 --with-requirements requirements.txt --with pytest python -m pytest tests -q
./start_dashboard.sh          # Windows: .\start_dashboard.ps1   → http://127.0.0.1:8090/
```

On a machine without uv: `python -m venv .venv`, then `pip install -r requirements.txt`, then run the same commands with plain `python`. Keep the venv off cloud-synced drives.

## Interactive mode without Claude subagents

`agents/jev-planner.md`, `jev-executor.md` and `jev-auditor.md` are role prompts. Use them like this:

| Tool | Planner / auditor (high tier) | Executors (medium tier, parallel) |
|---|---|---|
| Claude Code | `.claude/agents/jev-*.md` subagents (`model: opus` / `sonnet`) | several `jev-executor` calls in one message |
| Codex CLI | a session on the high model (e.g. `gpt-6-astra`, or `gpt-6.1-sol` with high effort), prompt = role file | separate sessions or `codex exec` per TaskSpec on `gpt-6.1-sol` with medium effort |
| Gemini CLI / Antigravity | `gemini-4-argon` with the role file as system prompt | `gemini-3.8-flash`, one per TaskSpec |
| OpenCode | an agent profile per role | run in parallel per TaskSpec |

Rules that keep it a Jev workflow on any tool:
- The planner outputs JSON only: status, confidence, queries and TaskSpecs. Below 0.85 confidence it asks the user instead of guessing.
- Each executor gets exactly one TaskSpec and produces only its declared outputs.
- The auditor runs in a **fresh context** that did not write the work, preferably on a different provider. It returns PASS/FAIL with findings and never edits. On FAIL, the findings go back to the planner (at most 3 loops).
- Record every departure from the plan in `handoffs.md`.

## Paths and shells

- Use forward slashes in `project.json`, even on Windows (`G:/Vault/知識庫/...`).
- Windows: `.ps1` bodies stay ASCII; put Chinese text in UTF-8 files. Piped child processes may print in the ANSI code page, so set `PYTHONUTF8=1`.
- Git Bash on Windows can collapse `\\` inside heredocs. Make backslash edits with a proper file-edit tool, or build them with `chr(92)`.
