# -*- coding: utf-8 -*-
"""
共用統計與資料選取（cognitive_task_pilot_skill；與網站 web/js/app/pilot-analysis.js 同一規則）。

- select_sessions：只收完成場次、指定資料來源（實測／模擬）、同一 cohort，且每位受試者只取最新一場。
- test_hypothesis：依 design（one_sample / between / proportion）計算；N < 2 或零變異一律不可估計（NaN），
  絕不回報 p = 0 或 t = ±inf。
- holm：只對可估計的檢定做 Holm-Bonferroni。
"""
import itertools, json, math
import numpy as np
from scipy import stats

EPS = 1e-9
NAN = math.nan


def is_simulation(s):
    sid, pid = str(s.get('session_id') or ''), str(s.get('participant_id') or '')
    return s.get('data_source') == 'simulation' or sid.lower().startswith('pilot-') or pid.upper().startswith('PILOT_SUBJ_')


def cohort_key(s):
    cfg = {k: v for k, v in (s.get('config') or {}).items() if k not in ('seed', 'participant_id', 'group')}
    return json.dumps([s.get('study_id') or '', s.get('task_version') or '', s.get('platform') or '', s.get('fidelity') or '', cfg], sort_keys=True)


def select_sessions(sessions, task_id, simulation=False, cohort='largest'):
    """回傳 (included, excluded_counts, cohort_key)。cohort='largest' 取人數最多的 cohort；None 不篩。"""
    ex = {'incomplete': 0, 'source': 0, 'cohort': 0, 'missing_id': 0, 'duplicate': 0}
    pool = []
    for s in sessions:
        if s.get('task_id') != task_id:
            continue
        if s.get('completion') != 'complete':
            ex['incomplete'] += 1; continue
        if is_simulation(s) != simulation:
            ex['source'] += 1; continue
        if not s.get('participant_id'):
            ex['missing_id'] += 1; continue
        pool.append(s)
    key = cohort
    if cohort == 'largest':
        counts = {}
        for s in pool:
            counts.setdefault(cohort_key(s), set()).add(s['participant_id'])
        key = max(counts, key=lambda k: len(counts[k])) if counts else None
    latest = {}
    for s in pool:
        if key is not None and cohort_key(s) != key:
            ex['cohort'] += 1; continue
        prev = latest.get(s['participant_id'])
        if prev is not None:
            ex['duplicate'] += 1
        if prev is None or str(s.get('started_at', '')) > str(prev.get('started_at', '')):
            latest[s['participant_id']] = s
    return [latest[k] for k in sorted(latest)], ex, key


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def signflip_p(x):
    n = len(x)
    if n < 2 or n > 16 or np.allclose(x, 0):
        return NAN
    signs = np.array(list(itertools.product([-1, 1], repeat=n)))
    return float(np.mean(np.abs((signs * x).mean(axis=1)) >= abs(x.mean()) - 1e-12))


def label_permutation_p(a, b):
    pooled = np.concatenate([a, b]); n, k = len(pooled), len(a)
    if n > 20:
        return NAN
    obs = abs(a.mean() - b.mean())
    diffs = [abs(pooled[list(c)].mean() - np.delete(pooled, list(c)).mean()) for c in itertools.combinations(range(n), k)]
    return float(np.mean(np.array(diffs) >= obs - 1e-12))


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (NAN, NAN)
    p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def test_hypothesis(included, hyp, metric=None):
    """included：select_sessions 的結果；hyp：registry 項目。回傳 dict（estimate 為主要估計值）。"""
    design = hyp.get('design') or 'one_sample'
    key = metric or hyp.get('dvKey')
    if metric and metric != hyp.get('dvKey'):
        design = 'one_sample'
    out = dict(metric=key, design=design, n=0, estimate=NAN, sd=NAN, sem=NAN, ci95_low=NAN, ci95_high=NAN, t=NAN, df=NAN,
               p=NAN, effect_size=NAN, effect_size_type='', p_permutation=NAN, estimable=False, note='')
    vals = [(s, s.get('summary', {}).get(key)) for s in included]
    vals = [(s, float(v)) for s, v in vals if _num(v)]
    if design == 'between':
        gk, (ga, gb) = hyp.get('groupKey', 'group'), hyp['groups']
        a = np.array([v for s, v in vals if s['summary'].get(gk) == ga]); b = np.array([v for s, v in vals if s['summary'].get(gk) == gb])
        out.update(n=len(a) + len(b), note=f'{ga} n={len(a)}, {gb} n={len(b)}；估計值為 {ga} − {gb}')
        if len(a) and len(b):
            out['estimate'] = float(a.mean() - b.mean())
        va = a.var(ddof=1) if len(a) > 1 else NAN; vb = b.var(ddof=1) if len(b) > 1 else NAN
        if len(a) >= 2 and len(b) >= 2 and va + vb > EPS:
            w = stats.ttest_ind(a, b, equal_var=False)
            se = math.sqrt(va / len(a) + vb / len(b))
            dfw = (va / len(a) + vb / len(b)) ** 2 / ((va / len(a)) ** 2 / (len(a) - 1) + (vb / len(b)) ** 2 / (len(b) - 1))
            tc = stats.t.ppf(0.975, dfw)
            pooled = math.sqrt(((len(a) - 1) * va + (len(b) - 1) * vb) / (len(a) + len(b) - 2))
            out.update(t=float(w.statistic), df=float(dfw), p=float(w.pvalue), sem=se, ci95_low=out['estimate'] - tc * se,
                       ci95_high=out['estimate'] + tc * se, effect_size=out['estimate'] / pooled if pooled > EPS else NAN,
                       effect_size_type="Cohen's d", p_permutation=label_permutation_p(a, b), estimable=True)
        else:
            out['note'] += '；組別 N < 2 或零變異，不可估計'
        return out
    x = np.array([v for _, v in vals])
    if design == 'proportion':
        k, n = int((x == 1).sum()), int(np.isin(x, [0, 1]).sum())
        lo, hi = wilson(k, n)
        out.update(n=n, estimate=k / n if n else NAN, ci95_low=lo, ci95_high=hi, note=f'比例 {k}/{n}，Wilson 95% CI；描述性')
        return out
    n = len(x)
    out['n'] = n
    if n:
        out['estimate'] = float(x.mean())
    if n >= 2:
        sd = float(x.std(ddof=1)); out['sd'] = sd
        if sd > EPS * max(1.0, abs(out['estimate'])):
            se = sd / math.sqrt(n); ci = stats.t.interval(0.95, n - 1, loc=out['estimate'], scale=se); tt = stats.ttest_1samp(x, 0)
            out.update(sem=se, ci95_low=float(ci[0]), ci95_high=float(ci[1]), t=float(tt.statistic), df=n - 1, p=float(tt.pvalue),
                       effect_size=out['estimate'] / sd, effect_size_type="Cohen's dz", p_permutation=signflip_p(x), estimable=True)
            return out
        out['note'] = '受試者間零變異：不可估計'
    else:
        out['note'] = 'N < 2：只能描述，不能推論'
    return out


def holm(pvals, estimable):
    """回傳與輸入等長的 Holm 校正 p（不可估計者為 NaN）與家族大小。"""
    p = np.asarray(pvals, float); e = np.asarray(estimable, bool)
    out = np.full(len(p), NAN); idx = np.where(e)[0]; m = len(idx)
    running = 0.0
    for rank, i in enumerate(idx[np.argsort(p[idx])]):
        running = max(running, min(1.0, (m - rank) * p[i])); out[i] = running
    return out, m
