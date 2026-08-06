---
title: Publish Lab Blog 實戰收尾：HHSA 與 Closed-Loop tACS 互動文章
source:
  type: personal
  authors: [朱國大, Codex]
  url: https://kidney-cognition-lab.vercel.app/blog/hhsa-amplitude-modulation-closed-loop-tacs.html
  published: 2026-08-06
date_ingested: 2026-08-06
status: reviewed
tags: [claude-code, publish-lab-blog, hhsa, closed-loop-tacs, github-pages, interactive-article]
related: ["[[publish-lab-blog-SKILL]]"]
---

# Publish Lab Blog 實戰收尾：HHSA 與 Closed-Loop tACS 互動文章

## 一句話總結

接手前一個工作階段留下的半成品，完成引用校正、第二張 SVG、靜態與 HTTP 驗證、三處網站註冊、Git commit／push、Vercel 正式部署與本機快照；同時把 Windows、瀏覽器、Pages queue 與 Drive 權限等失敗模式回饋到 `publish-lab-blog` skill。

## 發布成果

- 文章：〈藏在腦波底下的第二個節奏：一個被頻譜丟掉的維度，如何同時說明失智、巴金森與難治型憂鬱〉
- Vercel 正式頁：<https://kidney-cognition-lab.vercel.app/blog/hhsa-amplitude-modulation-closed-loop-tacs.html>
- GitHub Pages 預定頁：<https://ckt520728.github.io/kidney-cognition-lab/blog/hhsa-amplitude-modulation-closed-loop-tacs.html>
- 網站 repo：<https://github.com/ckt520728/kidney-cognition-lab>
- 發布 commit：`5712481d38d02cc0401d195608759c2046363ffa`
- 成品快照：`publish-lab-blog/examples/hhsa-amplitude-modulation-closed-loop-tacs.html`
- 詳細踩坑：`publish-lab-blog/PITFALLS.md`

## 成品內容

文章以繁體中文解釋 Holo-Hilbert spectral analysis 如何把載波頻率與調幅頻率拆成兩條軸，串連阿茲海默症、帕金森氏症、難治型憂鬱症與工作記憶研究，再把調幅包絡轉化為 closed-loop tACS 的工程目標。

單一 HTML 內含：

- 2 張 inline SVG：兩層 EMD／HHSA 流程圖、快慢雙迴路控制架構。
- 3 個 responsive canvas：AM 波形、FFT vs HHSA、延遲抖動與相位誤差。
- 6 個 range sliders 與多組 presets。
- `devicePixelRatio` resize、`prefers-reduced-motion`、除零與最小頻率 guard。
- 「作者觀點」與「評估／限制」分離，以及非醫療建議聲明。

## 發布前修正

### 引用

- Human Brain Mapping 的 Hsu 等人文章改用正式卷期年份 2023，而非 online-first 的 2022。
- Tsai 等人 TRD/rTMS 研究補齊全體作者、`25(3):100593` 與 DOI。
- Liang 等人工作記憶研究補上 DOI `10.1016/j.neuroscience.2021.02.013`。
- 已發表文獻 1–6、9 的期刊、卷期與 DOI 逐筆核對；兩篇未正式出版項目維持預印本標示。

### 圖像規格

原稿只有 1 張 SVG，未達 skill 的「a couple of colorful SVG diagrams」。新增快／慢迴路圖後，機械式計數為 2 SVG、3 canvas、6 sliders。

## 驗證紀錄

| 檢查 | 結果 |
| --- | --- |
| Inline JavaScript 編譯 | 通過，1 個 script block |
| 主要 HTML 標籤配對 | `svg 2/2`、`canvas 3/3`、`script 1/1`、`div 48/48`、`figure 2/2` |
| `git diff --check` | 通過 |
| 本機 HTTP | 200 |
| Vercel 文章 | 200，55,345 bytes，標題存在 |
| Vercel 首頁卡片 | 200，slug count = 1 |
| GitHub repo source | blob 存在，55,345 bytes |
| GitHub Pages | build 綁定正確 commit；當時受 GitHub minor service outage 影響仍為 `building` |
| 本機快照 | SHA-256 與 repo source 相符 |
| Google Drive snapshot | 失敗：API 403，資料夾可讀但 connector 無寫入權限 |

## 本次最值得保留的 pitfalls

1. **先找 partial checkout，再考慮重 clone。** 用 slug 或獨特數值搜尋暫存目錄，可避免丟掉未提交成果。
2. **PowerShell 顯示亂碼不等於檔案損壞。** 明確使用 `-Encoding UTF8`。
3. **HTML 不能直接丟給 `node --check`。** 應抽出 inline script 編譯。
4. **Pipeline 最後成功可能掩蓋前段失敗。** 驗證步驟應逐段檢查 exit code。
5. **規格要機械式計數。** 內容看起來圖很多，不代表 SVG 數量達標。
6. **公開書目必須查正式來源。** online-first 年份與正式卷期年份可能不同。
7. **沒有 browser binding 就沒有視覺測試。** 可做程式化驗證，但交付文字必須說清楚。
8. **不要用 `$home` 當 URL 變數。** PowerShell 變數不分大小寫，會撞到唯讀 `$HOME`。
9. **push、Vercel、Pages 是三個不同狀態。** 每一層都要獨立驗證。
10. **Drive 可讀不代表可寫。** 403 時保留本機副本，不要改傳 root 掩飾失敗。
11. **`git diff --stat` 不含 untracked files。** 必須和 `git status --short` 一起看。
12. **提升權限啟動的 process 要同權限清理。** 清理後再查 PID，不相信未受控的成功訊息。

## 對 skill 的回饋

本次已更新 `publish-lab-blog/SKILL.md`：

- 發布前要求閱讀 `PITFALLS.md`。
- Vercel 與 GitHub Pages 分別驗證，Pages 延遲時核對 build commit 與 GitHub Status。
- Drive 403 不得改傳 root，必須保留本機驗證副本。
- Windows 強制 UTF-8、避免 `$HOME`、正確檢查 HTML inline JS。
- `git status` 與 asset counts 成為 commit 前必要檢查。
- 無瀏覽器連線時不可聲稱視覺互動驗證通過。

## Source of truth

網站內容的 source of truth 是 `ckt520728/kidney-cognition-lab`。`claude-skills` 與 Obsidian 中的 HTML 都是帶日期的教學／稽核快照，不會自動跟網站後續修改同步。
