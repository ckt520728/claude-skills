---
name: dashboard-builder
description: 為使用者建立**個人化資訊看板**——從既有資料來源(Gmail、Obsidian vault、Google Calendar、NotebookLM、本地檔案、Google Drive)聚合成每日 briefing、每週回顧、專案狀態、閱讀進度等實用 dashboard。輸出格式優先選 Markdown 或單檔 HTML(無需跑 server),Streamlit / Dash 只在真正需要互動時才用。觸發詞:「做一個 dashboard」「我要看每天的 briefing」「整理一個 weekly review」「build a daily summary view」「I want a dashboard for X」「做一個個人後台」「each morning show me X」「把這些資訊匯整成一頁」「produce a status report」「我想一眼看到 X+Y+Z」。可結合 schedule skill 變成定時自動產出。不適用:純對話介面(那是 ChatGPT/Claude 自己的工作,不需另做)、商業 BI(那是 Tableau/PowerBI 的範疇)、即時系統監控(那是 ops 範疇)。
---

# Dashboard Builder

## 目的

幫使用者把「每天/每週想看到的資訊」聚合成一個**可重複產出**的看板。重點不是花俏的 UI,是:

- **聚合**:從多個來源(MCP 工具 + 本地檔案)抓資料
- **濃縮**:每個面板回答一個明確問題,不是貼一堆原始 dump
- **可重產**:存成腳本,使用者隨時 `python dashboard.py`(或 `claude run dashboard`)就刷新
- **可定時**:配合 schedule skill 變成「每天早上自動生成今日 briefing」

## 🚨 鐵則:零虛擬資料(Zero-Mock-Data Rule)

dashboard 上的**每一個**數字、項目、清單,都必須來自實際 MCP 呼叫或檔案讀取。**絕對不准**:

- 為了「先看一下長怎樣」就放假資料(`"Lorem ipsum email"`、`"Meeting at 3pm with John"`、隨機數字)
- 用 emoji + 隨機數值「裝飾」面板
- 因為某個資料來源連不上,就用上次的快取或估計值假裝有資料

資料來源連不上時,該面板顯示明確的失敗訊息(例:`⚠️ Gmail 連線失敗 @ 09:32,請手動檢查`),而**不是**留空、塞假資料、或捏造數字。

理由:dashboard 一旦讓使用者懷疑「這個數字是真的還是假的?」就完全失去信任,變成裝飾品。

## 觸發後的工作流程

### Step 1:聚焦四個問題

主動問,直到四個都清楚:

1. **這個 dashboard 回答什麼問題?**
   - ❌ 「showing my data」(太空泛)
   - ✅ 「每天早上 8 點打開,讓我知道今天有什麼會議、未讀 email 中哪些急、Inbox 裡有沒有需要審的新筆記」
2. **資料從哪來?**(逐項列出來源)
   - Gmail 未讀 → Gmail MCP
   - 今日行程 → Calendar MCP
   - Obsidian Inbox 新檔 → Obsidian MCP
   - 本地某資料夾的最新檔案 → 檔案系統
   - 等等
3. **多久看一次?**
   - 每天早上 / 每週日晚上 / 隨時隨手 / 一次性
4. **看在哪裡?**
   - Markdown 檔(Obsidian / VS Code preview 開) ← 預設
   - 單檔 HTML(雙擊瀏覽器開,可有簡單互動)
   - 終端機文字(SSH / CLI 環境)
   - Streamlit(**僅當**真的需要表單輸入或即時互動,例外)

不要連環問——使用者通常一句話會給你 2-3 個維度的資訊,剩下的補問就好。

### Step 2:選輸出格式(預設 Markdown)

| 使用情境 | 建議格式 | 理由 |
|---------|---------|------|
| 個人每日 briefing | **Markdown** | Obsidian 開、VS Code 開、純文字易讀;不需 server |
| 週報 / 月報 | **Markdown** | 同上 + 可長期歸檔 |
| 多面板「儀表板」感、要顏色/icon | **單檔 HTML** | 雙擊就開,可內嵌 chart.js / tailwindcss CDN,不需 server |
| 真的需要表單、即時 query、互動篩選 | Streamlit / 簡單 Flask | **這時候才考慮**——需要使用者啟動 server,日常用很煩 |
| SSH / Cron 環境只看終端 | Plain text + ANSI 顏色 | 用 `rich` library |

**強烈建議從 Markdown 開始**:如果第一版 MD 不夠用,再升級到 HTML。直接跳 Streamlit 通常是過度工程。

### Step 3:設計面板架構

跟使用者一起決定 dashboard 有幾個區塊,每區塊回答什麼。範例(daily briefing):

```
┌─────────────────────────────────────┐
│ ☀️ Daily Briefing — 2026-05-13      │
├─────────────────────────────────────┤
│ 1. 今日行程(3 件)                    │ ← Calendar MCP
│ 2. 急件 Email(2 封)                  │ ← Gmail MCP + 規則篩
│ 3. Inbox 待審筆記(7 篇)              │ ← Obsidian MCP
│ 4. 昨日 carry-over actions(4 件)     │ ← 解析最近 meeting-minutes 檔
│ 5. 本週進度(這週寫 / 讀 / 開會)        │ ← 多源聚合
└─────────────────────────────────────┘
```

設計原則:
- **首版只放 3-5 個面板**——多了沒人會看
- 每個面板有**明確一句話標題**(「今日行程」不是「日程」)
- 每個面板**附資料來源時間戳**(`(Gmail @ 08:32)`)
- 排序:**最急的放最上**

### Step 4:寫產出腳本

預設用 Python(因為 MCP 客戶端 + 各種 lib 最齊),寫到工作目錄或使用者指定路徑:

```
dashboard/
├── dashboard.py           # 主腳本,執行後產出 dashboard 檔
├── sources/
│   ├── gmail.py           # 抓 Gmail 的邏輯(可被 dashboard.py import)
│   ├── calendar.py
│   ├── obsidian.py
│   └── ...
├── render/
│   ├── markdown.py        # MD render template
│   └── html.py            # (若有 HTML 版)
├── config.yaml            # 可調參數(時區、Inbox 路徑、急件規則、etc)
└── output/
    └── briefing_2026-05-13.md  # 產出
```

**每個 source 模組**必須:
1. 有明確的 fetch 函數,return 結構化資料(list / dict)
2. **錯誤處理**:連線失敗回 `{"error": "...", "fetched_at": ...}` 而不是 raise
3. 不主動寫死任何「假資料」用於測試(測試另外開檔)

**render 模組**收 source 回來的資料,輸出最終文件。錯誤的 source 在輸出中顯示為:

```markdown
## 今日行程
> ⚠️ Calendar MCP 連線失敗 @ 08:32
> Error: timeout after 10s
> 上次成功抓取:2026-05-12 08:31
```

### Step 5:跑一次,看真實輸出

寫完腳本**立刻跑一次**,把實際產出檔給使用者檢查:

```bash
python dashboard.py
```

回報:
- 產出檔路徑
- 每個面板的資料來源是否成功(成功/失敗各幾個)
- TL;DR 第一句(從產出檔抓)

如果有面板資料是空的(例如今天沒會議),確認這是**真的空**還是**抓失敗**——兩個情況面板要顯示不同訊息:

- 真的空 → `今日無會議。`
- 抓失敗 → `⚠️ Calendar 連線失敗 @ 08:32`

### Step 6:可選——加排程(配合 schedule skill)

問使用者:「要不要設成每天早上 7:55 自動產出?」

如果要,呼叫 schedule skill(或直接走 `mcp__scheduled-tasks__create_scheduled_task`),把 `python dashboard.py` 加進 cron。

**不要**主動加排程——問了才加。

## Markdown 看板的範本

```markdown
# ☀️ Daily Briefing — 2026-05-13 (Mon)

*Generated at 08:00:23. Sources: 4/5 succeeded.*

---

## 🗓 今日行程
*(Calendar @ 08:00)*

- **09:00–10:00** Team standup `Zoom`
- **14:00–15:30** 王老師會議 `Conference Room A` — 議題:Q2 預算
- **16:00** Submit grant draft (內部 deadline)

> 衝突檢查:無

## 📧 急件 Email
*(Gmail @ 08:00 · 過濾規則:`is:unread AND (label:client OR from:boss@...)`)*

1. **林經理** — Re: 上週合約版本(等待 24h)
2. **學生 A** — 論文 draft 第二版回覆(等待 36h)

(其他 12 封未讀,點 [完整收件夾](mailto://...) 查看)

## 📥 Obsidian Inbox 待審
*(Obsidian @ 08:00)*

最近 48h 新進 7 篇:

- `2026-05-12 ingested paper - Attention is All You Need.md` — status: inbox
- `2026-05-11 meeting Q2 budget.md` — status: inbox
- ...

## ✅ Carry-Over Actions
*(parsed from meeting-minutes/*.md @ 08:00)*

- [ ] 寄出 Q2 預算修正版給林經理(deadline: 2026-05-13,**今天**)
- [ ] 確認租約條款第 7 條(deadline: 2026-05-14)
- [ ] ...

## 📊 本週至今(週一 → 今天)
*(aggregate @ 08:00)*

- 讀:3 篇 paper / 1 本書
- 寫:1 篇 article draft (knowledge-base ingest: 4 筆)
- 開:5 場會議
- 收 email:127 封 / 回 89 封 / 草稿待送:6

---

> ⚠️ NotebookLM source 連線失敗 @ 08:00,該面板已略過。
```

## HTML 看板的設計準則(若選 HTML)

只有當 Markdown 真的不夠才走 HTML。準則:

- **單檔**:HTML + 內嵌 CSS + 內嵌 JS,不要拆檔(個人 dashboard 不需要 webpack)
- **CDN 引用 Tailwind / Chart.js**:不要 npm install
- **無 backend**:資料用 fetch 時間生成的 `const data = {...}` 內嵌進 HTML
- **重新整理 = 重跑腳本**:不做「網頁 auto-refresh」,因為個人 dashboard 不需要每 5 秒 fetch 一次
- **適度顏色**:status 用顏色(綠/黃/紅),但**不要**整版 gradient 跟 emoji

## Streamlit / Flask 的使用情境(僅限以下)

只有以下情境用 Streamlit:

- 需要使用者**輸入表單**才能查詢(例:「輸入專案名,顯示該專案所有相關筆記」)
- 需要**篩選 / 排序**互動(例:大量資料的 filterable table)
- 多人協作(別人也要打開看)→ 此時也得處理 hosting,日常使用通常不適合

絕大多數個人 dashboard 用 Markdown 或 HTML 已經夠,不要被「dashboard 一定要 Streamlit」綁架。

## 反 LLM dashboard 陳腐用詞清單

- ❌ `🚀` `✨` `💡` 之類裝飾性 emoji(只用真有資訊功能的 icon:`⚠️` warn、`✅` 完成、`📧` email、`🗓` calendar)
- ❌ `"Your AI-powered productivity hub"` 之類 marketing 文案
- ❌ `"Loading insights..."` 不會結束的 spinner(真的失敗就明說失敗)
- ❌ 為了佔版面而生的「motivational quote」面板
- ❌ 「Last updated: just now」(用實際時間 `08:32:15` 而不是「just now」)
- ❌ 用「AI Insights」這個區塊來掩飾沒有實質資料(如果只剩 LLM 生成的「insight」可以塞,就代表你的 dashboard 沒有真正內容,該刪減而不是補)

## 重要的設計原則

**Less is more**:dashboard 上每多一個面板,都增加維護成本和注意力分散。第一版只放 3-5 個,跑兩週後再決定加減。

**信任 > 完整**:寧可 dashboard 上少一個面板,也不要那個面板資料不可靠。資料不可靠的面板比沒有更糟。

**時間戳是必要的**:每個面板都顯示「資料是何時抓的」,讓使用者知道資料新鮮度。

**配色克制**:dashboard 不是設計作品。用兩三個顏色就夠(中性灰 + 強調色 + 警示紅)。

**避開「儀表板綜合症」**:不要每個面板都套同一個視覺模板(全部 card / 全部 metric tile)。文字面板就用文字,清單就用 bullet,趨勢才用圖。

**腳本要可被使用者讀懂**:dashboard.py 內的程式碼結構要清楚,因為使用者三個月後會想自己改一個面板。寫法清晰 > 寫法巧妙。

## 跟其他 skill 的協作

- **meeting-minutes ← dashboard-builder**:carry-over actions 面板從 `meeting-minutes/*.md` 解析
- **knowledge-base ← dashboard-builder**:Inbox 待審面板從 vault 抓 `status: inbox` 的筆記
- **email-assistant ← dashboard-builder**:急件 email 面板用 Gmail MCP 篩選,然後可一鍵接 email-assistant 起草草稿
- **schedule(內建)→ dashboard-builder**:用 schedule skill 把 `python dashboard.py` 設成每天定時跑
- **data-analyzer ← dashboard-builder**:若有面板需要做時序聚合 / 統計,呼叫 data-analyzer 的邏輯

## 不要做的事

- ❌ 不要做「Streamlit + 一個對話框 + 串 GPT」這種沒實際價值的 dashboard——那是把 ChatGPT 介面變難用
- ❌ 不要塞假資料給使用者「先看一下長怎樣」——直接跑真實資料,即使一開始只有 2 個面板
- ❌ 不要主動加排程——問了才設定
- ❌ 不要用「AI Insights」面板掩飾沒有實質資料
- ❌ 不要用 auto-refresh 每 N 秒重抓 → 浪費 API quota 且製造焦慮
- ❌ 不要在連不到資料來源時顯示 0 / 空白 / 上次快取——一律明示「連線失敗 @ 時間」
- ❌ 不要把整份 dashboard.py / dashboard.md 內容貼到 chat 裡——使用者去打開檔案
- ❌ 不要每個面板都套同一個 card UI 模板,造成假對稱感
- ❌ 不要用 pie chart(同 data-analyzer 規則)
- ❌ 不要把資料源寫死在腳本裡 hardcode——抽到 `config.yaml`,讓使用者三個月後可改
