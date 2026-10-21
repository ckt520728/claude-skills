# -*- coding: utf-8 -*-
"""
Empirical vs Simulation Comparative Diagnostic Engine (Python / SciPy / Matplotlib)
Part of cognitive_task_pilot_skill
朱國大醫師 (Kwo-Ta Chu, MD, PhD) 認知神經科學實驗室規範

新受試者資料進來時：計算描述／推論統計、與模擬基準對照，並執行品質檢查。
規則（與網站 pilot-analysis.diagnose 相同）：
- 實測只收完成、非模擬、同一 cohort 的場次，每位受試者取最新一場；基準只收模擬場次。
- N < 2 或零變異：不可估計（不回報 p = 0）。登錄表 DV 缺失時不自動換指標。
- 「效應反向」只在 N ≥ 2、p < .05 且方向相反時提出；狀態取最嚴重者，不被後續檢查覆寫。
- 模擬效應量是反應器設定值：實測／模擬比率只作附註，不判定「設計缺陷」。
- QC 只用 summary 中實際存在的欄位；未檢查的項目會列出。
"""
from pathlib import Path
import json, math, argparse, sys, html
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pilot_stats import select_sessions, test_hypothesis  # noqa: E402

SEVERITY = {'NORMAL': 0, 'NOT_EVALUABLE': 0, 'NO_PRIMARY_DV': 0, 'DESIGN_CEILING': 1, 'OPERATIONAL_DEVIATION': 2,
            'DESIGN_TIMING_ISSUE': 2, 'DESIGN_TOO_DIFFICULT': 3, 'EFFECT_REVERSED': 4}


def load_sessions(src):
    p = Path(src)
    if p.is_file():
        content = json.loads(p.read_text(encoding='utf-8'))
        if isinstance(content, list):
            return content
        return content.get('sessions', [content]) if isinstance(content, dict) else []
    if p.is_dir():
        out = []
        for f in sorted(p.glob('*.json')):
            if f.name.startswith(('execution', 'profile', 'SHA256')):
                continue
            data = json.loads(f.read_text(encoding='utf-8'))
            out.extend(data if isinstance(data, list) else [data])
        seen, uniq = set(), []
        for s in out:  # sessions.json 與 SIMxx.json 重疊時去重
            if isinstance(s, dict) and s.get('session_id') not in seen:
                seen.add(s.get('session_id')); uniq.append(s)
        return uniq
    raise FileNotFoundError(f'Cannot load sessions from {src}')


def num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def qc(included):
    alerts, checks, state = [], [], {'status': 'NORMAL'}

    def raise_(s):
        if SEVERITY[s] > SEVERITY[state['status']]:
            state['status'] = s

    has = lambda k: any(num(s.get('summary', {}).get(k)) for s in included)
    tot = lambda k: sum(s['summary'][k] for s in included if num(s.get('summary', {}).get(k)))
    if has('n_timeouts'):
        checks.append('超時率')
        denom = sum(s['summary'].get('n_main') or s['summary'].get('n_main_trials') or len(s.get('trials', [])) for s in included)
        rate = tot('n_timeouts') / max(1, denom)
        if rate > 0.05:
            alerts.append(f"【{'嚴重' if rate > 0.15 else '輕度'}漏答】超時率 {rate * 100:.1f}%"); raise_('OPERATIONAL_DEVIATION')
    fk = 'n_dropped_frame_trials' if has('n_dropped_frame_trials') else 'n_exposure_errors' if has('n_exposure_errors') else None
    if fk:
        checks.append('掉格')
        if tot(fk) > 0:
            alerts.append(f'【硬體掉格】{tot(fk):g} 個試次刺激幀數與預定不符'); raise_('DESIGN_TIMING_ISSUE')
    if has('n_visibility_lost'):
        checks.append('切頁')
        if tot('n_visibility_lost') > 0:
            alerts.append(f"【視窗切頁】{tot('n_visibility_lost'):g} 次"); raise_('OPERATIONAL_DEVIATION')
    ak = 'accuracy_overall' if has('accuracy_overall') else 'accuracy' if has('accuracy') else None
    if ak:
        checks.append('正確率天花板／地板')
        acc = float(np.mean([s['summary'][ak] for s in included if num(s['summary'].get(ak))]))
        if acc < 0.55:
            alerts.append(f'【地板效應】平均正確率 {acc * 100:.1f}%'); raise_('DESIGN_TOO_DIFFICULT')
        elif acc > 0.98:
            alerts.append(f'【天花板效應】平均正確率 {acc * 100:.1f}%'); raise_('DESIGN_CEILING')
    return state, alerts, checks, raise_


def run_comparison(empirical_input, baseline_input, out_dir_str, registry_path_str=None):
    out_dir = Path(out_dir_str); fig_dir = out_dir / 'figures'; fig_dir.mkdir(parents=True, exist_ok=True)
    emp_all = load_sessions(empirical_input)
    base_all = load_sessions(baseline_input) if baseline_input else []
    reg_path = Path(registry_path_str) if registry_path_str else Path(__file__).resolve().parent.parent / 'references' / 'hypotheses_registry.json'
    registry = json.loads(reg_path.read_text(encoding='utf-8')) if reg_path.exists() else {}
    emp_tasks = sorted({s.get('task_id') for s in emp_all if s.get('task_id')})
    nan = math.nan

    rows, diag_out, emp_pids = [], [], set()
    for tid in emp_tasks:
        hyp = registry.get(tid, {})
        included, ex, _ = select_sessions(emp_all, tid, simulation=False)
        base_inc, _, _ = select_sessions(base_all, tid, simulation=True, cohort=None)
        emp_pids.update(s['participant_id'] for s in included)
        dv = hyp.get('dvKey')
        state, alerts, checks, raise_ = qc(included)
        notes = []
        if not included:
            state['status'] = 'NOT_EVALUABLE'; notes.append('沒有完成、非模擬的場次')
        empty = dict(metric=dv, design=hyp.get('design') or 'one_sample', n=0, estimate=nan, p=nan, ci95_low=nan, ci95_high=nan,
                     estimable=False, t=nan, effect_size=nan, sd=nan, note='')
        if not dv or not any(dv in s.get('summary', {}) for s in included):
            notes.append(f'summary 沒有假說主要 DV（{dv}）；不自動改用其他欄位')
            e, b = empty, dict(empty)
            if state['status'] == 'NORMAL':
                state['status'] = 'NO_PRIMARY_DV'
        else:
            e = test_hypothesis(included, hyp)
            b = test_hypothesis(base_inc, hyp) if base_inc else dict(empty)
            direction = -1 if hyp.get('expectedDirection') == 'less_than_zero' else 1
            checks.append('效應方向')
            if e['design'] == 'proportion':
                notes.append('比例型假說：描述比例與 Wilson CI，不做方向檢定')
            elif not e['estimable']:
                notes.append(f"無法檢定方向：{e['note']}")
            elif e['estimate'] * direction < 0 and e['p'] < 0.05:
                alerts.append(f"【效應顯著反向】估計 {e['estimate']:.4g}、p = {e['p']:.4f}；請核對條件標籤、按鍵對應與計分")
                raise_('EFFECT_REVERSED')
            if num(b['estimate']) and abs(b['estimate']) > 1e-9 and num(e['estimate']):
                notes.append(f"實測／模擬比率 {e['estimate'] / b['estimate'] * 100:.1f}%（模擬效應為設定值，僅供參考）")
            if e['n'] < 2 and state['status'] == 'NORMAL':
                state['status'] = 'NOT_EVALUABLE'
        welch_t = welch_p = nan
        if e.get('design') == 'one_sample' and dv:
            xe = np.array([s['summary'][dv] for s in included if num(s.get('summary', {}).get(dv))])
            xb = np.array([s['summary'][dv] for s in base_inc if num(s.get('summary', {}).get(dv))])
            if len(xe) >= 2 and len(xb) >= 2 and xe.var(ddof=1) + xb.var(ddof=1) > 1e-12:
                w = stats.ttest_ind(xe, xb, equal_var=False); welch_t, welch_p = float(w.statistic), float(w.pvalue)
        unchecked = [c for c in ['超時率', '掉格', '切頁', '正確率天花板／地板'] if c not in checks]
        if unchecked:
            notes.append('未提供 QC 欄位、未檢查：' + '、'.join(unchecked))
        status = state['status']
        diag_out.append({'task_id': tid, 'metric': dv, 'status': status, 'alerts': alerts, 'notes': notes, 'excluded': ex,
                         'empirical_estimate': e['estimate'], 'baseline_estimate': b['estimate'], 'welch_p': welch_p})
        rows.append({'task_id': tid, 'label': hyp.get('name', {}).get('zh-TW', tid), 'metric': dv, 'unit': hyp.get('unit', ''),
                     'design': e.get('design'), 'n_emp': e['n'], 'estimate_emp': e['estimate'], 'sd_emp': e.get('sd'),
                     'ci95_low_emp': e['ci95_low'], 'ci95_high_emp': e['ci95_high'], 't_emp': e.get('t'), 'p_emp': e['p'],
                     'effect_size_emp': e.get('effect_size'), 'estimable_emp': e['estimable'], 'n_base': b['n'],
                     'estimate_base': b['estimate'], 'sd_base': b.get('sd'), 'welch_t': welch_t, 'welch_p': welch_p,
                     'diagnostic_status': status, 'alert_count': len(alerts),
                     'excluded_duplicate': ex['duplicate'], 'excluded_cohort': ex['cohort'], 'excluded_incomplete': ex['incomplete']})

    comp = pd.DataFrame(rows)
    comp.to_csv(out_dir / 'comparison_metrics.csv', index=False, encoding='utf-8-sig')
    (out_dir / 'diagnostic_alerts.json').write_text(json.dumps(diag_out, indent=2, ensure_ascii=False, default=str), encoding='utf-8')

    names = {f.name for f in font_manager.fontManager.ttflist}
    plt.rcParams['font.family'] = next((f for f in ['Microsoft JhengHei', 'Noto Sans CJK TC', 'Arial Unicode MS'] if f in names), 'DejaVu Sans')
    plt.rcParams.update({'font.size': 10, 'axes.unicode_minus': False})
    fig, ax = plt.subplots(figsize=(15, max(6, len(comp) * 0.45)))
    if len(comp):
        y = np.arange(len(comp)); me = comp['estimate_emp'].to_numpy(float); mb = comp['estimate_base'].to_numpy(float)
        colors = ['#d93025' if s == 'EFFECT_REVERSED' else '#f2994a' if SEVERITY.get(s, 0) >= 1 else '#1a73e8' for s in comp['diagnostic_status']]
        ax.barh(y - 0.15, np.nan_to_num(me), height=0.3, color=colors, alpha=0.85, label='實測估計 ± 95% CI')
        lo, hi = comp['ci95_low_emp'].to_numpy(float), comp['ci95_high_emp'].to_numpy(float)
        ok = np.isfinite(lo) & np.isfinite(hi) & np.isfinite(me)
        ax.errorbar(me[ok], (y - 0.15)[ok], xerr=[me[ok] - lo[ok], hi[ok] - me[ok]], fmt='none', color='black', capsize=4)
        if np.isfinite(mb).any():
            ax.barh(y + 0.15, np.nan_to_num(mb), height=0.3, color='#5f6368', alpha=0.45, label='模擬基準（設定值）')
        ax.set_yticks(y); ax.set_yticklabels([f"{r.task_id}: {str(r.metric)[:24]} [{r.unit}]" for r in comp.itertuples()], fontsize=9)
        ax.invert_yaxis(); ax.legend(loc='lower right')
    ax.axvline(0, color='gray', linestyle='--', linewidth=1)
    ax.set_xlabel('估計值（原單位）')
    ax.set_title(f'實測（N={len(emp_pids)} 人）vs 模擬基準', fontsize=13, fontweight='bold')
    fig.tight_layout(); fig.savefig(fig_dir / 'fig_empirical_vs_simulation.png', dpi=200); plt.close(fig)

    def block(a):
        items = ''.join(f'<li>{html.escape(m)}</li>' for m in a['alerts'])
        notes = ''.join(f'<li class="muted">{html.escape(m)}</li>' for m in a['notes'])
        return f"<div class='card'><strong>[{html.escape(a['task_id'])}] {html.escape(str(a['metric']))}</strong>：{html.escape(a['status'])}<ul>{items}{notes}</ul></div>"

    any_alert = any(a['alerts'] for a in diag_out)
    head = '' if any_alert else '<p>未觸發任何已實作的檢查。這不代表結果符合理論；請看各作業的附註（未檢查項目、N、可估計性）。</p>'
    table = comp.to_html(index=False, float_format=lambda x: f'{x:.3g}', border=0, na_rep='—')
    (out_dir / 'comparative_report.html').write_text(f"""<!doctype html>
<html lang="zh-TW"><head><meta charset="utf-8"><title>實測與模擬基準對照報告</title>
<style>body{{font-family:-apple-system,"Segoe UI","Microsoft JhengHei",sans-serif;max-width:1400px;margin:30px auto;padding:25px;line-height:1.7;color:#202124;background:#fafafa}}
.card{{background:#fff;border-radius:8px;padding:14px 18px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.12)}}.muted{{color:#5f6368}}
table{{width:100%;border-collapse:collapse;font-size:12px}}th,td{{padding:6px 8px;border-bottom:1px solid #e0e0e0;text-align:right}}img{{max-width:100%}}</style></head>
<body><h1>實測資料與模擬基準對照報告</h1>
<div class="card"><strong>研究主持人：</strong>朱國大醫師 (Kwo-Ta Chu, MD, PhD)<br>
實測受試者 {len(emp_pids)} 位（每人每作業取最新一場有效完成資料）；作業 {len(emp_tasks)} 項。<br>
模擬基準的效應量是反應器設定值，只作流程對照，不是實徵常模。</div>
<h2>1. 品質與方向檢查</h2>{head}{''.join(block(a) for a in diag_out)}
<h2>2. 對照圖</h2><img src="figures/fig_empirical_vs_simulation.png" alt="對照圖">
<h2>3. 統計表</h2>{table}</body></html>""", encoding='utf-8')

    md = '\n'.join(f"- **[{a['task_id']}] {a['metric']}**（{a['status']}）：" + '；'.join(a['alerts'] + a['notes']) for a in diag_out)
    (out_dir / 'comparative_report.md').write_text(f"# 實測與模擬基準對照\n\n實測受試者 {len(emp_pids)} 位。模擬效應為設定值，僅供流程對照。\n\n{md}\n", encoding='utf-8')
    print(f'Comparative report generated in {out_dir}')
    return comp


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Empirical vs Simulation Pilot Comparison')
    parser.add_argument('--empirical', required=True, help='Path to empirical sessions.json or directory')
    parser.add_argument('--baseline', default='output/battery-pilot-10/sessions.json', help='Path to baseline simulation sessions.json')
    parser.add_argument('--out', default='output/empirical-comparison', help='Output directory')
    parser.add_argument('--registry', default=None, help='Hypotheses registry path')
    args = parser.parse_args()
    run_comparison(args.empirical, args.baseline, args.out, args.registry)
