---
title: 每日筆記 Life OS
type: lifeos-template
tags:
  - lifeos
---

# 每日筆記模板（Life OS 版）

> 這是給**參考**用的。夜間腳本 `nightly.js` 會自己建檔、自己填日期、自己寫 frontmatter，
> 所以你**不需要**手動套這個模板，也**不需要**裝 Templater。
>
> 附在這裡的原因：讓你看得到今天的筆記長什麼樣、欄位從哪來。

## 腳本產生的結構

```markdown
---
title: 2026-09-29
date: 2026-09-29
type: 每日筆記
tags:
  - 每日筆記
dq_read: 8            ← 由 nightly.js 寫入，欄位名來自 Compass Config
dq_build: 7
dq_body: 6
dq_present: 9
habit_move: true
habit_sleep_before_1: false
lifeos_scored_at: 2026-09-29 23:14
---

# 2026-09-29

---

## 🏥 臨床          ← 只在本機數筆數，寫成 clinical_pending / clinical_load 兩個數字

-

---

## 📝 日記          ← Ctrl+Shift+I 選「日記」追加到這裡（帶時間）

## 🏆 今日小勝      ← 週記會自動收集這一段

## 🙏 感恩

---

## 💡 今日反思        ← 夜間反思追加在這裡

- **23:14 夜間反思**：今天把設定檔的題目改成自己的了

---

## 明日優先事項

1.
2.
3.
```

## 沿用你原本的結構

`## 🏥 臨床` / `## 💡 今日反思` / `## 明日優先事項` 三個標題來自你自己的
`Templates/每日筆記.md`，不是新發明的。日記／小勝／感恩三段來自 Compass 的每日筆記，
由 `capture.js` 追加內容。Life OS 只在 frontmatter 加欄位、在標題底下追加行。

標題文字可以在 [[Compass Config]] 改（`reflection_heading` 等），腳本會跟著變。

## 關於你原本的模板

`Templates/每日筆記.md` 用的是 Templater 語法（`<% tp.date.now() %>`），
而這個 vault 沒裝 Templater —— 所以它一直沒辦法展開。這大概是
`每日筆記/` 從 2026-05-09 之後就空了的原因。

要修有兩條路：裝 Templater，或者就用夜間腳本（它自己會建檔）。**建議後者**，
因為少一個依賴。
