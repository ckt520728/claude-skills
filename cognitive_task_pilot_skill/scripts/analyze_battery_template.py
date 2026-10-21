# -*- coding: utf-8 -*-
"""
Reusable Cognitive Battery Statistical Analysis Engine (Python / SciPy / Matplotlib)
Part of cognitive_task_pilot_skill
朱國大醫師 (Kwo-Ta Chu, MD, PhD) 認知神經科學實驗室規範

規則見 pilot_stats.py：每人一場、同 cohort；N < 2／零變異不可估計；不自動改用其他指標；
組間（between）與比例（proportion）設計各自處理；Holm 只校正可估計的檢定。
"""
from pathlib import Path
import json, math, argparse, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pilot_stats import select_sessions, test_hypothesis, holm  # noqa: E402


def load_registry(path):
    p = Path(path) if path else Path(__file__).resolve().parent.parent / 'references' / 'hypotheses_registry.json'
    return json.loads(p.read_text(encoding='utf-8'))


def run_analysis(out_dir_str, registry_path_str=None, simulation=True):
    out_dir = Path(out_dir_str)
    fig_dir = out_dir / 'figures'
    fig_dir.mkdir(parents=True, exist_ok=True)
    sessions = json.loads((out_dir / 'sessions.json').read_text(encoding='utf-8'))
    registry = load_registry(registry_path_str)
    tasks = sorted({s['task_id'] for s in sessions})
    print(f"Loaded {len(sessions)} sessions, {len(tasks)} tasks.")

    rows = []
    for tid in tasks:
        included, ex, _ = select_sessions(sessions, tid, simulation=simulation)
        pd.DataFrame([{'participant_id': s['participant_id'], **{k: v for k, v in s.get('summary', {}).items()
                       if isinstance(v, (int, float, bool, str)) or v is None}} for s in included]) \
            .to_csv(out_dir / f'{tid}_participant_summary.csv', index=False, encoding='utf-8-sig')
        hyp = registry.get(tid)
        if not hyp or not hyp.get('dvKey'):
            rows.append({'task_id': tid, 'metric': None, 'estimable': False, 'note': '登錄表無此作業：不自動選指標'})
            continue
        if not any(hyp['dvKey'] in s.get('summary', {}) for s in included):
            rows.append({'task_id': tid, 'metric': hyp['dvKey'], 'estimable': False, 'note': f"summary 沒有 {hyp['dvKey']}：不自動改用其他欄位"})
            continue
        r = test_hypothesis(included, hyp)
        r.update(task_id=tid, label=hyp.get('name', {}).get('zh-TW', tid), unit=hyp.get('unit', ''),
                 expected_direction=-1 if hyp.get('expectedDirection') == 'less_than_zero' else 1,
                 excluded=json.dumps(ex, ensure_ascii=False))
        rows.append(r)

    res = pd.DataFrame(rows)
    for col in ['p', 'estimate', 'expected_direction', 'effect_size']:
        if col not in res:
            res[col] = math.nan
    res['p_holm'], m = holm(res['p'].fillna(math.nan), res['estimable'].fillna(False))
    res['holm_family_size'] = m
    res['model_direction_supported'] = res['estimable'].fillna(False) & (res['estimate'] * res['expected_direction'] > 0) & (res['p_holm'] < 0.05)
    res.to_csv(out_dir / 'inferential_metrics.csv', index=False, encoding='utf-8-sig')

    # 描述統計
    desc = []
    for tid in tasks:
        included, _, _ = select_sessions(sessions, tid, simulation=simulation)
        df = pd.DataFrame([s.get('summary', {}) for s in included])
        for col in df.columns:
            arr = pd.to_numeric(df[col], errors='coerce').dropna().to_numpy(float)
            if df[col].dtype == bool or not len(arr):
                continue
            sd = float(arr.std(ddof=1)) if len(arr) > 1 else math.nan
            desc.append({'task_id': tid, 'condition_metric': col, 'n': len(arr), 'mean': float(arr.mean()),
                         'median': float(np.median(arr)), 'sd': sd, 'sem': sd / math.sqrt(len(arr)) if len(arr) > 1 else math.nan})
    pd.DataFrame(desc).to_csv(out_dir / 'descriptive_statistics.csv', index=False, encoding='utf-8-sig')

    # 效應量圖（不可估計者標示，不畫成 ±15）
    names = {f.name for f in font_manager.fontManager.ttflist}
    plt.rcParams['font.family'] = next((f for f in ['Microsoft JhengHei', 'Noto Sans CJK TC', 'Arial Unicode MS'] if f in names), 'DejaVu Sans')
    plt.rcParams.update({'font.size': 10, 'axes.unicode_minus': False})
    fig, ax = plt.subplots(figsize=(14, max(8, len(res) * 0.35)))
    y = np.arange(len(res)); es = res['effect_size'].to_numpy(float)
    ax.barh(y, np.where(np.isfinite(es), np.clip(es, -15, 15), 0), color=['#1f77b4' if t.startswith('M') else '#2ca02c' for t in res['task_id']],
            alpha=0.75, height=0.65, edgecolor='black', linewidth=0.8)
    for yi, v in zip(y, es):
        if not np.isfinite(v):
            ax.text(0.1, yi, '不可估計／描述性', va='center', fontsize=8, color='#b91c1c')
    ax.axvline(0, color='gray', linestyle='--', linewidth=1)
    ax.set_yticks(y); ax.set_yticklabels([f"{t}: {str(m_)[:28]}" for t, m_ in zip(res['task_id'], res['metric'])], fontsize=9)
    ax.invert_yaxis(); ax.set_xlabel('效應量（dz 或組間 d）', fontsize=11, fontweight='bold')
    ax.set_title('認知測驗電池效應量（模擬效應為反應器設定值）', fontsize=13, fontweight='bold')
    fig.tight_layout(); fig.savefig(fig_dir / 'fig_battery_forest.png', dpi=200); plt.close(fig)
    print(f"Done: {int(res['model_direction_supported'].sum())} supported / {m} estimable / {len(res)} tasks -> {out_dir}")
    return res


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cognitive Battery Statistical Analysis')
    parser.add_argument('--out', default='output/battery-pilot-10', help='Output directory (contains sessions.json)')
    parser.add_argument('--registry', default=None, help='Hypotheses registry path')
    parser.add_argument('--empirical', action='store_true', help='Analyse observed (non-simulation) sessions instead')
    args = parser.parse_args()
    run_analysis(args.out, args.registry, simulation=not args.empirical)
