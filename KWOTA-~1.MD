---
name: kwota-daily-stack
description: Kwo-Ta 個人化每日工作 stack——整合 Gmail triage、Google Calendar、Google Scholar alerts、AI 主流科技媒體新聞搜尋、NotebookLM 筆記摘要,產出一份單檔 HTML dashboard 並寫入 Google Drive 上的 Obsidian 第二大腦 `/一個知識庫/kwota-daily-stack/`。**強制依賴 NotebookLM MCP 與 Google Drive MCP**:任一缺失就 halt 不執行。觸發詞:「跑我的每日 stack」「kwota daily stack」「daily-stack」「我的每日工作 briefing」「produce my daily command center」「整合 email + 行事曆 + Scholar + AI 新聞 + NotebookLM」。整合 email-assistant 的 triage 邏輯、article-writer 的研究摘要展開邏輯、dashboard-builder 的零虛擬資料原則。不適用:單純回信(直接用 email-assistant)、單純寫文章(用 article-writer)、無 NotebookLM 或 Drive 環境(此時 skill 會主動 halt)。
---

# Kwo-Ta Daily Stack

一個整合的每日工作 stack,專為 Kwo-Ta(kwotachu@gmail.com)設計。從 Gmail、Google Calendar、Google Scholar alerts、主流 AI 科技媒體、NotebookLM 五個來源拉資料,產出一份**單檔 HTML dashboard**。

## 🚨 鐵則 1:NotebookLM MCP + Google Drive MCP 是硬性 Prerequisite

**這個 skill 預設要連到兩個 MCP**:
- **NotebookLM MCP**(處理 NotebookLM 區塊)
- **Google Drive MCP**(把 dashboard 寫到第二大腦 `/一個知識庫/kwota-daily-stack/`)

執行前必須兩個都驗證可用,否則 halt。

### Prerequisite Check(每次執行的第一步)

1. 列出當前 session 可用的所有 MCP tools。
2. 檢查兩個必要 MCP:
   - **NotebookLM**:搜尋名稱含 `notebooklm` 或 `notebook-lm`(case-insensitive)的 tool
   - **Google Drive**:搜尋含 `drive` 字串、且具備 `create_file` / `search_files` 之類 file ops 能力的 MCP tool
3. 三種結果:
   - ✅ **兩個都找到** → 繼續往下執行完整 stack
   - ❌ **NotebookLM 沒找到** → **立即 halt**,訊息:

     ```
     ⚠️ kwota-daily-stack halted

     原因:此 skill 預設需要 NotebookLM MCP 連線,當前環境沒有偵測到任何
     NotebookLM 相關的 MCP tool。

     解法:
     1. 在這台電腦安裝 NotebookLM MCP server,然後重啟 Cowork
     2. 或改用其他不依賴 NotebookLM 的 briefing 流程
        (例如直接呼叫 dashboard-builder 或 email-assistant)

     本 skill 不提供 "skip NotebookLM" 的降級模式,這是設計選擇——
     確保此 stack 的輸出在跨電腦時是一致的。
     ```

   - ❌ **Google Drive 沒找到** → **立即 halt**,訊息:

     ```
     ⚠️ kwota-daily-stack halted

     原因:此 skill 預設要把每日 dashboard 寫到 Google Drive 的
     /一個知識庫/kwota-daily-stack/ 資料夾(使用者的 Obsidian 第二大腦),
     當前環境沒有偵測到 Google Drive MCP。

     解法:在這台電腦連接 Google Drive MCP 後重試。
     ```

   **不要**自作主張改 fallback 模式跑「寫本地檔案」或「跳過 NotebookLM」。使用者明確要求兩個都是硬性 prerequisite。

## 🚨 鐵則 2:零虛擬資料(繼承自 dashboard-builder)

Dashboard 上**每一個**數字、標題、清單,都必須來自實際 MCP 呼叫或網頁搜尋結果。**絕對不准**:

- 為了「先看一下長怎樣」就放假資料
- 隨機數值裝飾面板
- 來源連不上就用上次快取或估計值假裝有資料

來源連不上時,該面板顯示 `⚠️ <來源> 連線失敗 @ <時間>,該面板已略過`,而不是塞假資料。

## 🚨 鐵則 3:Email 永遠只存草稿,不送(繼承自 email-assistant)

如果在過程中需要起草任何回信(例如某封信明顯急、使用者要求順便草擬),**只能** `create_draft`,**絕不** call 任何 send API。

---

## 執行流程

### Step 0:Prerequisite Check
如上述。NotebookLM MCP 與 Google Drive MCP 任一缺失就 halt。

### Step 1:確認當天日期 + 時區
```bash
date +"%Y-%m-%d %A %Z"
```
記下 `YYYY-MM-DD`,後續輸出檔名要用。

### Step 2:平行抓五個來源(可同時呼叫多個 tool)

#### Source A:Google Calendar 今日行程
- 用 `mcp__*__list_events`(Google Calendar MCP),範圍今天 00:00 → 23:59 user 本地時區。
- 抽出:時間、標題、地點、與會者、會議連結。
- 識別**空檔**:兩個事件之間 ≥ 60 分鐘的時段、以及一天頭尾的空白。

#### Source B:Gmail Triage(過去 24h)
- `search_threads` query: `is:unread newer_than:1d -from:scholaralerts-noreply@google.com`
- 取最多 30 封,套 email-assistant 的四象限分類:
  - 🔴 立即回(緊急 + 重要)
  - 🟡 今日內(重要不緊急)
  - 🟢 快速 ack(緊急不重要)
  - ⚪ 可批次 / 可略
- **不要主動草擬**,只列分類。除非使用者另外指示。

#### Source C:Google Scholar Alerts
- `search_threads` query: `from:scholaralerts-noreply@google.com newer_than:2d`
- 對每封 alert `get_thread` 抽出:
  - 訂閱主題 keyword
  - 文章標題、作者、發表年份、期刊
- 從中挑 3–5 篇最相關,**標註選擇理由**(切勿瞎選)。

#### Source D:AI 主流科技媒體新聞搜尋
**只搜以下四家**(這是使用者明確選的):
- TechCrunch(`site:techcrunch.com`)
- The Verge(`site:theverge.com`)
- Ars Technica(`site:arstechnica.com`)
- MIT Technology Review(`site:technologyreview.com`)

執行方式:
1. 用 WebSearch 對每家做 query:`AI` + 過去 24 小時的時間限制(query 加上 `after:YYYY-MM-DD`,用昨天日期)。
2. 從每家挑 1–2 條最相關的 AI 新聞(避開 listicle 跟 advertorial)。
3. 對每條新聞,用 WebFetch 抓原文,**只摘 2–3 句**(不要全文搬)。

**降級規則**:如果 WebSearch / WebFetch 失敗(網路、quota、被 block),該家標 `⚠️ <媒體> 連線失敗 @ <時間>`,**不**捏造新聞。

#### Source E:NotebookLM 最近 3 個 Notebook(只在 prereq check 通過時)
- 用 NotebookLM MCP 列出 notebooks,按最近使用時間排序,取前 3 個。
- 對每個 notebook 用 NotebookLM MCP 拉:
  - 標題、主題
  - 最近新增的 sources 數量
  - 最後互動時間
- 為每個 notebook 產出:
  - **一段話摘要**(該 notebook 的研究主題與目前累積方向)
  - **2–3 個建議的後續研究題目**(具體、可執行,而非空泛的「探索 X 更多面向」)

如果某個 notebook 的內容極少(< 3 個 source),那條建議標註 `⚠️ 資料量不足,建議先補 sources`。

### Step 3:依空檔安排今日讀書 / 工作計劃
根據 Source A 識別的空檔,**自動排程**:
- 大空檔(≥ 90 分鐘)→ 深度閱讀(Source C 的 Scholar 文獻 或 Source E 的 NotebookLM follow-up)
- 中空檔(60–90 分鐘)→ 處理 🔴 / 🟡 email、文獻摘要書寫、AI 新聞延伸閱讀
- 小空檔(< 60 分鐘)→ 🟢 quick ack、處理單一 to-do

格式:`09:30–11:00 → 讀 [paper title]` / `14:00–15:00 → 回覆林經理合約 thread`

### Step 4:套 article-writer 的展開邏輯(僅 Scholar + NotebookLM 區塊)
對於 Source C 的精選文獻 + Source E 的 notebook 摘要,**用 article-writer 的 outline-then-expand 精神**:
1. 先給結構化 outline(主題、為什麼重要、與使用者既有研究的連結)
2. 再展開成 2–3 段可讀的中文摘要
3. **不要**直接搬論文 abstract——要消化過再寫
4. 引用時用 `[作者 et al., 年份]` 行內格式,文末給連結

### Step 5:產出單檔 HTML Dashboard,寫到 Obsidian 第二大腦

**寫入位置(雙寫策略)**:

1. **本機暫存**:先寫到 `<outputs>/kwota-daily-stack-{YYYY-MM-DD}.html`(供 `present_files` 用)
2. **正式歸檔到 Google Drive**:用 Drive MCP 把同一份 HTML 上傳到
   **`/一個知識庫/kwota-daily-stack/kwota-daily-stack-{YYYY-MM-DD}.html`**
   (使用者的 Obsidian 第二大腦資料夾)

**Drive 寫入步驟**:
1. 用 Drive MCP 的 `search_files` 確認 `/一個知識庫/kwota-daily-stack/` 資料夾存在;不存在則用 `create_file`(folder 類型)建立。
2. 用 `create_file`(mimeType: `text/html`)把 HTML 內容上傳到該資料夾。
3. 拿到回傳的 Drive file URL。
4. 若 Drive 寫入失敗(quota、權限、網路),halt 整個流程並回報——**不要**只寫本地就交差(這違反「進第二大腦」的核心需求)。

**檔名規則**:`kwota-daily-stack-YYYY-MM-DD.html`,一日一檔累積成歷史(不覆蓋)。



**HTML 設計準則**(嚴格遵守):
- **單檔**:HTML + 內嵌 CSS + 內嵌 JS,不拆檔
- **CDN**:只用 Tailwind CSS CDN(`https://cdn.tailwindcss.com`),不用 Chart.js 除非真的有趨勢圖
- **無 backend**:資料 hardcode 進 HTML(這是當下這份 snapshot,不需即時 fetch)
- **不做 auto-refresh**
- **配色克制**:中性灰 + 一個強調色(藍或墨綠) + 警示紅,不要全版 gradient
- **時間戳**:每個區塊角落顯示「Gmail @ 07:03」之類來源時間
- **頁首 status bar**:`Sources: 5/5 succeeded` 或 `Sources: 4/5 — NotebookLM 連線失敗`
- **語言**:繁體中文為主

**HTML 結構模板**:
```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <title>Kwo-Ta Daily Stack — YYYY-MM-DD</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-900 font-sans">
  <header class="bg-white border-b border-slate-200 px-8 py-5">
    <h1 class="text-2xl font-bold">☀️ Daily Stack — {YYYY-MM-DD ddd}</h1>
    <p class="text-sm text-slate-500 mt-1">Generated at HH:MM:SS · Sources: X/5 succeeded</p>
  </header>

  <main class="max-w-5xl mx-auto p-8 space-y-8">
    <!-- 1. 今日行程 (Calendar) -->
    <!-- 2. Email Triage 四象限 -->
    <!-- 3. AI 主流媒體新聞 (4 家分區) -->
    <!-- 4. Google Scholar 文獻精選 -->
    <!-- 5. NotebookLM 最近 3 個 Notebook + 後續研究方向 -->
    <!-- 6. 今日讀書/工作排程建議 -->
    <!-- 7. 一日總結 (2-3 句) -->
  </main>

  <footer class="text-center text-xs text-slate-400 py-6">
    kwota-daily-stack v1 · 任何失敗來源以 ⚠️ 標記
  </footer>
</body>
</html>
```

### Step 6:呈現給使用者
- 用 `mcp__cowork__present_files` 把本機 HTML 給使用者(`computer://` 連結)。
- 額外附上 Drive 連結:「📚 已歸檔到第二大腦 /一個知識庫/kwota-daily-stack/」+ Drive URL。
- Chat 回覆只要一句話 + 兩個連結 + sources 統計(`5/5 succeeded` 或 `4/5 — NotebookLM halted`)。

**不要**在 chat 裡重複貼 HTML 內容。

---

## 跨電腦攜帶性

此 skill 設計為可攜——把整個 `kwota-daily-stack/` 資料夾複製到另一台電腦的 skills 目錄即可:

- macOS: `~/Library/Application Support/Claude/.../skills/kwota-daily-stack/`
- Windows: `%APPDATA%\Claude\...\skills\kwota-daily-stack\`

依賴的 MCP servers(目標電腦必須安裝):
1. **必裝**:Gmail MCP、Google Calendar MCP、**NotebookLM MCP**、**Google Drive MCP**(寫入第二大腦)
2. **WebSearch / WebFetch**:Cowork 內建,不需另裝
3. **可選**:無

另外,Google Drive 上必須事先存在 `/一個知識庫/` 資料夾(Obsidian 第二大腦根目錄)。
`/kwota-daily-stack/` 子資料夾 skill 會在第一次執行時自動建立。

另一台電腦只要 NotebookLM MCP 有連好,prereq check 就會通過,完整 stack 就能跑。

## 與其他 skill 的關係

- **email-assistant**:本 skill 繼承其 triage 邏輯與「絕不送信」鐵則,但不自動草擬。若使用者後續要對某封信草擬,直接呼叫 email-assistant 處理那一封即可。
- **article-writer**:本 skill 借用其 outline-then-expand 寫法處理 Scholar + NotebookLM 區塊的摘要,但不產出完整文章。需要把某個研究主題展開成 blog/Medium 時,改呼叫 article-writer。
- **dashboard-builder**:本 skill 繼承其零虛擬資料原則與單檔 HTML 設計準則,但專為 Kwo-Ta 的工作流寫死了五個來源與排版,不是通用 dashboard 工具。

## 反 LLM 陳腐用詞清單(繼承自上述三 skill)

- ❌ `🚀` `✨` `💡` 之類裝飾性 emoji(只用 `⚠️` `✅` `📧` `🗓` `📚` `🤖` 等有功能意義的)
- ❌ `"Your AI-powered productivity hub"` 之類 marketing 文案
- ❌ `"AI Insights"` 區塊用來掩飾沒有實質資料
- ❌ Email 草稿開頭 `I hope this email finds you well`
- ❌ 任何「motivational quote of the day」面板
- ❌ pie chart
- ❌ auto-refresh / 假動畫 / `Loading insights...`

## 不要做的事

- ❌ 沒有 NotebookLM MCP 或 Google Drive MCP 就跑「降級版」——直接 halt(這是設計選擇)
- ❌ Drive 寫入失敗就「只寫本地交差」——halt,因為核心需求是進第二大腦
- ❌ 把整份 HTML 內容貼到 chat
- ❌ 在沒問過的狀況下,主動把急件 email 全部 `create_draft`(只列分類)
- ❌ 假資料(連線失敗就標 `⚠️`,不要編)
- ❌ AI 新聞超過 4 家來源(使用者明確只要主流四家)
- ❌ 直接複製 Scholar abstract 當摘要(要消化過再寫)
- ❌ 對 NotebookLM 建議的後續研究題目寫得空泛(必須具體可執行)
- ❌ 主動排第二天的計劃(本 skill 只處理「今天」)
- ❌ 寫 cron / 排程 — 排程交給 mcp__scheduled-tasks__create_scheduled_task,本 skill 是被排程呼叫的對象
