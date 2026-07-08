---
name: install-skill-pack
description: Install a downloaded collection of Claude Code / Agent skills — either as a toggleable plugin (via a local marketplace) or as flat global skills in ~/.claude/skills. Cross-platform (Windows, macOS, Linux). Use when the user wants to install a skills repo, set up a skills plugin, add skills to the global inventory, enable/disable a skill pack, or fix a failed "/plugin install".
---

# Install a Skill Pack (plugin or global skills)

Two supported ways to install a downloaded skills repo. Pick by **size** and **use pattern**, then follow that section. Cross-platform notes are inline.

## 0. Decide: plugin vs global skills

| Situation | Use | Invocation name | Toggle as a unit |
|---|---|---|---|
| Large domain collection (50+), used only in some projects | **Plugin** (local marketplace) | `/<plugin>:<skill>` | ✅ via `/plugin` |
| A handful of general skills you always want | **Global skills** | `/<skill>` (short) | ✗ (delete files) |

Rule of thumb: **50+ skills → plugin** (so you can disable it and save context in unrelated projects). **A few general skills → global.**

Key mental model: **"enable" is persistent (do once); "invoke" happens every time you use a skill.** Enabling a plugin only makes its skills *available* — you still call a skill each time.

---

## A. Install a big collection AS A PLUGIN (toggleable)

Works when the repo has a top-level `skills/` folder (Claude Code auto-discovers it).

### A1. Write the plugin + marketplace manifests
Claude Code reads `.claude-plugin/plugin.json`; a non-standard file (e.g. `openclaw.plugin.json`) is **ignored**. Generate the correct pair:

```
python scripts/make_plugin_marketplace.py --repo "<REPO_PATH>" \
    --plugin <plugin-name> --marketplace <marketplace-name> --owner <you>
```

This writes `<REPO>/.claude-plugin/plugin.json` and `<REPO>/.claude-plugin/marketplace.json` (plugin `source: "."`).

### A2. Handle spaces in the path (common Windows trap)
`/plugin marketplace add` chokes on paths with spaces. Make a **space-free link** and point the command at that:

- **Windows (PowerShell):** `New-Item -ItemType Junction -Path C:\Skills\pack -Target "D:\My Skill Folder"`
- **macOS / Linux:** `ln -s "/path with spaces" ~/skills-pack`

### A3. Install (INSIDE an interactive Claude Code session — not the OS shell)
`/plugin` is a Claude Code command. Start `claude`, then run **one line at a time** (wait for success between them):

```
/plugin marketplace add <space-free-repo-or-link-path>
/plugin install <plugin-name>@<marketplace-name>
```

CLI equivalent for the first step (works in the OS shell): `claude plugin marketplace add "<path>"`.

### A4. Verify & toggle
`/plugin` → **Installed** → the plugin shows `√ enabled · N skills`. Press **Space** to enable/disable. Run `/reload-plugins` (or restart) after changes.

### A5. Invoke a skill from the plugin
`/<plugin-name>:<skill-name> <your text>` — **no space around the colon.** Best: type `/`, start typing the skill name, and **select** the entry from autocomplete (don't hand-type the colon). Or just describe the task in natural language and let Claude auto-invoke it.

---

## B. Install a small set AS GLOBAL SKILLS (always-on, short names)

Copies each skill folder into the global skills dir (`~/.claude/skills` on macOS/Linux, `%USERPROFILE%\.claude\skills` on Windows — same path via `Path.home()`).

### B1. Copy the skills
```
# Use the repo's own plugin.json skill list (recommended — installs the "released" set):
python scripts/install_global_skills.py --repo "<REPO_PATH>" --from-manifest

# Or pick specific ones:
python scripts/install_global_skills.py --repo "<REPO_PATH>" --only code-review,tdd,research

# Or auto-update on git pull (symlink; needs Developer Mode/admin on Windows):
python scripts/install_global_skills.py --repo "<REPO_PATH>" --symlink
```

The script **flattens** nested layouts (e.g. `skills/engineering/<name>/` → `~/.claude/skills/<name>/`) and skips `deprecated/`.

### B2. Verify & invoke
Restart Claude Code (or `/reload-plugins`). Invoke with the **short name**: `/<skill-name>`, or just describe the task.

### B3. Updating later
Copy mode does **not** auto-update — after `git pull` in the source repo, re-run the copy command. Symlink mode auto-updates but is fragile on Windows.

---

## Pitfalls (learned the hard way)

- **`/plugin` in the OS shell → "Unknown command".** It's a Claude Code slash command; run it inside `claude`, not PowerShell/bash.
- **Space in the repo path → "Invalid marketplace source format".** Use a junction/symlink to a space-free path (A2).
- **Two `/commands` pasted on one line → parse error.** One command, one Enter.
- **`/<plugin>: <skill>` (space after colon) → "Unknown command".** The whole `plugin:skill` must be one token, no spaces.
- **Non-standard manifest** (`*.plugin.json` at root) is ignored — you must create `.claude-plugin/plugin.json` (A1).
- **`/plugin install` copies the whole repo to a cache** — big vendored repos take time/disk; that's expected.
- **Windows long paths / Git LFS** can break `git clone` of huge repos: `git config --system core.longpaths true` and `GIT_LFS_SKIP_SMUDGE=1 git clone …`.
- **Never trust a SKILL.md's API examples verbatim** — versions drift (e.g. an API's `v4`→`v6`, field renames). Inspect the live response.

## Related
- Companion notes: `../2026-07-07 Lessons learned — Claude Code skills 安裝踩坑.md`
- Official docs: code.claude.com/docs/en/plugins and /en/plugin-marketplaces
