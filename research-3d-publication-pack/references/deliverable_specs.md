# Deliverable specs (proven on the 2026-10 HHSA run)

Adapt the topic-specific parts (bands, datasets) to the new project; keep the structure.

## 1. Data contract: one JSON per dataset (analysis → Blender → explorer)

```
{ "dataset": "<id>", "synthetic": bool, "label": "<neutral public label>",
  "units": {"f": "Hz|cph", "t": "s|h"},
  "axes": {"t": [window centres], "fc": [bin centres], "fam": [bin centres], "log": true},
  "bands": [{"name", "lo", "hi"}],
  "params": {layer1, layer2, ensemble, noise_sd, envelope, weight, seed, edge_trim, admissible},
  "record": {"n", "dt", "duration", "nyquist"},
  "encoding": "dense-float16-base64", "shape": [nT, nF, nW],
  "H": "<base64 float16, C order t,fc,fam>",   // THE dense cube. Key is "H". Not "H_b64".
  "H_sparse": [[t, fc, fam, value], ...],       // top-k cells, for Blender
  "band_cube": [...], "admissible_mask": [[bool]],
  "resolvability": {"unresolvable_below_hz", "fc_resolvable": [bool], "fam_resolvable": [bool]},
  "projection_consistency": {...},
  "truth": {...}                                // synthetic only
}
```
- Field names are a contract. Producers may add fields but must not rename these. Write a test that loads every cube with the explorer's reader.
- Check float16 range: max(H) < 65504. Normalize if it is larger.
- Ship the web copies as compact JSON (`separators=(',',':')`). Pretty-printed files were about 2× bigger.
- Every number quoted anywhere comes from a facts file written by code. The template is `templates/demo_facts.py`. Rerun it after every analysis change.

## 2. Website (`site/`, published as `<site_dir>/`)

| Page | Purpose |
|---|---|
| index.html | Hero (Blender render), thesis, entry cards, mini turntable (same explorer module) |
| explorer.html | The 3-D tool (below) |
| method.html | The method in steps, including a validation table built from the facts file |
| demos.html | One card per dataset: provenance, metrics table, "Can claim" vs "Cannot claim" |
| library.html | The user's own papers (DOI); the new paper as a **summary only**; deck and PPTX buttons (`data-alt` fallback); blog link |
| links.html | Curated external papers, grouped, each with a checked HTTP status |
| about.html | Author (from the homepage!), disclaimer, data provenance, licence |

Explorer (template: `templates/site/`):
- Axes: x = carrier, y = AM, z = time, all on log-spaced bins.
- Point cloud: size and colour ∝ energy above a threshold slider.
- Three orthogonal slice planes, plus three linked 2-D projections S(t,f), C(f,w), M(t,w). Clicking a projection sets the slice.
- Dataset pills and a badge stating synthetic vs real (n, consent).
- Toggles: admissibility f_AM < f_c, 3/T unresolvable hatching, band slabs, turntable.
- Camera presets: oblique, top = C, side = S, front = M.
- A "What am I looking at?" guide per dataset, written from the facts file.
- Three.js 0.160.0 through an **import map**. The Blender GLB supplies the frame, labels and truth ridge only; the browser draws the data.
- `file://` notice and `start_local_server.bat`.

Blender (template: `templates/blender_build_scene.py`, run `blender -b -P`):
- Cube space is [0, 10]³ with x = f_c, y = f_AM, z = t, Z-up.
- In three.js, rotate the model +90° about X and position it at (-5, -5, -5).
- Keep at most about 400 icospheres per GLB.
- Hide `EnergyLobes` and `BandLandscape` in the browser.
- Render a 1920×1080 hero image and a turntable video.

Palette (shared by site, deck and blog): bg `#0a0f1e`, cards `#111d3c`, teal `#4dd9cf`, purple `#8b5cf6`, gold `#f4a261`, text `#e8f4f8` / `#8ba8c4`. Fonts: Inter, Noto Sans TC, JetBrains Mono. Provide a light theme too.

## 3. Review paper (English; default journal Frontiers in Aging Neuroscience, Review)

- Verify the journal rules live before formatting:
  - word cap (Review 12,000);
  - reference style (Harvard vs Vancouver);
  - abstract limit;
  - 5–8 keywords;
  - figures 300 dpi RGB TIFF/JPEG;
  - ethics statement, generative-AI disclosure, no unpublished material.
- Sections: Abstract → 1 Introduction → 2 Framework → 3 Search strategy (PRISMA-ScR, with exact queries, dates and counts) → 4.x Evidence by system → 5 Worked demonstrations → 6 Discussion (pitfalls, reporting checklist, outlook) → 7 Conclusion → End matter.
- Write the Markdown with Pandoc citations `[@key]`. Every key must be in `references.bib`; the build fails otherwise.
- Build the DOCX with `scripts/md_to_docx.py`. It renders math and author-year citations and embeds the figures. Then convert it to PDF and look at it.
- §5 states the real results, including failed targets. Its method parameters must match the code exactly.
- End matter rules:
  - author, affiliations and email come **only** from the user's homepage or the user;
  - funding is a placeholder unless the user gives it;
  - the AI disclosure is truthful (agents drafted text, ran searches, wrote code);
  - IRB details are a placeholder.
- The paper does not go into a public repo before submission unless the user says so; posting it there counts as a preprint.

## 4. Decks (English, SOIL, 20 slides, 16:9)

SOIL arc: State (slides 2–4) → Opportunity (5–7) → Implementation (8–15, including a live 3-D widget on slide 8 and one slide per demo) → Leverage (16–19) → take-home (20).
- **HTML deck**: follow the `soil-html-deck` skill. Use an import map for Three.js. Slide 8 loads the **real** synthetic cube (`../site/…` locally, `../<site_dir>/…` in the repo), never random points. Speaker notes run 60–120 words per slide, and the numbers in them match the facts file.
- **PPTX**: use the `soil-teaching-deck` skill or adapt `templates/generate_pptx_example.py` (python-pptx). Render the slides through PowerPoint COM with an **absolute** output path and look at the PNGs; the bounds audit does not catch text overflowing its box.

## 5. Homepage blog post (Traditional Chinese, Taiwan)

- Copy the homepage's latest HHSA post for the `:root` tokens and class skeleton: `.top-bar` → `article.article > header.article-header` → numbered 一、二、三 `h2` → `.dashboard` widget → `.callout` → `.tbl-wrap` → 延伸閱讀（本站） → 參考資料 `.references`.
- Length 3,500–4,500 characters, first-person physician-scientist voice, ending in an honest ledger of limits and a disclaimer callout.
- Tag claims `observed`, `derived` or `hypothesis`. Demo numbers come from the facts file.
- Link to the 3-D site with relative repo paths: `../hhsa-3d/…`, `../slides/…`.
