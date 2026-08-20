"""
make_demo_data.py -- synthetic CGM-like series so the pipeline is runnable
without touching patient data.

Deliberately built to contain a KNOWN answer, so the pipeline's output can be
checked rather than admired:

    circadian carrier   24 h, amplitude 2.6, trough near 04:00
    meal-scale carrier   ~4 h bursts, only during waking hours
                         -> a 4 h carrier amplitude-modulated at 24 h,
                            which is exactly what layer 2 should recover
    multi-day drift      ~3 d
    measurement          rounded to a 0.1 mmol/L lattice, mild smoothing
                         -> the resolution audit should FIND that lattice

    python make_demo_data.py --days 13 --out demo_cgm.csv
"""
import argparse
import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=13)
    ap.add_argument('--step-min', type=float, default=5.0)
    ap.add_argument('--seed', type=int, default=11)
    ap.add_argument('--out', default='demo_cgm.csv')
    a = ap.parse_args()

    rng = np.random.default_rng(a.seed)
    n = int(a.days * 24 * 60 / a.step_min)
    t = np.arange(n) * a.step_min / 60.0          # hours
    tod = t % 24

    # slow components
    circadian = 2.6 * np.cos(2 * np.pi * (t - 16.0) / 24.0)   # peak ~16:00
    drift = 0.8 * np.sin(2 * np.pi * t / 72.0)
    baseline = 7.9 + circadian + drift

    # meal-scale carrier, gated to waking hours -> genuine 24 h AM of a 4 h carrier
    gate = 0.5 * (1 + np.tanh((np.sin(2 * np.pi * (tod - 6) / 24) + 0.15) * 4))
    meals = 1.5 * gate * np.cos(2 * np.pi * t / 4.0)

    # correlated measurement noise (sensor is smoothed, not white)
    w = rng.normal(0, 0.28, n)
    k = np.exp(-np.arange(12) / 4.0)
    k /= k.sum()
    noise = np.convolve(w, k, mode='same')

    x = baseline + meals + noise
    x = np.clip(x, 2.0, 22.0)
    x = np.round(x * 10) / 10                       # 0.1 mmol/L storage lattice

    ts = pd.date_range('2020-01-01 00:00:00', periods=n,
                       freq=f'{int(a.step_min)}min')
    pd.DataFrame({'timestamp': ts, 'glucose': x}).to_csv(a.out, index=False)

    print(f'wrote {a.out}: n={n}, {a.days} days at {a.step_min:g} min')
    print(f'  mean {x.mean():.2f}  SD {x.std(ddof=1):.2f}  '
          f'range {x.min():.1f}-{x.max():.1f}')
    print('  ground truth planted in this file:')
    print('    24 h carrier, amplitude 2.6, peak ~16:00 (trough ~04:00)')
    print('    4 h carrier amplitude-modulated at 24 h (waking-hours gate)')
    print('    72 h drift, amplitude 0.8')
    print('    0.1 mmol/L quantisation lattice + smoothed (non-white) noise')
    print('  a correct pipeline run should recover all four.')


if __name__ == '__main__':
    main()
