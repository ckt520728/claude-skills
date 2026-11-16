# 專案收尾：糖尿病智慧照護網 v2（桌面 Agentic AI + MCP）踩過的坑

**專案：** 2026 Smart Diabetes Care Network v2（院內三層混合架構）
**日期：** 2026-11-17（單一工作階段）
**環境：** Windows 11、Git Bash + PowerShell 5.1、Python 3.11（uv）、FastAPI、SQLite（放在 Google Drive G:）、Claude in Chrome、headless Chrome（CDP）、Claude Desktop（Microsoft Store 版）
**產出：**
- GitHub `ckt520728/2026-open-code` PR #1，已合併至 master：`projects/smart-dm-care`
- 新技能 `patient-care-network/`，位於 `ckt520728/claude-skills`
- Claude Desktop 已登錄 MCP（stdio bridge）

> 本文只記錄方法與教訓。沒有金鑰，所有病人資料都是合成資料。

---

## 一句話總結

**臨床 AI 的價值，不在讓 LLM 做更多事，而在讓它只能做「讀、解釋、起草」。** 數字由確定性程式計算，送出則需要臨床人員確認。真正花時間的地方是：護欄的邊界、在 Windows 雲端硬碟上的效能，以及 MCP 的連線細節。

## 做了什麼（v1 → v2）

| 區塊 | 內容 | 證據 |
|---|---|---|
| 病人端（LINE） | CGM 串流 API（<54 → Rule of 15、護理站紅旗卡、15 分鐘覆測）、主動關懷排程（醫師核准 × 臨床啟用 × 病人同意 × 06–21 時）、語音記餐（STT → 台灣食物代換表）、Flex、Rich menu、營養師覆核佇列 | 實測：串流 72→60→48 觸發 `level2_hypo` 與全部後續動作 |
| 臨床端 | SCORE2-Diabetes 與 WATCH-DM 並列、五維度照護輪、AGP、餐後 CGM 反應、6 代理門診前摘要（醫師簽署）、FHIR RiskAssessment 匯出、網絡、護理站與主動關懷頁 | 瀏覽器 1280 px 實際操作；390×844 下七頁皆無水平捲動 |
| RAG／LLM Wiki 安全層 | 三環知識庫（guideline／wiki）、混合檢索（詞彙 ＋ 中文二元字 TF-IDF，零新依賴）、醫師驗證閘門、確定性護欄 | 8 位病人自動摘要的護欄結果全部 `pass`；「增加胰島素 4 單位」被 `blocked` |
| MCP | 23 工具、3 個 prompts、`wiki://` 資源、2 個 MCP Apps `ui://` 面板 | 線上 initialize → 23／3／2；無 token 回 401 |
| 測試 | 48 passed（原有 14 項 ＋ 新增 34 項） | `pytest -q` |

使用者決策（寫成 ADR 0009–0012）：
- 自動送出只限兩種：安全硬規則與已核准範本；
- SCORE2 用 high 區，並標示「台灣未驗證」；
- 同時提供 MCP App 面板與網頁儀表板。

---

## 踩過的坑與解法

### 資料來源

1. **私人 GitHub 用 web fetch 會回 404。** 改用 `gh api .../git/trees/master?recursive=1`。結果發現所謂「初步程式碼」與本機版本 byte 完全相同，所以規劃前先比對檔案大小，省掉一輪合併分析。
2. **NotebookLM 回答有 51 KB，在 cp950 終端印不出來。** 讀存檔的 JSON，加上 `PYTHONIOENCODING=utf-8` 再印。
3. **筆記中的程式碼有錯。** KFRE 用 eGFR/10、SSE 舊 API 等，只能當設計參考。
4. **公式不能只憑記憶。** SCORE2-Diabetes 的係數用獨立實作（R 套件 RiskScorescvd）逐項比對，並把 worked example（8.4%）寫成測試釘住。
5. **台灣不在 SCORE2 校正區。** 區域做成可設定，每個結果都標示區域與「台灣未驗證」。

### 計算與測試

6. **測試失敗時，先懷疑測試本身。** 餐後反應測試把餐前 30 分鐘的值當基線，但實際上餐點時刻的讀值才是正確基線。改的是測試的期望值，引擎不動。
7. **時區混用。** CGM 裝置送的是本地時間（naive），伺服器事件是 UTC。統一用 `to_local_naive()` 處理，AGP 分時段與餐點配對才會正確。
8. **吸菸狀態不明時不補值。** 改用條件表的 0/1 列來記錄；沒有這一列就代表未知，SCORE2 回 `not_calculable`。

### 護欄（最容易「看起來對」但其實錯）

9. **斷句把引用切離主張。** 「…一次。[wiki:x]」會被切成兩句。規則改成：標點後面緊接 `[wiki:` 就不斷句，「；」也不斷。
10. **標題被當成「未引用的主張」。** `# ...` 與單獨一行的 `【...】` 都略過。
11. **數字比對太寬鬆。** 「eGFR 31」竟然通過，因為某一餐的升幅剛好是 31.2。改成三件事：
    - 依標籤比對對應欄位；
    - 依草稿數字本身的精度比對；
    - 原始歷史（CGM 序列、AGP 時段、檢驗史、餐點）不能當成數字依據。
12. **時間被當成數字。** 「12:45」產生一個查無依據的「45」。比對前先移除時間與日期。
13. **系統自己產生的摘要引用了 draft 頁面**，結果被自己的護欄判為 needs_review。自動產生的內容只能引用已驗證的頁面。
14. **示範用的語音辨識被自動接受。** 只要是模擬的 adapter（mode 或 stt_mode 為 demo），信心值一律封頂，一定轉給人工覆核。

### MCP

15. **HTTP 421 "Invalid Host header"。** MCP SDK 的 DNS-rebinding 防護預設只允許 localhost，所以 TestClient（testserver）與院內區網的 agent 都會被擋。用 `MCP_ALLOWED_HOSTS` 與 `MCP_ALLOWED_ORIGINS` 設定允許名單，防護保持開啟。
16. **session manager 每個 process 只能啟動一次。** 兩個測試檔各自建立 session 層級的 TestClient 會失敗，所以把 fixture 移到 `conftest.py` 共用。
17. **`_audit_mcp(action, chart_number=...)` 發生參數名稱衝突**（"got multiple values"）。位置參數改名為 `patient_ref`。
18. **工具回傳 dict 時，常常沒有 `structuredContent`。** 面板與客戶端都要退回去解析 `content[0].text`。
19. **Microsoft Store 版的 Claude Desktop 不讀 `%APPDATA%\Claude`。** 實際路徑是 `%LOCALAPPDATA%\Packages\Claude_<id>\LocalCache\Roaming\Claude\claude_desktop_config.json`，可在 `main.log` 搜尋 "Reading claude_desktop_config.json from" 確認。`Claude-3p` 是另一個 profile，不要改錯。
20. **Claude Desktop 只能用 stdio 啟動本機 server。** 用 100 行的 httpx bridge 轉接，不必下載 npm 套件，伺服器重啟後（回 404）也會自動重新 initialize。

### 效能與平台

21. **SQLite 放在 Google Drive（G:）上，每次連線約 60 ms。** 原本 `/api/patients` 要 5.5 秒、測試跑 43 秒。改成每個 thread 快取一條連線，reset 前先 `close_all()`（Windows 無法刪除開啟中的檔案），結果降到 1 秒以內、測試 14 秒。
22. **WAL 不需要每次連線都設定。** WAL 會寫在資料庫檔案裡，只要在 `init_db` 設一次。
23. **Git Bash heredoc 遇到中文加引號會壞掉**（unexpected EOF），而且可能已經執行了一半。改用編輯工具寫檔，重試之前先確認哪些檔案已經寫入。
24. **`uv run --with` 讀 `.pth` 時發生 cp950 解碼崩潰。** 臨時需要的套件改用 `pip install --target <scratch>/libs`，再設 `PYTHONPATH`，不會汙染專案的 venv。
25. **Windows 檔案複製進 LF 換行的 repo 後，所有檔案都顯示被修改。** 先設 `git config core.autocrlf true` 再 `git add`。

### UI 驗證

26. **瀏覽器視窗無法縮到 390 px**（視窗是最大化狀態）；iframe 也被自家 CSP 的 `frame-ancestors 'none'` 擋下。改用 headless Chrome 搭配 CDP 的 `Emulation.setDeviceMetricsOverride`，逐頁檢查 `scrollWidth == clientWidth` 並存截圖。
27. **固定等 2.5 秒會拍到上一頁。** 雲端硬碟太慢，應該等待頁面特定內容出現，或先把延遲修好。
28. **手機版 CSS `span:last-child{display:none}`** 在加了徽章 span 之後失效，標籤又出現了。改用有語意的選擇器 `span[data-i18n]`。
29. **擴充既有的 vanilla JS 時，用 hook 而不是重寫。** 在 `app.js` 加三個 hook，另外寫 `app-v2.js`，v1 的測試全部維持綠燈。

### 營運

30. **由 agent session 啟動的 uvicorn，會隨 session 結束而停止**；in-process 排程器在多個 worker 下會重複發送。要寫清楚手動啟動的指令，並且只用單一 worker，或把排程器移到獨立的 process。

---

## 可重用原則

- **先寫好契約（AGENTS.md 硬規則 ＋ ADR）再寫程式。** 每個使用者決策都要有一份 ADR。
- **單一事實來源：** REST、MCP、UI 都呼叫同一個 `build_assessment()`。
- **缺值就是待辦，不是零；** 不補值，不做的事也要誠實標示（眼睛風險是「優先度」而非機率、KFRE 只在 eGFR<60 時報告、SCORE2 標示區域）。
- **自動送出的理由用白名單寫死在程式碼裡**，其他理由一律丟出 `PermissionError`，並且要有測試確認「未核准就不會送」。
- **用系統自己的輸出測試護欄：** 每位病人自動產生的摘要都必須通過自己的護欄。
- **驗證分三層：** 單元測試、線上實際串流與 MCP 握手、瀏覽器桌機版加 CDP 手機版。

## 下一步

- 在 Claude Desktop 重啟後確認 `ui://` 面板能在對話中顯示。
- 請醫師驗證兩份 draft wiki 頁面（台灣指引摘要、營養估算限制）。
- 用台灣在地世代資料校正 SCORE2。
- 評估、評估 CSV 匯入、吸菸狀態匯入。
- 上線前移除 CGM 模擬按鈕。
- 改用 SSO 與 PostgreSQL。

## 相關筆記

- `2026-11-09_跨平台Agent串接_Lessons_and_Pitfalls.md`（多平台 agent）
- `2026-07-18 Claude Code MCP 安裝紀錄 — GitHub／Firebase／NotebookLM 連接與踩坑.md`
- 技能：`claude-skills/patient-care-network/`（SKILL.md ＋ references/pitfalls.md）
