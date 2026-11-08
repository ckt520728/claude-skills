# Pitfalls (each one happened while building or running this, 2026-11-08)

## Secrets and config

| Pitfall | What happened | Rule |
|---|---|---|
| Keys pasted into `.env.example` | The user filled in API keys, commented out, in the *tracked* example file. The engine found no keys, and the keys were one commit away from a public repo | Check that `.env` exists and is git-ignored, and that the example file holds no values. Move keys without printing them |
| Guessed model ids | Tier names like "GPT-astra" / "Argon" are not API ids | Read the ids from `--models`. The real ids were `gpt-6-astra`, `gpt-6.1-sol`, `gemini-4-argon`, `gemini-3.8-flash` |
| "sol-high" vs "sol-medium" | The same model at two reasoning efforts | Write them as `@high` / `@medium`, priced by the base id |
| Listed ≠ usable | `gemini-4-argon` was in the model list but returned HTTP 429 (quota) | Ping every model once before a paid run |
| Temporary prices | Gemini launch prices double later | Use the post-introductory rate so the budget errs high |

## Sources

| Pitfall | What happened | Rule |
|---|---|---|
| Wrong `nlm` on PATH | An old v0.7.7 (from another tool's venv) came before the v0.16.1 the MCP server uses | Prefer `~/.local/bin/nlm(.exe)`, the uv-tool install, and fall back to PATH |
| Garbled Chinese from a subprocess | `nlm` piped its output in cp950 on Windows | Set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` in the child process's environment |
| MCP live ≠ engine live | The notebook MCP worked inside the coding agent, but the engine calls the CLI | Test the engine's own connector (`query_notebook`) and check for 0 U+FFFD characters |
| Off-topic evidence | Run 1 cited CML and sensor-control papers in an AI-agents review | Executors flag `off_topic`, and code keeps those sources out of the paper and the checks |
| Secondary answers look primary | NotebookLM answers carry precise numbers that point to no paper | Label the kind as secondary, keep it in the reference list, and say so in the paper's Methods and Limitations |

## Engine and graph

| Pitfall | What happened | Rule |
|---|---|---|
| Cancel recorded as FAILED | anyio wraps a cancel in `BaseExceptionGroup` | Unwrap the group, record CANCELLED, mark running nodes failed and pending ones skipped |
| Parallel jobs overspent | Each deliverable job got the whole remaining budget | Split it with `budget_share = 1/len(jobs)`, plus a mutation test that fails without the split |
| PASS with a high finding | The auditor said PASS, yet listed a high-severity finding | Code forces FAIL when any finding is high or any check fails |
| Sanitizer bypass | `&#x6A;avascript:` got through the URL filter | Decode entities, then check against a scheme allow-list |
| KB edits outside markers | A link repair rewrote text the user had written | Restrict rewrites to managed blocks, with a test |
| Fitness falls as the wiki grows | Absolute counts: 0.906 → 0.879 while quality held | Fixed in `normalised-v2`: each defect is a share of its own denominator (0.886 on the same wiki) |

## Deliverables (found only by reading them)

| Pitfall | Fix |
|---|---|
| "推論解碼" used for speculative decoding | `terms.forbidden` / `terms.preferred`; CleanText now fails on it |
| Slug cut mid-word (`...-in-ai-re`) | Cut on a word boundary (test) |
| Chart label truncated ("NotebookLM answer (seconda") and in English | zh-TW kind labels, truncated with "…" (test) |
| English verified-note inside the zh-TW notice | The blog renderer uses the zh note (test) |
| Personal site and author hard-coded in the renderer | Read from `project.json` → `blog` |

## Tooling and OS

| Pitfall | Rule |
|---|---|
| Git Bash heredocs collapse `\\` → `\`. This put a backspace byte in a regex, made an octal escape out of a path, and let a fixture edit silently not apply | Make backslash edits with a file-edit tool or `chr(92)`, then `grep -c $'\x08'` and assert that each replacement happened |
| Cloud-synced drive (Google Drive G:) | Keep venvs and caches local (uv). Serialize files to memory and write once (PPTX) |
| Windows console cp950 | Printing JSON that contains "ö" crashed the script. Use `PYTHONUTF8=1` |
| `grep -c '<svg'` counts lines | Use `grep -o '<svg' \| wc -l` |
| Dashboard server killed by low memory | It is not a crash. Don't auto-restart; tell the user the restart command |
| Links to `G:\我的雲端硬碟\...` don't open from the terminal | Serve the files through the dashboard (`/outputs/...`) or open them with `Start-Process` |
| Several stale clones of the publishing repo | Stage in a fresh clone; never in one that is behind or holds untracked work |
