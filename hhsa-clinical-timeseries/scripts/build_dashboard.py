"""
build_dashboard.py -- results.json + figs/ -> one self-contained HTML page.

Design contract (see ../references/dashboard-spec.md):
  - single file, figures inlined as data URIs, no external requests
  - works in light and dark, via CSS custom properties defined at :root
  - reads top-down: verdict cards -> what the data is -> scales -> tests -> caveats
  - EVERY number comes from results.json; nothing is written into the template
  - the null results get equal billing with the positive ones

Called by hhsa_pipeline.py, or standalone:
    python build_dashboard.py out/
"""
import base64, json, os, sys


def _img(path):
    if not os.path.exists(path):
        return ''
    b = base64.b64encode(open(path, 'rb').read()).decode()
    return f'data:image/png;base64,{b}'


def _fig(path, cap):
    src = _img(path)
    if not src:
        return ''
    return (f'<figure class="fig"><img src="{src}" alt="{cap}">'
            f'<figcaption>{cap}</figcaption></figure>')


def _verdict(p):
    """Turn a one-sided p into an honest label. Both tails matter: a statistic
    far BELOW its null is a finding, not a failure."""
    if p < 0.05:
        return 'above null', 'sig'
    if p > 0.95:
        return 'below null', 'inv'
    return 'not distinguishable', 'ns'


def build(R, outdir):
    u = R.get('unit', '')
    figs = os.path.join(outdir, 'figs')

    # ---- cards -----------------------------------------------------------
    cards = []
    aud = R.get('audit', {})
    q, qs = aud.get('lattice_step'), aud.get('lattice_score', 1)
    res_txt = (f'Values sit on a {q:.4g} {u} lattice.' if qs < 0.05
               else 'No quantisation lattice detected.')
    cards.append(('Effective resolution',
                  f'{res_txt} Analysed at {R["dt_min"]:g} min '
                  f'(native {R.get("native_cadence_min", float("nan")):.1f} min).',
                  'ok'))

    cyc = R.get('cycle_var_pct', 0)
    cards.append((f'Dominant {R.get("cycle_period_h", 0):.1f} h mode',
                  f'IMF{R.get("cycle_imf")} carries {cyc:.1f} % of the variance.',
                  'ok'))

    rot = R.get('rotation') or {}
    ve = rot.get('var_explained_pct', {})
    if ve:
        lab, cls = _verdict(ve.get('p_one_sided', 1))
        cards.append(('Locked to the clock?',
                      f'Phase alone explains {ve["observed"]:.1f} % of variance '
                      f'(null {ve["null_mean"]:.1f} %), p = {ve["p_one_sided"]:.4f}.',
                      'ok' if lab == 'above null' else 'neg'))

    am = (R.get('aaft') or {}).get('am_depth', {})
    if am:
        lab, cls = _verdict(am.get('p_one_sided', 1))
        cards.append(('Cross-scale structure vs linear null',
                      f'AM depth {am["observed"]:.3f} against '
                      f'{am["sur_mean"]:.3f} ± {am["sur_sd"]:.3f} — {lab}.',
                      'neg' if lab != 'above null' else 'ok'))

    card_html = ''.join(
        f'<div class="card"><span class="k">{k}</span><span class="v">{v}</span>'
        f'<span class="chip {c}">{"verified" if c=="ok" else "read with care"}</span></div>'
        for k, v, c in cards)

    # ---- IMF table -------------------------------------------------------
    rows = ''
    mx = max((i.get('var_pct', 0) for i in R.get('imfs', [])), default=1)
    for i in R.get('imfs', []):
        above = i.get('above_null')
        cls = 'hi' if above else ''
        vp = i.get('var_pct', 0)
        rows += (f'<tr class="{cls}"><td class="lbl">IMF{i["imf"]}</td>'
                 f'<td class="num">{i["period_h"]:.2f}</td>'
                 f'<td class="num">{vp:.1f}</td>'
                 f'<td class="barcell"><span class="bar" '
                 f'style="width:{100*vp/mx:.1f}%"></span></td>'
                 f'<td class="num">{i.get("mean_amp", 0):.3f}</td>'
                 f'<td class="num">{i.get("am_depth", float("nan")):.2f}</td>'
                 f'<td class="num {"yes" if above else "no"}">'
                 f'{"yes" if above else "no"}</td></tr>')

    # ---- test table ------------------------------------------------------
    trows = ''
    for k, v in (R.get('aaft') or {}).items():
        lab, cls = _verdict(v['p_one_sided'])
        trows += (f'<tr><td class="lbl">AAFT · {k}</td>'
                  f'<td class="num">{v["observed"]:.3f}</td>'
                  f'<td class="num">{v["sur_mean"]:.3f} ± {v["sur_sd"]:.3f}</td>'
                  f'<td class="num p {cls}">{v["p_one_sided"]:.3f}</td>'
                  f'<td>{lab}</td></tr>')
    for k, v in (R.get('rotation') or {}).items():
        if not isinstance(v, dict):
            continue
        lab, cls = _verdict(v['p_one_sided'])
        trows += (f'<tr><td class="lbl">Rotation · {k}</td>'
                  f'<td class="num">{v["observed"]:.3f}</td>'
                  f'<td class="num">{v["null_mean"]:.3f}</td>'
                  f'<td class="num p {cls}">{v["p_one_sided"]:.4f}</td>'
                  f'<td>{lab}</td></tr>')

    brows = ''.join(
        f'<tr><td class="lbl">{b["name"]}</td>'
        f'<td class="num">{b["lo"]:g}–{b["hi"]:g}</td>'
        f'<td class="num">{b["pct"]:.1f}</td></tr>' for b in R.get('bands', []))
    band_block = (f'<h2><span class="n">05</span>Band occupancy</h2>'
                  f'<div class="tablewrap"><table><thead><tr><th>Band</th>'
                  f'<th>Range ({u})</th><th>% of record</th></tr></thead>'
                  f'<tbody>{brows}</tbody></table></div>') if brows else ''

    n_cyc = (R.get('rotation') or {}).get('n_cycles', 0)
    short = n_cyc and n_cyc < 20

    return f"""<title>{R.get('label', 'HHSA Report')}</title>
<style>
:root {{
  --ground:#F5F7F9; --surface:#FFFFFF; --surface-2:#EDF1F5;
  --ink:#131820; --ink-2:#4C566A; --ink-3:#78849A;
  --rule:#DCE2EA; --rule-2:#C3CCD8;
  --accent:#1F3A6E; --crit:#A81D36; --crit-soft:#FAE8EB;
  --good:#3B6A4D; --good-soft:#E6EFE8;
  --warn:#8A5A12; --warn-soft:#F8EEDC;
  --font-body:"Iowan Old Style","Palatino Linotype","Book Antiqua",Palatino,Georgia,serif;
  --font-mono:ui-monospace,"SFMono-Regular","Cascadia Mono",Consolas,monospace;
}}
@media (prefers-color-scheme:dark) {{
  :root:not([data-theme="light"]) {{
    --ground:#0D1117; --surface:#151B23; --surface-2:#1C2430;
    --ink:#E4E9F0; --ink-2:#9AA5B6; --ink-3:#727E92;
    --rule:#242D3A; --rule-2:#33404F;
    --accent:#94B4EE; --crit:#F08599; --crit-soft:#3B1621;
    --good:#8AC69C; --good-soft:#14301E;
    --warn:#E0B063; --warn-soft:#33260F;
  }}
}}
:root[data-theme="dark"] {{
  --ground:#0D1117; --surface:#151B23; --surface-2:#1C2430;
  --ink:#E4E9F0; --ink-2:#9AA5B6; --ink-3:#727E92;
  --rule:#242D3A; --rule-2:#33404F;
  --accent:#94B4EE; --crit:#F08599; --crit-soft:#3B1621;
  --good:#8AC69C; --good-soft:#14301E;
  --warn:#E0B063; --warn-soft:#33260F;
}}
*{{box-sizing:border-box}}
body{{background:var(--ground); color:var(--ink); font-family:var(--font-body);
  font-size:16.5px; line-height:1.6; margin:0; padding:0 20px 80px;}}
.wrap{{max-width:1060px; margin:0 auto}}
header{{max-width:1060px; margin:0 auto; padding:56px 0 30px;
  border-bottom:2px solid var(--ink)}}
.eyebrow{{font-family:var(--font-mono); font-size:11px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--ink-3); margin:0 0 16px}}
h1{{font-size:clamp(2rem,4.6vw,3rem); line-height:1.06; margin:0 0 14px;
  letter-spacing:-.02em; font-weight:600; text-wrap:balance}}
.meta{{display:flex; flex-wrap:wrap; gap:6px 24px; font-family:var(--font-mono);
  font-size:12px; color:var(--ink-3)}}
.meta b{{color:var(--ink-2); font-weight:500}}
section{{margin:46px auto 0; max-width:1060px}}
h2{{font-size:1.5rem; margin:0 0 10px; letter-spacing:-.012em; font-weight:600}}
h2 .n{{font-family:var(--font-mono); font-size:.7em; color:var(--accent);
  margin-right:.6em; font-weight:400}}
p{{margin:0 0 14px; max-width:72ch}}
.cards{{display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
  gap:14px}}
.card{{background:var(--surface); border:1px solid var(--rule); padding:18px;
  display:flex; flex-direction:column; gap:9px}}
.card .k{{font-family:var(--font-mono); font-size:10.5px; letter-spacing:.11em;
  text-transform:uppercase; color:var(--ink-3)}}
.card .v{{font-size:1rem; line-height:1.45}}
.chip{{align-self:flex-start; font-family:var(--font-mono); font-size:10px;
  letter-spacing:.08em; text-transform:uppercase; padding:3px 8px;
  border:1px solid currentColor}}
.chip.ok{{color:var(--good); background:var(--good-soft)}}
.chip.neg{{color:var(--warn); background:var(--warn-soft)}}
.tablewrap{{overflow-x:auto; margin:18px 0; border:1px solid var(--rule);
  background:var(--surface)}}
table{{border-collapse:collapse; width:100%; font-size:.88rem}}
th,td{{padding:8px 12px; text-align:left; border-bottom:1px solid var(--rule)}}
thead th{{font-family:var(--font-mono); font-size:10px; letter-spacing:.09em;
  text-transform:uppercase; color:var(--ink-3); font-weight:500;
  background:var(--surface-2); white-space:nowrap}}
tbody tr:last-child td{{border-bottom:none}}
td.num{{font-family:var(--font-mono); font-variant-numeric:tabular-nums;
  text-align:right; white-space:nowrap}}
td.lbl{{font-weight:600; white-space:nowrap}}
tr.hi td.lbl{{color:var(--accent)}}
td.yes{{color:var(--good); font-weight:600}}
td.no{{color:var(--ink-3)}}
td.p.sig{{color:var(--accent); font-weight:600}}
td.p.inv{{color:var(--warn); font-weight:600}}
td.p.ns{{color:var(--ink-3)}}
.barcell{{width:26%; min-width:80px}}
.bar{{display:block; height:8px; background:var(--accent); opacity:.75}}
.fig{{margin:22px 0}}
.fig img{{width:100%; height:auto; display:block; border:1px solid var(--rule);
  background:#fff}}
.fig figcaption{{font-family:var(--font-mono); font-size:11px; color:var(--ink-3);
  margin-top:8px; line-height:1.5}}
.callout{{background:var(--surface); border:1px solid var(--rule);
  border-left:3px solid var(--accent); padding:16px 20px; margin:22px 0;
  font-size:.95rem; color:var(--ink-2)}}
.callout.warn{{border-left-color:var(--warn); background:var(--warn-soft)}}
.callout p:last-child{{margin-bottom:0}}
ul{{margin:0 0 14px; padding-left:1.2em; max-width:72ch}} li{{margin-bottom:7px}}
footer{{max-width:1060px; margin:40px auto 0; padding-top:20px;
  border-top:1px solid var(--rule); font-family:var(--font-mono);
  font-size:11px; color:var(--ink-3); line-height:1.7}}
@media (max-width:640px){{ .barcell{{display:none}} body{{padding:0 15px 60px}} }}
</style>

<header>
  <p class="eyebrow">Holo-Hilbert spectral analysis · two-layer EMD</p>
  <h1>{R.get('label', 'HHSA Report')}</h1>
  <div class="meta">
    <span><b>n</b> {R.get('n')} samples</span>
    <span><b>cadence</b> {R.get('dt_min')} min</span>
    <span><b>span</b> {R.get('span_h', 0):.1f} h</span>
    <span><b>mean</b> {R.get('mean', 0):.3f} {u}</span>
    <span><b>SD</b> {R.get('sd', 0):.3f}</span>
  </div>
</header>

<section><div class="cards">{card_html}</div></section>

<section>
  <h2><span class="n">01</span>What the data can support</h2>
  <p>Effective resolution is settled before any decomposition, because EMD will
  manufacture modes out of quantisation and interpolation just as readily as out
  of physiology. {res_txt} The record was analysed at
  {R.get('dt_min')} min; anything faster is instrument, not signal.</p>
  {_fig(os.path.join(figs, 'series.png'), 'The record, with the dominant slow mode overlaid.')}
</section>

<section>
  <h2><span class="n">02</span>Scale decomposition</h2>
  <div class="tablewrap"><table>
    <thead><tr><th>Mode</th><th>Period (h)</th><th>Var %</th><th></th>
    <th>Mean amp</th><th>AM depth</th><th>&gt; noise null</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
  <p>Variance shares sum to {R.get('var_sum_pct', 0):.1f} % — EMD modes are near-
  but not exactly orthogonal. Reconstruction error is
  {R.get('recon_error', 0):.1e} {u}. The white-noise null is white by
  construction, so a red signal is <em>expected</em> to fall below it at fast
  scales; that alone does not make the fast modes artefacts.</p>
  {_fig(os.path.join(figs, 'imfs.png'), 'Every mode with its instantaneous amplitude envelope.')}
</section>

<section>
  <h2><span class="n">03</span>Layer 2 — the holo-spectrum</h2>
  <p>Each mode's amplitude envelope is itself decomposed, giving the modulation
  frequency ω that rides on each carrier f. Only admissible pairs (ω &lt; f) are
  kept: {100*R.get('holo_rejected_frac', 0):.1f} % of layer-2 energy was rejected
  as inadmissible, which is envelope ripple rather than modulation.</p>
  {_fig(os.path.join(figs, 'holo.png'), 'H(f, ω). The dashed diagonal is the admissibility boundary ω = f.')}
  {_fig(os.path.join(figs, 'spectra.png'), 'Hilbert marginal spectrum and the cycle-averaged profile.')}
</section>

<section>
  <h2><span class="n">04</span>Is any of it more than noise?</h2>
  <div class="tablewrap"><table>
    <thead><tr><th>Test</th><th>Observed</th><th>Null</th><th>p</th>
    <th>Verdict</th></tr></thead>
    <tbody>{trows}</tbody>
  </table></div>
  <div class="callout"><p><strong>How to read these.</strong> AAFT surrogates keep
  the power spectrum, so they already contain any spectral peak — they cannot tell
  you a rhythm exists, only whether the joint carrier–modulation structure exceeds
  a linear process with the same spectrum. The rotation test is the one that
  licenses calling a rhythm entrained: it preserves each cycle's internal dynamics
  and destroys only the alignment to external time. A statistic far <em>below</em>
  its null is a finding too — it means the signal is more regular than chance.</p></div>
</section>

{band_block}

<section>
  <h2><span class="n">06</span>Limits</h2>
  <ul>
    <li>{"<strong>Short record.</strong> Only %d full cycles of the target period. Modulation frequencies slower than the cycle itself have a handful of periods in the window and cannot be resolved — the holo-spectrum's own value proposition needs many more cycles." % n_cyc if short else "Record length supports the modes reported; still check that the slowest mode has enough cycles to be meaningful."}</li>
    <li><strong>Edges.</strong> Statistics exclude the trimmed margin at each end;
    the slowest mode and the residual remain edge-affected regardless.</li>
    <li><strong>EMD is a dyadic filter bank.</strong> Run it on any red-noise
    process of this length and a mode will land near your target period. Existence
    of such a mode is not evidence of a rhythm — the rotation test is.</li>
    <li><strong>No covariates.</strong> Nothing here can attribute a mode to a
    mechanism without externally recorded events to align against.</li>
  </ul>
</section>

<footer>
  Generated by hhsa_pipeline.py · every number in this page comes from
  results.json in the same folder.<br>
  HHSA after Huang et al., Phil. Trans. R. Soc. A 374:20150206 (2016).
  Surrogates after Theiler et al. (1992). Noise null after Wu &amp; Huang (2004).
</footer>
"""


if __name__ == '__main__':
    d = sys.argv[1] if len(sys.argv) > 1 else 'hhsa_out'
    R = json.load(open(os.path.join(d, 'results.json'), encoding='utf-8'))
    open(os.path.join(d, 'dashboard.html'), 'w', encoding='utf-8').write(build(R, d))
    print(f'wrote {d}/dashboard.html')
