# -*- coding: utf-8 -*-
"""The [C] numbers every coaching prompt needs, computed in code (invariant 5).

    python scripts/lifeos_status.py            # today
    python scripts/lifeos_status.py 2026-10-15 # as of a date

Prompts call this instead of asking the model to average scores or count days. Clinical
content is never read: only the clinical_pending / clinical_load scalars nightly.js wrote.
"""
from __future__ import print_function

import datetime
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lifeos import metrics, unlock               # noqa: E402
from lifeos.config import load_config            # noqa: E402

VAULT = os.environ.get("LIFEOS_VAULT", os.path.join("G:" + os.sep, "我的雲端硬碟", "Second Brain"))
CONFIG = os.path.join(VAULT, "Life OS", "Meta", "Compass Config.md")


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    today = datetime.datetime.strptime(argv[0], "%Y-%m-%d").date() if argv else datetime.date.today()
    cfg = load_config(CONFIG)
    folder = os.path.join(VAULT, cfg.daily_note_folder)

    rows30 = metrics.collect(folder, 30, today)
    scored = [d for d, fm in rows30 if any(k.startswith("dq_") and isinstance(v, (int, float))
                                           and not isinstance(v, bool) for k, v in fm.items())]
    frac, n, denom = unlock.journal_consistency(scored, cfg.start_date, today)

    print("日期 %s · 第 %d 天 · 近 %d 天評分 %d 天（%.0f%%）"
          % (today, unlock.day_number(cfg.start_date, today), denom, n, frac * 100))
    print("\n層級：")
    for layer, ok, day, iso, remaining, why in unlock.status_table(cfg, today, frac):
        state = "開放" if ok else ("還有 %d 天" % remaining if why == "days" else "一致性未達 80%")
        print("  %-14s 第 %3d 天（%s）  %s" % (unlock.LAYER_LABELS[layer], day, iso, state))

    rows7 = metrics.collect(folder, 7, today)
    todays = dict(rows7[0][1]) if rows7 and rows7[0][0] == today else {}
    print("\n每日提問（今天 / 7 日平均，分母一起看）：")
    for q in cfg.dq_questions:
        m = metrics.mean_of(rows7, q["id"], 7)
        mean = "—" if m.value is None else "%.1f（n=%d/7）" % (m.value, m.n)
        print("  %-10s 今天 %-3s 平均 %s  %s" % (q["id"], todays.get(q["id"], "—"), mean, q["prompt"]))
    print("\n習慣（近 7 天做到 / 有紀錄）：")
    for h in cfg.habits:
        vals = [fm.get(h["id"]) for _d, fm in rows7 if isinstance(fm.get(h["id"]), bool)]
        print("  %-22s %d/%d  %s" % (h["id"], sum(1 for v in vals if v), len(vals), h["name"]))
    clin = [(d, fm.get("clinical_pending"), fm.get("clinical_load")) for d, fm in rows7
            if isinstance(fm.get("clinical_pending"), int)]
    if clin:
        print("\n臨床負荷（只有數字）：")
        for d, p, l in clin:
            print("  %s  待處理 %s 例  負荷 %s/5" % (d, p, l))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
