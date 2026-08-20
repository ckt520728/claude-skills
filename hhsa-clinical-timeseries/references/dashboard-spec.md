# The one-page HHSA dashboard — design contract

`scripts/build_dashboard.py` renders `results.json` + `figs/` into a single HTML
file. This is what it guarantees and why.

## Hard constraints

1. **One file, no network.** Figures are inlined as `data:` URIs. The page must
   render with the machine offline and must survive being emailed as an
   attachment. No CDN fonts, no external CSS, no analytics.
2. **Every number comes from `results.json`.** The template contains no
   hard-coded findings. If a value is not in the JSON it does not appear on the
   page. This is what makes the dashboard auditable rather than decorative.
3. **Light and dark.** Palette lives in CSS custom properties on bare `:root`;
   dark is redefined under `@media (prefers-color-scheme: dark)` guarded with
   `:root:not([data-theme="light"])`, and again under `:root[data-theme="dark"]`.
   `body` sets an explicit background token — a transparent body borrows the
   host's ground and produces one theme's text on the other theme's background.
4. **Wide content scrolls inside its own box.** Tables get
   `overflow-x: auto` on a wrapper; the page body never scrolls sideways.

## Reading order

The page is built to be read top-down by a clinician or a reviewer who will not
run the code:

| Block | Question it answers |
|---|---|
| Verdict cards | What should I take away in 15 seconds? |
| 01 What the data can support | Is this resolution real, or vendor smoothing? |
| 02 Scale decomposition | Where does the variance actually live? |
| 03 Layer 2 / holo-spectrum | Which carrier is modulated by which? |
| 04 Is any of it more than noise? | Would a linear null have produced this? |
| 05 Band occupancy | The clinical summary numbers, if bands were given |
| 06 Limits | What this record cannot support |

Resolution comes **before** decomposition on purpose. A reader who sees the IMF
table first will interpret IMF1 physiologically; a reader who first learns the
effective resolution is 15 minutes will not.

## Honesty rules baked into the renderer

- **Null results get the same visual weight as positive ones.** A statistic below
  its null is rendered `below null` in the warning colour, not hidden — see
  pitfall 8. `_verdict()` returns three states, never a bare "significant".
- **The white-noise-null column is annotated in-page** as white, so a reader does
  not conclude that a red signal's fast modes are artefacts.
- **The AAFT caveat is printed next to the AAFT results**, not in a footnote:
  those surrogates preserve the spectrum, so they cannot test whether a rhythm
  exists. Only the rotation test licenses the word "entrained".
- **Variance sum and reconstruction error are shown**, so a reader can see the
  modes are not exactly orthogonal.
- **The short-record limitation is emitted automatically** when fewer than 20
  full cycles are present.

## What NOT to put on the page

- Any clinical recommendation. The dashboard describes a signal. Treatment
  decisions need medication timing, meal logs and covariates that are not in a
  time series.
- Direct patient identifiers. If the source carried a name, MRN, device serial or
  exact calendar dates, they must be stripped before `results.json` is written —
  the dashboard is a shareable artifact by design.
- Any number the pipeline did not compute.

## Extending it

Add a section by adding a key to `results.json` and a block to the f-string. Keep
the two in step: a template referencing a missing key raises `KeyError` at render
time, which is the intended failure — better than silently publishing a blank.

Use `R.get(key, default)` only where the block is genuinely optional (bands,
rotation test on a too-short record).
