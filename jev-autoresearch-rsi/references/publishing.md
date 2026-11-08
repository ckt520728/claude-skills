# Publishing the blog (gated)

## What a run produces

`outputs/runs/<run_id>/blog_publish/` contains:
- `<slug>.html`: a self-contained zh-TW post in the house style
  - palette `#0a0f1e` / `#4dd9cf` / `#8b5cf6` / `#f4a261`
  - two inline SVG charts and one interactive canvas, with all data from the run's real evidence counts
  - an AI-assistance notice and a numbered reference list
- `teach-card.html`: the homepage card snippet
- `sitemap-entry.xml`: one `<url>` with `blog.site_url`

The site URL, author, avatar and bio come from `project.json` → `blog`. Nothing personal is hard-coded.

## Staging (safe, local)

1. Clone the site repo **fresh** into a scratch folder. Don't stage in an old clone: old clones may be behind or carry untracked work.
2. Copy the post to `blog/<slug>.html`.
3. Insert the card at the top of the blog/teaching list (newest first), matching the indentation of the cards around it.
4. Add the sitemap entry before `</urlset>`, and bump the homepage `<lastmod>`.
5. Apply any fixes found when reading the outputs to the staged copy. Run outputs stay as generated.
6. Open the post and the homepage in a real browser (Playwright, Edge or Chrome):
   - 0 page errors
   - the card is present
   - the charts render
   - check the labels by eye
7. Count inline SVGs with `grep -o '<svg' file | wc -l`, not `grep -c`, which counts lines.
8. Commit locally, staging only the post, the homepage and the sitemap.

## Gate

**Stop. Show the user the staged diff and the screenshots, and ask.** After an explicit yes:
1. Fetch and rebase if `origin` moved.
2. Push. On Windows, push from PowerShell.
3. Confirm the deployment with `curl -I https://<site>/blog/<slug>.html`, for every host the site deploys to (for example both Vercel and GitHub Pages).

Before approving, check the site for an existing post on the same topic.
