---
title: Hermes Agent 安裝與部署踩坑全紀錄
type: note
updated: 2026-05-26
tags:
  - Hermes
  - AI-Agent
  - Nous-Research
  - 踩坑
  - Windows
  - Telegram
  - CRON
related:
  - "[[Codex Firebase 懶人包實測踩坑]]"
---

# Hermes Agent 安裝與部署踩坑全紀錄

## 一句話總結

> 在 Windows 上把 Nous Research 的 Hermes Agent(v0.14.0)從零安裝、接通 Telegram bot、設定 CRON 每日自動推播 AI 新聞,**全程踩了 18 個坑**。本筆記是給未來重灌、教別人、或踩同樣坑時的 cheatsheet。

## 系統環境

- **OS**:Windows 10
- **既有 Python**:Anaconda 3.9.12(`C:\Users\User\anaconda3`)— **不夠用**,Hermes 需要 3.11+
- **Hermes 版本**:0.14.0
- **預期工作目錄**:`C:\Users\User\2026 Hermes\`(空資料夾,實際安裝會走全域 CLI)
- **訊息平台**:Telegram(iPhone App)
- **預設模型**:Gemini 3 Flash Preview(via Nous portal,免費)

---

## 安裝階段(踩坑 1–7)

### 踩坑 1:`pip` 不在 PATH

- **現象**:cmd 打 `pip install hermes-agent` 噴 `'pip' 不是內部或外部命令`
- **原因**:Anaconda 的 Scripts 資料夾沒加進 cmd 的 PATH,只有 Anaconda Prompt 才有
- **解法**:不用糾結 pip,改走官方 PowerShell 安裝腳本(下面踩坑 2 一起解)

### 踩坑 2:Python 3.9 太舊,純 pip 裝會失敗

- **現象**:`hermes-agent` 需要 Python 3.11+,Anaconda 預設 3.9.12 不符
- **原因**:套件相依性硬性要求
- **解法**:用官方 Windows PowerShell 一行安裝腳本,**它會自動裝齊 Python 3.11 + Node.js + ripgrep + ffmpeg + uv**,不會動到既有 Anaconda 環境:

  ```powershell
  irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1 | iex
  ```

### 踩坑 3:cmd 不認 `&&` 運算子

- **現象**:cmd 跑 `pip install hermes-agent && hermes` 失敗
- **原因**:`&&` 是 PowerShell 7 / bash 語法,Windows 內建 cmd 跟 PowerShell 5.1 不支援
- **解法**:改用 PowerShell,或用 `&` 隔開、或拆成兩行

### 踩坑 4:Sudo password 提示在 Windows 沒意義

- **現象**:Hermes setup 問 `Enable sudo support? [y/N]`,選 Y 後要妳填 `Sudo password`
- **原因**:`sudo` 跟 `apt install` 是 Linux 指令,Windows 原生環境用不到。Windows 沒所謂的「sudo 密碼」
- **解法**:遇到這題**一律答 N**(或直接按 Enter 用預設值),不要走 sudo 流程

### 踩坑 5:Gateway `start` 在 Windows 沒用,要用 `run`

- **現象**:在 Dashboard 按「重新啟動閘道」一直轉圈,跑 `hermes gateway start` 也卡死
- **原因**:`start` 是「啟動已安裝的 systemd/launchd 背景服務」,**Windows 沒有 systemd 也沒有 launchd**
- **解法**:用 `hermes gateway run`,它是前景模式(WSL/Docker/Termux/Windows 通用):

  ```powershell
  hermes gateway run
  ```

  這個 PowerShell 視窗**不能關**,gateway 會一直跑在裡面

### 踩坑 6:UAC scheduled task 安裝陷入迴圈

- **現象**:setup 問「要不要把 gateway 裝成開機自啟動的 Scheduled Task?」,答 Y 後出現 UAC 彈窗 → 沒批准 → 一直重問,出不去
- **原因**:Scheduled Task 安裝需要管理員權限,UAC 視窗常被其他視窗蓋住沒按到
- **解法**(兩條):
  - **A. 跳過**:全部問題答 **N**,跳出後手動 `hermes gateway run` 就好。新手強烈建議走這條
  - **B. 真要自啟**:找到 UAC 彈窗(`Alt+Tab` 翻、看工作列閃爍盾牌),點「是」批准

### 踩坑 7:`hermes ui` 不存在,正確是 `hermes dashboard`

- **現象**:跑 `hermes ui` 噴 `invalid choice: 'ui'`
- **原因**:子命令叫 `dashboard`,不是 `ui`
- **解法**:`hermes dashboard`(瀏覽器自動開啟看板網頁)

---

## 對話與模型階段(踩坑 8–14)

### 踩坑 8:Kanban 不是分類看板,是 AI 任務佇列

- **現象**:以為 Hermes 的 Kanban 是 Trello 那種,建了「今日新訊 / 重點關注 / 待深讀 / 已消化」4 個分類卡
- **原因**:Hermes Kanban 的欄位是**固定的工作流程狀態**(待分類 → 待辦 → 已排程 → 完成),每張卡片代表「一個給 AI 做的任務」,不是分類標籤。`Orchestration: Auto` 表示 AI 會自動 pick up 待辦的任務並執行
- **解法**:
  - 想要「定時抓資訊」→ **用 CRON**,不要用 Kanban
  - 想要「丟具體任務給 AI」→ 用 Kanban,每張卡 = 一個任務

### 踩坑 9:CRON 表達式 `0900` 是錯的

- **現象**:CRON 欄位填 `0900`(像時間寫法),儲存失敗紅字「REQUIRED」
- **原因**:Cron 必須是 5 個欄位用空白隔開(分 時 日 月 週)
- **解法**:每天早上 9:00 寫成 `0 9 * * *`。速查:
  - 每天 21:00 → `0 21 * * *`
  - 週一到週五 9:00 → `0 9 * * 1-5`
  - 每 6 小時 → `0 */6 * * *`
- **工具**:不熟 cron 語法去 https://crontab.guru 線上測試

### 踩坑 10:Claude Opus 4.6 需付費,Nous portal 餘額不足

- **現象**:任務跑出來噴 `HTTP 404: Model 'anthropic/claude-opus-4.6' requires available credits`
- **原因**:Hermes 預設用 Claude Opus 4.6,而 Nous portal 帳號餘額為 0
- **解法**:切到免費模型 `google/gemini-3-flash-preview`(透過 Nous portal 也免費)

### 踩坑 11:Main Model 改了不夠,Auxiliary Tasks 還在偷叫 Claude

- **現象**:Dashboard 把 Main Model 改成 Gemini,但 CRON 還是噴 Claude 404
- **原因**:Hermes 有兩層模型設定:
  - **Main Model**:對話用的主模型
  - **Auxiliary Tasks**:11 個輔助任務(compression、vision、cron、web_extract、summarization、title_gen、approval、MCP routing、skills_hub、triage_specifier、kanban_decomposer)**各自有獨立模型設定**,預設全 auto = Claude
- **解法**:模型頁 → AUXILIARY TASKS → CONFIGURE → **11 項全部改成 Gemini**(或想用的模型)。完成後狀態列會顯示 `11 overrides · 0 auto`
- **預防**:`RESET ALL TO AUTO` 按鈕千萬別按,會打回原狀

### 踩坑 12:Profile 名稱欄填模型代號被 reject

- **現象**:想改 profile 內的模型,結果填到「名稱」欄,被 reject「僅允許小寫字母、數字、底線及連字號」
- **原因**:填錯欄位。`google/gemini-3-flash-preview` 含 `/`,違反 profile name 規則
- **解法**:看清楚畫面結構,名稱跟模型是分開兩欄。也別亂改 `default` profile 的名字

### 踩坑 13:CRON 任務存「舊模型快照」,改設定不會自動更新已存在的任務

- **現象**:Auxiliary 全改 Gemini 了,CRON 還是噴 Claude
- **原因**:CRON 任務在**建立當下**把模型寫死,後來改 profile / auxiliary 不會回填
- **解法**:**砍掉舊任務,重新建一個**(新的會吃當下的設定)

### 踩坑 14:跑去 BotFather 對話框等 bot 回應

- **現象**:設定完 Telegram,在 @BotFather 對話框等 Hermes bot 的訊息,等不到
- **原因**:**@BotFather 是「註冊 bot 的官方工具」,不是妳的 Hermes bot**。妳建的 bot username 是妳自己取的(類似 `xxxxx_bot`),要去那個對話才有 Hermes 的回應
- **解法**:Telegram 首頁找妳自己的 bot,或上方搜尋妳的 bot username,點開對話按 START

---

## ⭐ 最高優先級踩坑:工作流哲學(踩坑 15–18)

### 踩坑 15:CRON `傳送至: telegram` 預設指向 Home Channel,不一定通

- **現象**:CRON 跑成功(Dashboard 顯示綠燈),Telegram 對話框沒收到任何訊息,log 寫 `delivery error: Telegram send failed: Chat not found`
- **原因**:`傳送至` 選 `telegram` 時對應「Home Channel」(setup 時填的 user ID)。背景排程環境裡這個 channel binding 常常沒正確初始化
- **解法**:把 `傳送至` 改成 `origin` —— 「回傳給最後建立/修改這個任務的對話視窗」
- **怎麼改**:直接在 Telegram 對 bot 說「請幫我把 daily-ai-news 的傳送目標改成 origin」,Hermes Agent 會自己呼叫 cronjob update 修好

### 踩坑 16:Gemini Flash 沒 general web search,但 API 直連工具(curl/Python)完全可信【已修正】

- **原始觀察(2026-05-26 上午)**:CRON 跑完收到「AI 新聞摘要」,懷疑 arxiv URL 是 Gemini 編造的
- **後續驗證(2026-05-26 下午)**:
  - 用 Hermes 自我盤點工具確認:**browser-based web search 確實會編造**(回答用「預測到 2026 年...」這種未來式語氣,沒有真實 URL)
  - 但 **arxiv 官方 API 直連(`export.arxiv.org/api/query`)真實可用**——驗證 `2605.26112` 等 arxiv ID 都點得開
  - PubMed E-utilities 也真實可用(6 篇 PMID 全部驗證為真)
- **修正後的結論**:
  - ❌ 不要叫 Hermes「請搜尋網路上有沒有 X 的最新消息」(會編造)
  - ✅ **要叫 Hermes「請呼叫 X API,參數是 Y,把回傳結果整理給我」**(可信)
- **設計原則**:任何需要即時/外部資料的任務,**指定明確的 API endpoint + 參數**,不要讓 Agent 自己選「怎麼搜」
- **典型可用的免費 API**(都不需要 key):
  - PubMed E-utilities: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`
  - arXiv: `http://export.arxiv.org/api/query`
  - bioRxiv/medRxiv: `https://api.biorxiv.org/details/`
  - Semantic Scholar: `https://api.semanticscholar.org/graph/v1/`
  - Crossref(DOI lookup): `https://api.crossref.org/works`
- **預防**:寫 CRON prompt 時,**直接把 API URL + 參數寫進指令裡**,並加一句「如果 API 呼叫失敗,直接給我錯誤訊息,不要編造資料」

### 踩坑 17 ⭐ 最關鍵:觸發點決定回報點,Dashboard Run now 結果常消失

- **現象**:
  - 在 Dashboard 按 ▶︎ Run now → 任務跑成功,但 Telegram 收不到
  - 在 Telegram 對 bot 說「請執行 daily-ai-news」→ Telegram 立刻收到完整結果
- **原因**:從 Telegram 對話觸發時,Agent 會把當前 chat_id 當成 `origin`,直接回傳到妳眼前,**繞過 Home Channel 機制**。Dashboard 觸發則照任務本身的 `deliver` 設定,如果 deliver=telegram 但 Home Channel 沒綁好就石沉大海
- **核心觀念**:
  > Dashboard 上的 ▶︎ Run now 只是「執行」任務,
  > **「結果回報路徑」取決於任務本身的 deliver 設定**。
  >
  > 對話觸發則是「執行 + 回報路徑自動設為當前對話」,
  > 兩個動作一氣呵成,**最不會出錯**。
- **解法**(優先序):
  1. 建立任務時 `傳送至` 改 `origin`(而非 `telegram`)→ 不管從哪觸發都會回到觸發點
  2. 習慣從 Telegram 觸發,不要從 Dashboard 觸發
  3. 設好排程後手動測一次,確認有收到再離開
- **反模式對照**:

  ```
  ❌ 反模式
     建立 CRON → deliver=telegram(預設值)
     早上自動跑 → 結果消失在 Home Channel(Chat not found)
     立刻重跑 → Dashboard 按 Run now(也消失)
     永遠收不到結果,以為系統壞了

  ✅ 正確
     建立 CRON → deliver=origin
     早上自動跑 → Telegram 自動收到
     想立刻重跑 → 在 Telegram 對 bot 說「跑一下 daily-ai-news」
  ```

### 踩坑 18 💡 心智模型:對話是主軸,Dashboard 是儀表板

- **現象**:把 Hermes 當傳統 SaaS,用 Dashboard 操作、按鈕觸發任務、表單填參數,結果發現按鈕按了沒反應、改了沒生效、CRON 跑了沒結果
- **正確心智模型**:Hermes 是「**會用工具的 Agent**」,跟它**講話**最有效:
  - 新增 CRON → 對 bot 說「幫我設一個每天早上 9 點搜 AI 新聞的任務」
  - 改設定 → 對 bot 說「把 daily-ai-news 時間改成晚上 10 點」
  - 看狀態 → 對 bot 說「我的 CRON 任務有哪些?」
  - 砍任務 → 對 bot 說「砍掉 daily-ai-news」
  - Agent 會自己呼叫 cronjob update/delete/list 等工具,比手動點 Dashboard 還快、還準、還能自動修錯
- **Dashboard 該用在什麼時候?**
  - 第一次裝完做基礎配置(模型、auxiliary、profile)
  - 想視覺化看「現在有哪些任務、執行歷史」
  - 偵錯時看詳細 log
  - **不適合:日常操作、觸發任務、改參數**
- **經驗法則**:
  > 如果妳在 Dashboard 點按鈕點到第三次還沒成功,
  > 停下來,打開 Telegram,**用講的**。

### 踩坑 19:Dashboard 的「傳送至」下拉沒有 `origin` 選項

- **現象**:在 Dashboard 新增 CRON 任務時,「傳送至」下拉只有 `本機 / Telegram / Discord / Slack` 等靜態選項,**沒有 `origin`**。但踩坑 15、17 都強烈建議用 `origin` 才不會結果消失
- **原因**:`origin` 是 Hermes 內部的特殊 delivery mode(回傳給觸發任務的對話視窗)。Dashboard UI 沒實作這個下拉選項,但底層任務的 `deliver` 欄位接受任意字串,只是 UI 沒暴露給妳選
- **解法**:**用對話建造任務**——直接在 Telegram 對 bot 說「幫我建一個 CRON,傳送至 origin」,Hermes 會呼叫 `cronjob create` 工具並把 `deliver` 欄位塞進 `origin`。Dashboard 永遠做不到這件事
- **延伸觀察**:這是踩坑 18 的具體案例。判斷標準變得更清楚:

  ```
  能在 Dashboard 做這件事嗎?
  ├── 能 → 兩條路都行
  └── 不能 / 選項不全 → 一定要走對話路徑
                        (Agent 用工具的能力 ⊃ Dashboard UI)
  ```

- **預防**:任何想用 `origin` 的任務(基本上是所有 CRON),**從一開始就用對話建,別走 Dashboard**。

### 踩坑 20:Hermes 自我盤點是設計工作流的省力起點

- **現象**:設計新工作流時不知道 Hermes 有哪些工具/能力,猜半天設定方向錯
- **原因**:Plugins 頁面列出來的是「可安裝清單」,有些是 `inactive` 但實際可用、有些可用但沒在清單(例如內建的 PubMed via curl、Python via execute_code)
- **解法**:直接讓 Hermes 自我盤點。送一段「請逐項用工具驗證,真的試一次,不能說『理論上可以』」的診斷指令,例如:

  ```
  請用工具盤點你目前的能力,逐項真的試一次後回答:
  1. Web Search:能上網嗎?用什麼工具?現在搜「X」給我前 3 個結果
  2. PubMed:能 curl https://eutils.ncbi.nlm.nih.gov/... 嗎?現在試
  3. Python:能跑 `import requests; r = requests.get(...)` 嗎?現在試
  4. Gmail:能讀我的 Gmail 嗎?列過去 24h unread subject
  5. Calendar:能看我的 Calendar 嗎?列今天 events
  6. 外掛清單:跑 hermes plugins list

  每項回「✅ 可以,結果是…」或「❌ 不行,原因是…」。
  工具呼叫失敗就給我錯誤訊息,**不要編造**能力。
  ```

- **預防**:這個診斷指令值得存成模板,以後每次想設計新工作流前先跑一次,5 分鐘抵 2 小時的猜測

---

## 最終可用配置(2026-05-26 狀態)

### 模型設定
- **Main Model**:`google/gemini-3-flash-preview` (via Nous portal,免費)
- **Auxiliary Tasks**:11 項全部 override 為 Gemini Flash
- **Profile**:`default` profile 設為 Gemini;其他 (coder/researcher/reviewer) 暫不動

### 訊息平台
- **Telegram bot**:`KT Chu bot`(`@xxxxx_bot`)
- **Allowed user**:`8780377967`(個人 user ID)
- **Home Channel**:同 user ID(但不可靠,優先用 origin)

### CRON 任務

- **`daily-ai-news`** ⚠️ 部分編造(Gemini 沒 web search 會瞎掰 arxiv)
  - Schedule:`0 9 * * *`(每天早上 9:00)
  - Profile:`default`
  - Deliver:`origin`(修正後)
  - 用途:每日 AI/LLM/agentic AI 領域 3-5 條進展摘要
  - **狀態**:被 `morning-research-brief` 涵蓋,可考慮砍掉

- **`morning-research-brief`** ✅ Phase 1 已驗證,2026-05-26 建立
  - Schedule:`0 8 * * *`(每天早上 8:00)
  - Profile:`default`
  - Deliver:`origin`(對話建造,Dashboard 做不到)
  - Job ID:`e203b6411756`
  - 用途:每日醫學/神經科學情報員,三區塊整合:
    - 區塊 A:認知神經科學(Alzheimer + Diabetes-Dementia + Nature/Science/PNAS)→ PubMed
    - 區塊 B:腎臟學(NEJM/AJKD/KI/Lancet)→ PubMed
    - 區塊 X:AI 進展(arxiv API)→ 待驗證可信度
  - **驗證結果(2026-05-26 首次 Run now)**:
    - PubMed 6 篇全部 PMID 真實、abstract 內容詳細正確 ✅
    - arxiv 2 篇驗證真實(`2605.26112` 由作者 Shangding Gu 發表於 cs.AI 2026-05-25,完全對得上) ✅
    - 免責聲明正確出現
    - Telegram 推播自動分段(1/2, 2/2)
    - **整套工作流 100% 可信**,可放心使用

---

## 常用指令速查

| 想做的事 | 指令 |
|---|---|
| 啟動 gateway(前景) | `hermes gateway run` |
| 開看板 / Web UI | `hermes dashboard` |
| 直接終端對話 | `hermes chat` |
| 看狀態 | `hermes gateway status` |
| 看可用模型 | `hermes model` |
| 健康檢查 | `hermes doctor` |
| 子命令 help | `hermes <subcommand> --help` |
| 看版本 | `hermes version` |

**所有子命令清單**(從 hermes --help 抓):
`chat, model, fallback, secrets, migrate, gateway, proxy, lsp, setup, postinstall, whatsapp, slack, send, login, logout, auth, status, cron, webhook, portal, kanban, hooks, doctor, security, dump, debug, backup, checkpoints, import, config, pairing, skills, bundles, plugins, curator, memory, tools, computer-use, mcp, sessions, insights, claw, version, update, uninstall, acp, profile, completion, dashboard, logs`

---

## 待解決問題 / 後續優化

- [x] ~~驗證 daily-ai-news 第一次自動跑~~(被 morning-research-brief 取代)
- [x] **建立 morning-research-brief Phase 1**(2026-05-26 完成,PubMed 區塊已驗證真實)
- [ ] **驗證 morning-research-brief 明早 8:00 自動觸發**(2026-05-27)
- [x] **驗證 arxiv 區塊 X 的可信度**(2026-05-26 完成):`2605.26112` (From Model Scaling to System Scaling, by Shangding Gu) 已點開驗證為真,arxiv API pipeline 完全可信
- [ ] **記憶系統測試**:Hermes 已在 2026-05-26 確認把「繁體中文偏好」存進長期記憶,**待跨 session 驗證**
- [ ] **Phase 1.5:Gmail + Calendar 整合**:需要安裝 `gws` (Google Workspace CLI) 並完成 OAuth,讓 Hermes 能讀 Gmail 重要未讀 + 今日 Calendar
- [ ] **Phase 2:加入 multi-agent**:用 coder / researcher / reviewer profile 對應 literature / hypothesis / critic 角色,實現 AI Agent Research Automation skill 的完整框架
- [ ] **與 Obsidian vault 整合**:讓 Hermes 直接寫每日 brief 進 vault(每日筆記/ 或 創作庫/),透過 mcp-obsidian 或檔案系統 plugin
- [ ] **多 profile 角色設計**:coder / researcher / reviewer 目前是 auto + Claude,要為它們指派合適模型(可能 researcher 用 Claude+web search、coder 用 Gemini)

---

## 關鍵教訓

1. **Windows + AI agent CLI 工具的水土不服**:大部分文件假設 Linux/macOS,Windows 使用者要自己翻譯 `start` → `run`、`ui` → `dashboard`、跳過 sudo/systemd 相關問題
2. **多層模型設定的隱形成本**:Main / Auxiliary / Profile / 任務內嵌模型四層,改一層不夠
3. **Agent 的對話導向 vs Dashboard 的視覺導向**:Hermes 是前者,SaaS 思維會撞牆
4. **「沒 web search」≠「不能上網」**:Gemini Flash 沒 browser-based web search,但 Hermes 能直接 curl/Python 呼叫 API。**指定 API endpoint 給 Agent,不要叫它「搜尋網路」**——前者真實,後者編造
5. **Agent 自己修錯的威力**:踩坑 15 的「Chat not found」是 Hermes 自己診斷、自己跑工具鏈、自己改設定修好的,只用了一句「請幫我修正傳送的頻道」。這就是 agentic AI 的真正價值
6. **PubMed E-utilities 是醫療研究自動化的金礦**:免費、無 key、官方支援、能 fetch 完整 abstract。對醫師/研究者來說,這個 API 應該變成 daily driver,Google Scholar 對醫學文獻可以省
