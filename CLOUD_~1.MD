# Cloud_Skill 的製作經驗

> 製作日期:2026-05-18
> 製作者:Kwo-Ta(kwotachu@gmail.com)
> 主題:在 Cowork 上設計、實作、部署一個整合多 MCP 來源的個人化每日工作 skill(`kwota-daily-stack`),並把排程串起來

---

## 一、起點與範圍演進(這條路怎麼走偏的,又怎麼走回來)

### 0.0 一開始的請求
「我想設立一個 scheduled task。」——非常單純的一句話。

### 0.1 第一輪 AskUserQuestion 收斂
透過 4 個多選題收斂出:**每天早上 7:00 跑 Gmail 摘要,存成 Markdown 檔**。
這時的設計範圍極小:單一來源(Gmail)、單一輸出(Markdown)、本機儲存。

### 0.2 第二輪追問(時間 + 重點)
又問了 2 題,確認 **07:00 起跑 + 「快速摘要 + 行動項目」型輸出**。
這時排程已經建好(`daily-work-briefing`,cron `0 7 * * *`)。

### 0.3 範圍爆炸:從 Gmail briefing → 五源工作中心
緊接著使用者貼了一段大幅擴展的需求:
1. 整合 Email + Calendar 變每日工作行事曆
2. 整理 Google Scholar 訂閱
3. 安排讀書計劃 + NotebookLM 最近 3 個 notebook 摘要 + 後續研究方向

→ 我**沒有**直接照單實作,而是先做能力盤點:Calendar、Gmail、Scholar(走 Gmail alerts)可行,**NotebookLM 沒有 connector**——只能誠實標 ⚠️,並提供 3 個替代方案讓使用者選。

> **教訓 1**:當需求跨多個工具時,**先做工具能力盤點再回應**,不要假裝可以做到後來才補釘子。

### 0.4 使用者拍板:NotebookLM 在另一台電腦處理
使用者表示「另一台電腦已安裝 NotebookLM MCP」,所以這台只跑能跑的。排程更新成 4 個來源 + 依空檔排讀書計劃。

### 0.5 再次擴張:加 AI 新聞 + 整合成獨立 skill
新請求:
- 加上「主流科技媒體 AI 新聞搜尋」
- 把 email-assistant + article-writer + dashboard-builder **整合成一個 skill**
- 強制 NotebookLM MCP 為 prerequisite(沒有就不跑)
- 要能搬到另一台電腦

### 0.6 最後一次校正:輸出位置改 Obsidian 第二大腦
要求每日 dashboard 寫到 Google Drive `/Second Brain/知識庫/` 變第二大腦的累積。
這讓 Google Drive MCP 也升級為 **prerequisite**(因為核心需求是「進第二大腦」,不能 fallback 到只寫本地)。

---

## 二、最終產出

### A. 新 skill:`kwota-daily-stack`
五個資料來源 → 一份單檔 HTML dashboard → 寫進 Obsidian 第二大腦。

| 區塊 | 來源 | 處理邏輯 |
|------|------|---------|
| 今日行程 | Google Calendar MCP | 抽事件 + 識別 ≥ 60 分鐘空檔 |
| Email Triage | Gmail MCP(過去 24h 未讀) | email-assistant 的四象限分類,**不自動草擬** |
| Scholar 文獻精選 | Gmail MCP(`from:scholaralerts-noreply`) | 挑 3–5 篇 + 註明理由 |
| AI 新聞 | WebSearch + WebFetch(四家媒體) | TechCrunch、The Verge、Ars Technica、MIT Tech Review |
| NotebookLM 摘要 | NotebookLM MCP | 最近 3 個 notebook + 後續研究方向 |
| 讀書計劃 | 依 Calendar 空檔派工 | 大空檔讀文獻,中空檔回信,小空檔 ack |

### B. 排程:`daily-work-briefing`(每天 07:00)
排程本身**不重複實作邏輯**——只負責呼叫 `kwota-daily-stack` skill。這是 separation of concerns:邏輯變動只改 skill,不需改排程。

### C. 雙 prerequisite(硬性,任一缺失就 halt)
- **NotebookLM MCP**:不能跳過,因為它是 stack 的研究心臟
- **Google Drive MCP**:不能 fallback 寫本地,因為「進第二大腦」是核心需求

---

## 三、踩過的坑(實際遇到的工具/環境問題)

### 坑 1:`Write` 工具不會自動建立 parent directory
**現象**:嘗試 `Write` 到 `outputs/kwota-daily-stack/SKILL.md`,失敗訊息「outside this session's connected folders」——其實是子資料夾不存在。
**繞過**:改用扁平命名 `kwota-daily-stack-SKILL.md` 寫到 outputs 根目錄,再附 INSTALL.md 說明使用者自己把它放進對的子資料夾。
**教訓**:Write tool 沒有 `mkdir -p` 語意。要嘛先用 bash `mkdir`,要嘛改檔名規避。

### 坑 2:Bash workspace 偶發無法啟動
**現象**:`mcp__workspace__bash` 回報 `Workspace unavailable. The isolated Linux environment failed to start (Request error: net::ERR_QUIC_PROTOCOL_ERROR)`。
**繞過**:改用 file tools(Read/Write/Edit),完全不依賴 bash。
**教訓**:不要把 bash 當基礎設施。能用 file tool 完成的事就用 file tool。

### 坑 3:Skill 安裝位置是 Cowork 寫死的,不在 connected folders 裡
**現象**:想把 SKILL.md 直接寫到 `skills-plugin/.../skills/kwota-daily-stack/SKILL.md`,Write 拒絕:「outside this session's connected folders」。
**繞過**:檔案先寫到 outputs,附 INSTALL.md 教使用者手動拷過去 + 重啟 Cowork。
**教訓**:**Skill 不能用 chat 內的 LLM 自動部署**(即便它寫得出來),因為 sandbox 不允許寫入應用內部路徑。長期解法是 Cowork 自家做「skill install」UI/工具,讓 LLM 可以呼叫部署。

### 坑 4:Drive `/一個知識庫/` 找不到,實際路徑是 `/Second Brain/知識庫/`
**現象**:第一次 `search_files title = '一個知識庫'` 回空。
**繞過**:用 `title contains '知識庫'` 跟 `title contains 'Second Brain'` 廣搜,發現真實結構是 `/Second Brain/知識庫/`(parent-child 關係)。
**教訓**:**使用者口頭描述的資料夾路徑常與實際 Drive 結構不一致**(口語會加「一個」、會省略 parent 階層、會混用中英文)。永遠先 fuzzy search 確認真實路徑,不要直接 hardcode。

### 坑 5:GitHub MCP 不在 mcp-registry 結果裡
**現象**:`search_mcp_registry keywords=["github","git","repository"]` 回傳 10 個全不相關的金融/雲端 MCP。
**繞過**:改走 `plugins__search_plugins`,因為 GitHub 整合在 Cowork 是 plugin 而非 raw MCP。
**教訓**:同樣是「連外部服務」,registry 跟 plugins 是**兩套不同的目錄**,得兩邊都查。

### 坑 6:設計上的 trade-off — 強制 prerequisite vs 跨機可用性
**衝突**:使用者要求「沒有 NotebookLM MCP 就不跑」,但這台電腦沒有 NotebookLM MCP。
**結果**:這台電腦上每天 07:00 排程會跑到 skill prereq check 然後 halt,留下「halted: NotebookLM MCP not detected」訊息。
**設計選擇**:**遵循使用者明示**(halt),但在最終訊息裡**明確提醒這個 trade-off**,並提供「另建 lite 版排程」的選項。
**教訓**:當使用者明確表達設計選擇,即便會在當下產生不便,也應該照辦——但**主動把後果說清楚**,讓使用者有機會調整。

### 坑 7:範圍持續擴張時,**用 task list 持續更新而不是重寫**
**現象**:從一個 scheduled task → 五源 stack → 新 skill → 加 AI 新聞 → 改 output 路徑,範圍一路放大。
**做法**:每次擴張時 `TaskCreate` 新任務 + `TaskUpdate` 標進度,不重寫前面的工作。SKILL.md 也用 `Edit` 增量改,不重寫整份。
**教訓**:**增量編輯 > 重寫**,尤其在多輪需求變更時。Edit 工具的精準 `old_string / new_string` 替換比 Write 重寫安全。

### 坑 8:Session 內已知資訊 ≠ 重新讀 transcript
**現象**:在做 Cloud_Skill 經驗總結時,本來打算用 `session_info__read_transcript` 拉完整對話。
**判斷**:對話完全在這個 session 內,我自己就記得全部上下文。重新讀 transcript 只會把同樣內容塞回 context window,徒增 token 成本。
**教訓**:**不要無腦工具呼叫**——能靠自己 context 寫的,就直接寫。tool call 不是越多越好。

---

## 四、設計上學到的東西(可推廣到其他 skill 的原則)

### 4.1 整合 skill 不是「複製貼上」三個來源 skill
`kwota-daily-stack` **引用**了 email-assistant、article-writer、dashboard-builder 的**精神與鐵則**(零虛擬資料、絕不送信、outline-then-expand),但**不複製**它們的全部邏輯——它是個「指揮官」,負責協調流程與輸出格式。
單一信件回覆 → 仍呼叫 email-assistant。
單一研究主題展開 → 仍呼叫 article-writer。
這保持了 skill 之間的責任邊界。

### 4.2 Prerequisite check 該在 Step 0 完成,不要散在後面
用 hard prereq 把所有環境依賴在最前面驗證完,而非各 Step 自己處理失敗。這讓:
- 失敗訊息明確(知道是 prereq 沒過,而不是執行到一半才崩)
- 使用者修復時知道要裝什麼
- skill 邏輯本體可以假設環境完整,不必處處 if-else

### 4.3 排程的 prompt 應該「呼叫 skill」而非「重新實作邏輯」
排程的 prompt 寫越少越好——只負責**入口**(呼叫哪個 skill、用什麼輸出位置),不重複 skill 內的邏輯。
這樣 skill 升級時不用改排程,排程改時間/頻率也不需動 skill。

### 4.4 雙寫策略:本機暫存 + 雲端歸檔
本機暫存讓 `present_files` 能立刻給使用者開啟,雲端歸檔(Drive)做長期累積。
兩個位置各有用途,不衝突——一份檔案的兩個生命週期。

### 4.5 「絕不送信」、「零虛擬資料」這類鐵則要明示為 **🚨 鐵則**
不能只寫在隨手的 note 裡。它們應該在 SKILL.md **最頂端**用顯眼格式呈現,因為它們是**安全/信任邊界**——一旦違反就會傷害到使用者。

### 4.6 反 LLM 陳腐用詞清單是 skill 的隱形品質保證
原本 email-assistant 跟 dashboard-builder 各自的「禁用清單」(`I hope this email finds you well`、裝飾性 🚀✨、`AI Insights` 區塊...)在新 skill 裡**繼承並重申**——這是維持 skill 產出品質一致的關鍵。

---

## 五、最終成品清單

| 物件 | 位置 | 用途 |
|------|------|------|
| `kwota-daily-stack-SKILL.md` | Cowork outputs | Skill 本體,使用者部署到 `skills/kwota-daily-stack/SKILL.md` |
| `kwota-daily-stack-INSTALL.md` | Cowork outputs | 跨機安裝 + MCP 依賴 + Drive 路徑說明 |
| `daily-work-briefing` 排程 | Cowork Scheduled(cron `0 7 * * *`) | 每天 07:00 呼叫 skill |
| `Cloud_Skill 的製作經驗.md`(本文件) | Drive `/Second Brain/` + 本機 + GitHub | 製作過程的反思紀錄 |

---

## 六、給未來自己的提醒

1. **需求收斂在前**:任何 ≥ 3 步驟的任務都先 AskUserQuestion,避免做完才發現方向錯
2. **工具能力盤點在前**:跨工具任務先確認哪些 MCP 可用,缺的就誠實標 ⚠️ 並提替代方案
3. **rule 寫在最上面**:🚨 鐵則永遠在 SKILL.md 第一段
4. **增量 > 重寫**:多輪需求變更時用 Edit,不要重寫整檔
5. **本機 + 雲端雙寫**:工具產出需要長期累積時,雙寫是更安全的設計
6. **prerequisite 設計選擇要清楚溝通**:hard halt 跟 graceful degrade 各有適用場景,讓使用者明示偏好
7. **task list 是給使用者看的 UI,不是給 Claude 用的便條紙**:Cowork 的 task widget 會渲染,所以 TaskCreate 該寫得讓使用者一眼看懂進度
8. **不要假裝有 NotebookLM/GitHub MCP**:沒有就說沒有,給替代路徑

---

*本文件記錄了 2026-05-18 一場約 90 分鐘的 Cowork 對話。從「設一個 scheduled task」一句話起,經過 6 次範圍擴張,最終產出一個整合 5 來源 + 雙 prereq 的個人化 skill,並完整部署到排程。*
