# Claude Code CLI — Session Lessons & Pitfalls (2026-06-18)

## Session Context
Setting up Claude Code CLI on Windows, navigating to a project directory, and running `/init` on a project.

---

## Key Lessons & Pitfalls

### Pitfall 1 — `/init` is a Claude Code slash command, NOT a shell script
**Symptom:** Typing `/init` in PowerShell gives a red error:
> "The term '/init' is not recognized as the name of a cmdlet, function, script file, or operable program."

**Why:** `/init`, `/help`, `/code-review` etc. are Claude Code internal commands. They only work INSIDE the Claude Code interactive session prompt.

**Fix:** Run `claude` first to enter the session, THEN type `/init`.

---

### Pitfall 2 — `claude` command not found outside install directory
**Symptom:** `claude` works from `.local\bin` but throws "CommandNotFoundException" from any other directory.

**Why:** `C:\Users\YuyingRoom2\.local\bin` is not in the system PATH.

**Fix — Permanent (requires PowerShell restart):**
```powershell
[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";C:\Users\YuyingRoom2\.local\bin", "User")
```

---

### Pitfall 3 — Claude Code working directory is fixed at launch
**Symptom:** Running `cd "C:\project"` inside a running Claude Code session does NOT move the session root. `/init` still operates on the original directory.

**Why:** The session working directory is set once when `claude` starts. It cannot be changed mid-session.

**Fix:** Always `cd` to the target project directory FIRST, then run `claude`.

```powershell
cd "C:\Users\YuyingRoom2\2026 Claude code"
claude
# Then inside Claude Code:
/init
```

---

### Pitfall 4 — Spaces in directory names require quoting
**Symptom:** `cd C:\Users\YuyingRoom2\2026 Claude code` fails with "too many arguments".

**Fix:** Always double-quote paths with spaces:
```powershell
cd "C:\Users\YuyingRoom2\2026 Claude code"
```

---

### Pitfall 5 — Image pasting (Ctrl+V) not supported in Claude Code CLI
**Symptom:** Pressing Ctrl+V in the Claude Code CLI prompt does nothing for images.

**Why:** The CLI only accepts text input. Image paste works on claude.ai web, not the terminal.

**Fix:** Save the screenshot as a file, then reference it by absolute path in your prompt:
```
Please read C:\Users\YuyingRoom2\Desktop\screenshot.png
```

---

### Pitfall 6 — Mapped drives (G:) inaccessible from Claude Code shell tools
**Symptom:** Writing to `G:\Second Brain\...` fails: "A drive with the name 'G' does not exist."

**Why:** The sandboxed shell in Claude Code does not inherit mapped network/cloud drives.

**Fix:** Use the Google Drive MCP tools to write directly, or save to a local path and sync manually.

---

## Correct End-to-End Workflow

```powershell
# 1. Open PowerShell (Win+X -> Terminal)
# 2. Navigate to project (quote if spaces in path)
cd "C:\Users\YuyingRoom2\2026 Claude code"
# 3. Start Claude Code
claude
# 4. Inside Claude Code interactive prompt, type:
/init
```

---

## Resources
- Multi-Agent Research Skill v2.5: https://github.com/ckt520728/2026-Hermes/blob/main/multi_agent_research_skill_v2.5.md
- PHCSSM workflow script: `phcssm_multi_agent_analysis_workflow.js` (same folder)
- Paper: arXiv 2604.01295 — "Parallelized Hierarchical Connectome" (Po-Han Chiang, NYCU, 2026)
