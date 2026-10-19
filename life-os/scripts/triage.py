# -*- coding: utf-8 -*-
"""GTD clarify: work the inbox, one capture at a time, and teach the layer as you go.

    python scripts/triage.py              # work the real inbox
    python scripts/triage.py --demo       # a few sample captures, touches no vault file
    python scripts/triage.py --report     # calibration + agreement so far, then exit

Every answer you give is a label. The decision layer starts cold and escalates everything;
the bands you keep agreeing with eventually earn the right to file without asking. Bands you
keep correcting never do.

Until the Tasks layer opens (Compass Build Order, day 91) this runs in **shadow mode**: it
proposes, asks, and records, but writes nothing to your task lists. That is deliberate — the
layer arrives at the Tasks layer already carrying evidence rather than cold.

The decision layer is the jev-engineering skill itself (lifeos/jev/, provider `local`):
one jev.decide() call per capture, gated by jev.gate().
"""

from __future__ import print_function

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from lifeos import gtd, triage, unlock          # noqa: E402
from lifeos.config import load_config                      # noqa: E402
from lifeos.jev import calibration                         # noqa: E402

VAULT = os.path.join("G:" + os.sep, "我的雲端硬碟", "Second Brain")
CONFIG = os.path.join(VAULT, "Life OS", "Meta", "Compass Config.md")
INBOX = os.path.join(VAULT, "Life OS", "08 Tasks", "任務總表.md")
CALIBRATION = os.path.join(VAULT, "Life OS", "Meta", "calibration.json")
DECISION_LOG = os.path.join(VAULT, "Life OS", "Meta", "decisions.jsonl")

DEMO = [
    "回覆張醫師的 email",
    "重構 Life OS 儀表板，然後接著寫測試",
    "JAMA 那篇糖尿病文獻要讀",
    "有空想學日文",
    "幫我匯款給房東",
]

LABELS = {
    "bucket": "這則屬於哪一類",
    "folder": "應該歸到哪個資料夾",
    "area": "屬於哪個生活領域",
    "actionable": "這則可以行動嗎",
}
OPTIONS = {
    "bucket": list(gtd.BUCKETS),
    "folder": list(gtd.FOLDERS),
    "actionable": ["yes", "no", "unclear"],
}


def ask(question, proposed, options, audited):
    """Present one decision. Enter accepts the proposal; a number overrides it."""
    tag = "  [抽查確認]" if audited else ""
    print("\n  %s？%s" % (LABELS.get(question, question), tag))
    for i, opt in enumerate(options, 1):
        mark = " <- 建議" if opt == proposed else ""
        print("    %d) %-14s%s" % (i, opt, mark))
    while True:
        try:
            raw = input("    Enter 接受建議，或輸入編號 / s 跳過：").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if raw == "":
            return proposed
        if raw.lower() in ("s", "skip"):
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("    ？請輸入 1-%d，或直接按 Enter。" % len(options))


def show_report(cfg):
    cal = calibration.Calibrator.load(CALIBRATION)
    print("\n== 決策層校準狀態 ==")
    any_data = False
    for q in triage.ADJUDICATED:
        n = cal.observations(q)
        if n == 0:
            continue
        any_data = True
        print("\n  %s" % cal.report(q))
        print("    %-10s %-6s %-9s %s" % ("信心帶", "次數", "實際正確率", "狀態"))
        for band, count, acc, warm in cal.reliability(q):
            print("    %-10s %-6d %-9.2f %s" % (band, count, acc, "已暖機" if warm else "資料不足"))
    if not any_data:
        print("  還沒有任何觀測。決策層是冷的，所以每一題都會問你。")
        print("  這是正確的行為，不是故障 —— 它還沒有資格替你決定任何事。")

    summary = triage.summarize_log(DECISION_LOG)
    if summary:
        print("\n== 你同意了多少 ==")
        for q, s in sorted(summary.items()):
            rate = "—" if s["rate"] is None else ("%.0f%%" % (s["rate"] * 100))
            print("  %-12s %s  (%d/%d)" % (q, rate, s["agreed"], s["total"]))
    print("")


def main(argv):
    if not os.path.exists(CONFIG):
        print("找不到設定檔：%s" % CONFIG)
        return 1
    cfg = load_config(CONFIG)

    if "--report" in argv:
        show_report(cfg)
        return 0

    demo = "--demo" in argv
    captures = DEMO if demo else triage.parse_inbox(INBOX)

    day = unlock.day_number(cfg.start_date) if cfg.start_date else 0
    can_file = triage.filing_allowed(cfg)

    print("\n=== GTD 清空收件匣 ===")
    print("第 %d 天。" % day, end=" ")
    if can_file:
        print("歸檔已解鎖。")
    else:
        gate = cfg.unlock_days["tasks"]
        print("**影子模式**：只提議、只學習，不會寫進你的任務清單（第 %d 天解鎖歸檔）。" % gate)
        print("這段期間的每一個回答都算數 —— 目的就是讓決策層在解鎖前先累積證據。")

    if demo:
        print("（--demo：以下是範例句子，不會碰到 vault 裡任何檔案）")
    if not captures:
        print("\n收件匣是空的。沒事可做。")
        return 0

    if not sys.stdin.isatty():
        print("\n需要互動輸入，但 stdin 不是終端機。請直接在終端機執行。")
        return 2

    layer = gtd.layer_for_env({"LIFEOS_CALIBRATION": CALIBRATION})
    print("\n決策層：%s（%s）" % (layer.name + " / jev-engineering", "本機、免 key、零成本、一次呼叫問完全部題目"))
    print("共 %d 則。Enter 接受建議，輸入編號改掉，s 跳過，Ctrl-C 離開。" % len(captures))

    resolved = 0
    corrected = 0
    for idx, text in enumerate(captures, 1):
        pending = triage.propose(text, cfg, layer=layer)
        print("\n" + "-" * 66)
        print("[%d/%d] %s" % (idx, len(captures), text))

        guards = gtd.hard_rules(text)
        if guards:
            print("  ⚠ 觸發硬規則（%s）—— 不論信心多高一律由你決定。"
                  % "、".join(t for t, _ in guards))

        questions = pending.questions_for_human()
        if not questions:
            print("  決策層有足夠把握，全部自動處理。")
            continue

        answers = {}
        for q in questions:
            d = pending.decisions[q]
            opts = OPTIONS.get(q) or (cfg.wheel_ids + ["other"])
            audited = not triage.needs_human(d)
            chosen = ask(q, d.label, opts, audited)
            if chosen is None:
                continue
            answers[q] = chosen
            if chosen != d.label:
                corrected += 1

        if not answers:
            continue

        for res in triage.resolve_all(layer, pending, answers,
                                      log_path=DECISION_LOG, save=True):
            resolved += 1
            flag = "同意" if res.agreed else "更正 -> %s" % res.chosen
            conf = "—" if res.confidence is None else "%.2f" % res.confidence
            print("    ✓ %-11s 建議 %-12s conf=%s  %s"
                  % (res.question, res.proposed, conf, flag))

    print("\n" + "=" * 66)
    print("記錄了 %d 個決策，其中 %d 個你更正了。" % (resolved, corrected))
    if not can_file:
        print("影子模式：沒有任何東西被寫進任務清單。")
    print("校準檔：%s" % CALIBRATION)
    print("決策紀錄：%s" % DECISION_LOG)
    print("\n用 python scripts/triage.py --report 看目前的校準狀態。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
