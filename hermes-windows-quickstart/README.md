# Hermes Agent · Windows 安裝懶人包

> **5 步驟、20 分鐘**,在 Windows 上裝好 Hermes Agent + 接通 Telegram + 跑你的第一個 daily research brief。
>
> 適合對象:對 AI agents 有興趣的 Windows 使用者(不需要工程背景)
>
> 經 2026-05-26 親身踩 20 個坑驗證,所有指令都是真實可用版本。完整踩坑紀錄見文末連結。

---

## TL;DR(60 秒看完)

```
1. PowerShell 跑一行安裝
2. setup 精靈一路答 N(不要 sudo、不要 scheduled task)
3. 申請 Telegram bot + 接通 Hermes
4. 把 Main Model + 11 項 Auxiliary 全改成 Gemini 3 Flash(免費)
5. 在 Telegram 對 bot 講話,讓它建你的第一個 CRON
```

**執行成果**:每天早上 8:00 自動收到一則 PubMed + arxiv 整理的文獻摘要,送到你的 Telegram bot。完全免費,不需要任何付費 API key。

---

## 前置需求

- Windows 10 或 11
- PowerShell(系統內建,不需要 PowerShell 7)
- ~4 GB 硬碟空間(自動裝 Python 3.11、Node.js、ripgrep、ffmpeg)
- Telegram 帳號 + 手機 App
- **不需要付費 API key**(全程用 Nous portal 免費 Gemini 3 Flash)

---

## Step 1:安裝 Hermes(5 分鐘)

### 1.1 開 PowerShell(不要用 cmd)

`Windows 鍵` → 輸入 `PowerShell` → 點開。

> ⚠️ **千萬別用 cmd**。cmd 不認 `&&`、不認 PowerShell 語法,後面會撞牆。

### 1.2 跑官方安裝腳本

複製這一行,貼到 PowerShell,按 Enter:

```powershell
irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1 | iex
```

這會自動裝 Python 3.11(**不會動到你既有的 Anaconda**)、Node.js、ripgrep、ffmpeg、uv,並把 `hermes` 加入 PATH。需時 5–10 分鐘。

### 1.3 重開 PowerShell

PATH 變更要重新開 shell 才生效。**關掉這個 PowerShell,重新開一個**。

---

## Step 2:跑 setup 精靈(5 分鐘)

```powershell
hermes setup
```

它會問你一連串問題。**照下表回答,別自己亂試**:

| 問題 | 答 | 原因 |
|---|---|---|
| Terminal backend? | **Local** | 在本機跑 |
| Gateway working directory? | Enter(用預設 `.`) | 用當前資料夾 |
| **Enable sudo support?** | **N** | Windows 沒有 sudo |
| **Install gateway as scheduled task?** | **N** | 跳過自啟動,手動跑就好 |
| **Start the gateway automatically on Windows login?** | **N** | 同上 |
| 任何問 UAC / scheduled task / 自動啟動 | **N** | 全部跳過 |

完成後跳出精靈,回到 PowerShell 提示符。

> ⚠️ **遇到 UAC 彈窗(Windows 安全性警示)直接關掉**,別點「是」。一旦啟動 scheduled task 路徑會陷入迴圈。

---

## Step 3:接通 Telegram bot(10 分鐘)

### 3.1 在手機 Telegram 申請 bot

1. 打開 Telegram App
2. 搜尋 `@BotFather`(官方,藍勾驗證)
3. 送 `/newbot`
4. 取個 bot 名字(隨意,例如 `My Hermes`)
5. 取個 username(必須以 `bot` 結尾,例如 `my_hermes_bot`,全球唯一)
6. BotFather 會回一段話,裡面有:
   ```
   Use this token to access the HTTP API:
   123456789:AAH-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   **複製整串 token,等下要用**

> 🔒 Bot Token = bot 的密碼。**千萬別公開、別截圖貼網路**。

### 3.2 拿到你的 Telegram User ID

1. Telegram 搜尋 `@userinfobot`
2. 按 `/start`
3. 它會回:
   ```
   🆔 Id: 987654321
   ```
4. **記下這串純數字**(這個不是機密,但要正確)

### 3.3 在 Hermes 設定 Telegram

回 PowerShell,執行:

```powershell
hermes gateway setup
```

按提示:
- 選 `telegram`
- 貼 Bot Token
- 填 Allowed User IDs:**就是你的 User ID 那串純數字**
- Home Channel:選擇 `Use your user ID as the home channel? Y`
- 後面任何問「Install as scheduled task / 自動啟動」**一律 N**

### 3.4 啟動 Gateway

```powershell
hermes gateway run
```

> ⚠️ **這個 PowerShell 視窗不能關**,gateway 在這裡跑。要關掉就按 `Ctrl+C`。
>
> 別用 `hermes gateway start` —— 那是 Linux 的(systemd/launchd),Windows 上會卡死。

成功啟動會看到:
```
Hermes Gateway Starting...
Messaging platforms + cron scheduler
Press Ctrl+C to stop
```

可能會看到兩個 WARNING(`No user allowlists` / `No messaging platforms`),如果剛剛 gateway setup 有完成,重啟一次就會消失。

### 3.5 測試 bot 連線

iPhone 打開 Telegram → 上方搜尋你剛取的 bot username(`@xxxxx_bot`)→ 點開 → 按 **START** → 打「你好」送出。

如果 bot 在幾秒內回應 → **連線成功 🎉**

> ⚠️ 注意:你要去的是**自己建的 bot 對話**(`KT Chu bot` 之類的),不是 `@BotFather` 的對話。

---

## Step 4:切到免費 Gemini 模型(5 分鐘)

Hermes 預設用 Claude Opus 4.6,要付費。換成 Nous portal 免費的 Gemini 3 Flash。

### 4.1 開 Dashboard

**另開**一個 PowerShell 視窗(**不要關 gateway 那個**!):

```powershell
hermes dashboard
```

瀏覽器會自動彈出 `http://localhost:xxxx`。

> ⚠️ 是 `hermes dashboard`,**不是** `hermes ui`(`ui` 不存在,會噴 invalid choice)。

### 4.2 改 Main Model

左側 sidebar → **模型(Model)**

找 `google/gemini-3-flash-preview` 那張卡 → 點 **USE AS → Main**。

頂部 MAIN MODEL 應該變成 `nous · google/gemini-3-flash-preview`。

### 4.3 改 Auxiliary Tasks(關鍵步驟,**絕對不能跳**)

⚠️ **這一步漏掉的話,CRON 還是會偷叫 Claude,噴付費錯誤**。

同一頁 → **AUXILIARY TASKS** → 點 **CONFIGURE**。

會跳出 11 項輔助任務(Vision、Web Extract、Compression、Skills Hub、Approval、MCP、Title Gen、Triage Specifier、Kanban Decomposer、Session Search、Memory Curator)。**每一項**點 **CHANGE** → 改成 `google/gemini-3-flash-preview` → 存檔。

改完狀態列應該顯示:
```
AUXILIARY TASKS: 11 overrides · 0 auto
```

> 🚨 **千萬不要按右上角的 `RESET ALL TO AUTO`** —— 會打回原狀,前功盡棄。

### 4.4 改 default Profile

左側 sidebar → **多代理設定檔(Profiles)** → 點 `default` → 把內部的 `model` 欄位改成 `google/gemini-3-flash-preview` → 存檔。

---

## Step 5:建你的第一個 CRON 工作流(5 分鐘)

**重要觀念**:Hermes 是「會用工具的 Agent」,建任務最快的方法是**對 bot 講話**,不是用 Dashboard。Dashboard 的「傳送至」下拉甚至沒有 `origin` 選項(最重要的 delivery mode),但對 bot 講話它會自己處理。

### 5.1 在 Telegram 對 bot 送這段(整段複製)

````
請幫我建立一個新的 CRON 任務,設定如下:

- 名稱: hello-cron
- 排程: */5 * * * *  (每 5 分鐘一次,測試用)
- 傳送至: origin (這個對話)
- Profile: default
- 提示詞: 用 Python 跑 `print("Hello from Hermes CRON at " + str(datetime.datetime.now()))`,把結果回傳給我。

建立後請立刻 Run now 測試一次。
````

### 5.2 觀察 bot 回應

Bot 會:
1. 自己呼叫 `cronjob create` 工具
2. 立刻執行一次
3. 把結果(`Hello from Hermes CRON at 2026-05-26 14:35:00`)回傳到 Telegram

看到時間戳訊息 → **整個系統運作正常 🎉**

### 5.3 測試完記得砍掉

每 5 分鐘觸發一次會洗版。對 bot 說:

```
請砍掉 hello-cron。
```

Bot 會自己呼叫 `cronjob delete`。

---

## 驗證安裝成功的 5 個訊號

| # | 檢查項 | 通過標準 |
|---|---|---|
| 1 | `hermes version` | 顯示版本號(例如 `0.14.0`) |
| 2 | `hermes gateway run` | 啟動後顯示 `Gateway Starting`,沒有 error |
| 3 | Telegram 對 bot 打「你好」 | 5 秒內收到 Gemini 生成的回應 |
| 4 | Dashboard 左下角 | `Gateway Status: 執行中`(綠燈) |
| 5 | 模型頁 Auxiliary Tasks | `11 overrides · 0 auto` |

五項都過 = 部署完成。

---

## 常見錯誤對照表

| 錯誤訊息 / 現象 | 解法 |
|---|---|
| `'pip' 不是內部或外部命令` | 別用 cmd,用 PowerShell。直接跑官方安裝腳本(Step 1.2) |
| `HTTP 404: Model requires available credits` | Auxiliary Tasks 還在用 Claude。回 Step 4.3 全改成 Gemini |
| `delivery error: Telegram send failed: Chat not found` | CRON 的 deliver 設成 `telegram` 但 Home Channel 沒綁好。**對 bot 說「請把 X 的傳送目標改成 origin」** |
| `hermes: invalid choice: 'ui'` | 用 `hermes dashboard`,不是 `hermes ui` |
| `Gateway already running (PID xxx)` | 已在跑了。`hermes gateway status` 看狀態 |
| Dashboard 「重啟閘道」一直轉圈 | 那按鈕在 Windows 上沒用。改用 PowerShell `hermes gateway run` |
| CRON 跑了但 Telegram 沒收到 | 用對話建任務(deliver=origin),別用 Dashboard 建 |
| Bot 沒回應 | 確認 gateway 視窗還開著、確認去自己的 bot 對話(不是 @BotFather) |
| Setup 卡在 UAC 迴圈 | 關掉 UAC 彈窗,scheduled task 相關問題全答 N |
| CRON 改了設定還是用舊模型 | CRON 存舊快照,**砍掉重建**才會吃新設定 |
| Profile 名稱欄輸入被 reject | 看清楚欄位,名稱欄不能填模型代號(`/` 違規) |

---

## 進階使用

### 想加新工作流?用對話建,別用 Dashboard

```
對 bot 說:
「幫我建一個 CRON,每天晚上 10:00 提醒我吃藥,傳送至 origin」
```

Bot 會自己處理。Dashboard 的「傳送至」下拉**沒有 `origin` 選項**,只有對話建造才能用。

### 想搜真實網路資料?指定 API,別叫它「搜尋」

- ❌ 不要:「請搜尋網路上最新的 X」(Gemini 沒 web search,會編造)
- ✅ 要:「請呼叫 PubMed E-utilities API,查 X,把結果整理給我」(可信)

**免費可用 API 清單**(都不需要 key):

| 領域 | API | URL |
|---|---|---|
| 醫學文獻 | PubMed E-utilities | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` |
| AI / 物理 / quant-bio | arXiv | `http://export.arxiv.org/api/query` |
| 生醫 preprint | bioRxiv / medRxiv | `https://api.biorxiv.org/details/` |
| 跨領域 + 引用 | Semantic Scholar | `https://api.semanticscholar.org/graph/v1/` |
| DOI 查找 | Crossref | `https://api.crossref.org/works` |

### 範例:每日醫學文獻 brief

對 bot 送:

````
幫我建一個 CRON 任務:
- 名稱: daily-medical-brief
- 排程: 0 8 * * * (每天 8:00)
- 傳送至: origin
- 提示詞:

用 PubMed E-utilities API (esearch + efetch) 搜尋過去 7 天我感興趣領域的最新文獻:
- 查詢 1: "Alzheimer Disease"[MeSH] AND "last 7 days"[PDat], retmax=10
- 查詢 2: ("N Engl J Med"[Journal] OR "Lancet"[Journal]) AND "kidney"[TIAB] AND "last 7 days"[PDat], retmax=10

各挑 3 篇,每篇格式:
▸ 標題 (期刊, 年份)
▸ 作者: 第一+通訊
▸ 摘要: 200 字繁體中文
▸ 💡 跟我相關性: 1 句
▸ 📎 PMID + DOI

如果 PubMed API 失敗,直接給錯誤訊息,**不要編造** PMID 或論文標題。
````

把領域關鍵字換成你的就好。

---

## Hermes 心智模型口訣

> ### 對話是主軸,Dashboard 是儀表板
>
> - 想做什麼事 → 先在 Telegram 跟 bot 講
> - Bot 會自己呼叫工具(cronjob、kanban、tools 等)
> - Dashboard 只用來「看狀態 + 第一次配置」,**不適合**日常操作
>
> **經驗法則**:Dashboard 點按鈕點到第三次還沒成功,**停下來打開 Telegram 用講的**。

---

## 想深入了解

- 完整 20 個踩坑詳細紀錄:`Hermes Agent 安裝與部署踩坑全紀錄.md`(同 repo)
- Hermes 官方 GitHub:https://github.com/NousResearch/hermes-agent
- Hermes 官方文件:https://hermes-agent.nousresearch.com/docs/
- Nous Research portal:https://portal.nousresearch.com(管理 API 用量)

---

## 致謝與授權

本懶人包整理自 2026-05-26 親身安裝 Hermes Agent v0.14.0 的踩坑經驗。所有指令在當天確認可用。

若之後版本更新導致某些步驟失效,歡迎 PR 修正。

**License**: MIT(自由使用、修改、再散布)

---

**更新日誌**:
- 2026-05-26 初版,涵蓋 Hermes 0.14.0 + Gemini 3 Flash + Telegram + PubMed/arxiv API 工作流
