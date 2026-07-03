---
name: publish-lab-blog
description: >-
  Turn a research analysis, paper, or topic into a house-styled, self-contained
  interactive blog post and publish it to Dr. Chu's kidney-cognition-lab site
  (GitHub Pages / Vercel), then mirror to Google Drive. Handles house-style
  extraction, inline colorful SVG/canvas graphics, homepage-card + sitemap
  registration, the Windows push path that actually works here, deployment
  verification, and citation checks. Use when asked to "write a blog post",
  "publish to my homepage", "發佈到首頁", or turn an analysis into a web article.
---

# Publish a post to the kidney-cognition-lab blog

Repeatable pipeline for shipping a Traditional-Chinese popular-science article to
朱國大 醫師's personal site, matching the existing look and deploying it live.

> **Related:** `personal-medical-website` *builds* the site from zero; this skill
> *publishes an individual post* to that already-existing site and registers it on the homepage.

## Facts about the target site

- **Repo:** `https://github.com/ckt520728/kidney-cognition-lab` (public), owner `ckt520728` = kwotachu@gmail.com.
- **Layout:** each post is ONE standalone file in `blog/<slug>.html`. The homepage
  `index.html` lists posts as `<a class="teach-card teach-card-link">` blocks inside
  `#panel-lecture > .teach-grid`, newest first. Deploys via GitHub Pages
  (`https://ckt520728.github.io/kidney-cognition-lab/...`) and Vercel; `.nojekyll` is set.
- **Drive archive folder** `2026 Claude code/` id: `1IWRX34nROcdJxSMfjRcELJU81wMg9NrX`.
- **House palette** (dark theme): bg `#0a0f1e`, card `#111d3c`, teal `#4dd9cf` /
  light `#7ee8e2`, purple `#8b5cf6`/`#a78bfa`, gold `#f4a261`, red `#ef4444`,
  green `#22c55e`, text `#e8f4f8`, secondary `#8ba8c4`, dim `#4a6580`.
  Fonts via CDN: `Noto Sans TC`, `Inter`, `JetBrains Mono`; icons Font Awesome 6.5.

## Step 0 — Clone and study the house style (never guess it)

```bash
cd "$CLAUDE_JOB_DIR/tmp" && git clone --depth 1 https://github.com/ckt520728/kidney-cognition-lab.git repo
```

Read `blog/vbm-ei-alzheimers.html` (the richest template: top-bar, article-header,
callout/formula/table/blockquote, numbered references, interactive dashboard) and the
`#panel-lecture` card block in `index.html`. Copy the CSS `:root` tokens and structural
classes verbatim so the new post is visually identical to siblings.

## Step 1 — Write the post: `blog/<slug>.html`

Structure to mirror: `top-bar` (back link to `../index.html#teaching`) → `article-header`
(`article-meta` date · category, gradient `article-title`, `article-subtitle`, author block,
tags) → hero figure → numbered `<h2>` sections → `Take-home Messages` callout →
numbered `references` → `article-footer` with a "非診斷工具" disclaimer.

**Graphics discipline (this is the point of the post):**
- Everything **self-contained** — inline `<svg>` and `<canvas>`+`<script>`. NO extra asset
  files (siblings ship `.svg`/`.png`/`.js` separately; a single-file post is simpler to
  publish and mirror). CDN fonts/icons are fine (already referenced in `<head>`).
- Include at least one **interactive canvas** in the site's dashboard idiom (slider +
  live redraw + metric bars) and a couple of **colorful SVG diagrams** using the palette.
- Give `<canvas>` a real device-pixel-ratio resize, respect `prefers-reduced-motion`,
  and guard against divide-by-zero in any metric.
- Browser JS may use `Math.random`/`Date` freely (that restriction is only for Workflow
  scripts, not page scripts).

Match the surrounding writing: `【作者】`-vs-`【評估】` honesty, name a concrete
counterexample when the thesis is contestable, and keep the analyst's own stance explicit.

## Step 2 — Register in THREE places (all required)

1. `blog/<slug>.html` — the post itself.
2. `index.html` — a new `<a class="teach-card teach-card-link" ...>` at the **top** of
   `#panel-lecture .teach-grid` (newest first): date, `teach-badge` category +
   `teach-badge purple` ("Blog 全文 · 互動模型"), title, `teach-venue` keywords, blurb,
   and a "閱讀全文" arrow. Copy an existing card and edit — don't invent markup.
3. `sitemap.xml` — a `<url>` entry for the new post + bump the homepage `<lastmod>`.

## Step 3 — Verify citations BEFORE publishing (pitfall P14)

Every DOI / year / title on a public page must be checked against a primary source with
WebSearch. Today a Merker citation was wrong (2013 vs the correct **2016** Front Comput
Neurosci 10:78) and was caught only by verifying. Do not push unverified references.

## Step 4 — Commit and push (Windows-specific — read this)

Set author to match repo history, then commit:

```bash
cd "$CLAUDE_JOB_DIR/tmp/repo" && git config user.name "ckt520728" && git config user.email "kwotachu@gmail.com"
git add blog/<slug>.html index.html sitemap.xml
git commit -m "Add blog post: <topic>

<one-paragraph what/why>

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**Push via PowerShell, NOT Git Bash (pitfall P12).** Git Bash cannot fetch the stored
credential non-interactively (`credential.helper=manager`); it fails with
"could not read Username". PowerShell reaches Windows Credential Manager and pushes
silently:

```
# PowerShell tool:
Set-Location "<repo path>"; git push origin main 2>&1 | Out-String
```

PowerShell wraps git's stderr progress as `NativeCommandError` (red text) even on success —
**trust the `dd..aa  main -> main` line**, not the red wrapper.

## Step 5 — Verify deployment

```bash
curl -s -o /dev/null -w "%{http_code}\n" "https://ckt520728.github.io/kidney-cognition-lab/blog/<slug>.html"   # expect 200 (Pages may lag ~1 min)
curl -s "https://ckt520728.github.io/kidney-cognition-lab/index.html" | grep -c "<slug>"                         # expect 1 (card present)
```

## Step 6 — Copy locally + mirror to Drive

- Copy the post to `C:\Users\YangminRoom1\Documents\Dr Chu's file\Gamma Oscillations and EEG\`
  (or the relevant project folder) so local inventory stays complete.
- Mirror to the Drive folder with `mcp__claude_ai_Google_Drive__create_file`
  (`parentId` above, `contentMimeType:"text/html"`, `disableConversionToGoogleType:true`).
  Use `textContent` for the HTML; `base64Content` works too but the base64 file may exceed
  the Read cap — prefer textContent from a copy you already have in context.
- Tell the user Drive is a **snapshot**; the repo is the source of truth. It won't auto-sync.

## Gotchas (from the field)

- No `gh` CLI here — use `curl` against `api.github.com/repos/.../contents/<dir>` to list, and
  `raw.githubusercontent.com` to read file contents verbatim.
- `blob` GitHub URLs are HTML shells; convert to `raw` for source.
- `git add` prints a harmless `LF will be replaced by CRLF` warning — ignore it.
- Drive `create_file` can't overwrite (always a new file id); version filenames when re-uploading
  and let the user delete old snapshots in the web UI.
- Optional companion deliverable: a screenshot-ready 16:9 comparison **slide** via the Artifact
  tool (load the `artifact-design` skill first; commit to a single dark "neural console" theme).
