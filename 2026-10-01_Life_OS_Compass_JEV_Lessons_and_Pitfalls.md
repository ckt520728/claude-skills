# 專案收尾 — 踩過的坑與可重用做法

**專案：** 2026 Life OS — 照 Compass（Mike Schmitz 的系統、Daniel Agrici 的 Obsidian 模板）結構，蓋在既有第二大腦（694 篇筆記）上的 Life OS；GTD 的分類判斷交給 `jev-engineering` 技能的本機決策層
**日期：** 2026-09-29 ～ 2026-10-01（五個工作階段；本文重點是第 5 階段的「修正」）
**成果：** `life-os/`：stdlib-only Python 套件（含原封複製、雜湊鎖定的 jev 1.1.0）、8 個儀表板、12 個 DataviewJS view、5 個模板、12 則 prompt、2 個 QuickAdd 腳本、14 章使用手冊；`checks.sh` 70 項、行為測試 124 項全過
**環境：** Windows 11、Git Bash + PowerShell 5.1、Python 3.9.12、Node 25、Obsidian（桌機＋筆電，經 Google Drive 同步）、Claude Code

> **驗證聲明：** Python 端全部測過；Obsidian 端（12 個 view、2 個 QuickAdd 腳本）只通過 `node --check`
> 語法檢查。使用者在筆電上完成 QuickAdd 設定並評分了第一晚，但截至收工，這些變更**尚未同步到桌機**，
> 所以「在真實 app 裡跑過」這件事**還沒被驗證**。

---

## 零、一句話總結

| # | 教訓 | 適用範圍 |
|---|---|---|
| 1 | **使用者指名的技能／repo，要真的 import／clone 來用，不要照著描述自己再做一個。** 前四個階段自寫了一份「長得像 JEV」的決策層，違反技能自己 7 條規則中的 3 條，而且因為從沒 import 過，技能自帶的驗證完全抓不到 | 任何「用 X 技能／參考 Y repo」的請求 |
| 2 | **抓下來的「摘要」會把事實講反。** WebFetch 回的是摘要，據此「更正」文件說上游沒有 30 天規則——完整 `git clone` 後，`Guide/11 Build Order.md` 明明白白寫著 | 任何靠 fetch 判斷「上游有沒有 X」 |
| 3 | **部署腳本每次都覆寫全部檔案，包括使用者被叫去寫字的那個檔案。** 第一筆真實收件會在下一次 deploy 時消失 | 任何「工作區 → 產品」的單向部署 |

三句的共同點：**沒親眼看到真東西之前，不要相信任何關於它的二手陳述——包括自己上一個階段寫下的。**

---

## 一、「照描述做」與「真的用」的差距（這節最貴）

### 1. 自寫的決策層，違反了它要模仿的技能

**症狀：** 使用者：「Claude 沒有用我的 JEV Engineering 技能。」檢查後屬實：`lifeos/decide.py` + `calibrate.py` + `jev_stub.py` 是一套平行實作，API 是 `backend.choice(state, qid, options, "一行說明")`。

**用技能自己的 7 條規則對照：**
- 規則 1（意義寫在 criteria 裡）：選項只有名字，沒有描述文字。
- 規則 3（描述情境，不要用數字）：`Score(5)` 只給層數沒有描述——真的 `jev.Score` 會直接 `raise QuestionSpecError`。
- 規則 5（一次呼叫問完）：一則收件分四次呼叫。

**修法：** `scripts/sync_jev.py` 把技能的 `assets/jev/` **原封不動**複製到 `lifeos/jev/`，每個檔案的 SHA-256 寫進 `JEV_VENDOR.json`；`checks.sh` 在有人手改複本時失敗；測試斷言舊的 `decide.py` 等三個檔案**保持刪除**。`gtd.py` 改寫成真正的 `jev.Choice/Score/Noul`，一次 `jev.decide()`，用 `jev.gate()` 設閘。

**要點：** 「依賴被繞過」本身要能讓建置失敗。否則下一個階段又會覺得「自己寫比較快」。

### 2. 一個摘要害兩個階段：上游「沒有」的規則其實存在

**症狀：** 第 2 階段 fetch Compass repo，得到「沒有 30 天分層規則」，於是把 CLAUDE.md、README、設定檔全部「更正」為「這條規則是二手筆記編的」。

**實際：** 第 5 階段 `git clone --depth 1`，`Guide/11 Build Order.md` 寫著 1–30 / 31–60 / 61–90 / 91–120 / 121–150 天的分層，還有「上一層一致性低於 80% 就不要加下一層」。`Guide/01 Principles.md` §10 直接引用 Schmitz。

**原因：** WebFetch 回傳的是模型摘要，不是檔案；摘要裡「沒提到」被讀成「不存在」。

**修法：** 完整 clone，讀原檔。把正確的 Build Order 與 80% 規則寫成 `unlock.py`（Python）與 `gate.js`（Obsidian），`checks.sh` 比對兩邊常數，飄移即失敗。

**要點：** 「我沒找到」≠「不存在」（HarnessOS 那次也踩過一樣的坑）。要判斷「有沒有」，用 `git clone` + `grep`，不要用 fetch。

### 3. 叫使用者按了四個階段的熱鍵，其實什麼都沒綁

**症狀：** 每份 handoff 的第一項都是「請使用者按一次 Ctrl+Shift+Q」，四個階段都沒結果。

**實際：** `.obsidian/plugins/quickadd/data.json` 裡 **0 個 choice**。熱鍵從來沒綁到任何東西。

**修法：** 使用手冊第 1 章與「設定清單」逐步教建立兩個 Macro（名稱一字不差，因為儀表板按鈕用名稱找它們）。

**要點：** 要求使用者做某件事之前，先去讀設定檔確認前置條件真的存在。

---

## 二、資料安全

### 4. 部署會吃掉使用者的收件匣

**症狀：** 舊 `deploy.sh` 把 `vault-src/**` 每次全量複製。`GTD/收件匣.md` 也在其中——而手冊叫使用者把收件寫進這個檔案。

**修法：** 三種檔案、三種規則：
- **code**（儀表板、views、prompts、手冊）：每次覆寫。
- **seed**（設定檔、人生主題、核心價值、理想週、任務總表、看板）：第一次建立；之後只在 vault 那份的雜湊**仍在** `deploy-ledger.tsv`（＝證明使用者沒動過）時才升級，否則印出 `kept (yours)`。
- **retired**（不再出貨的舊檔）：同樣只在雜湊證明未被修改時才刪。

`checks.sh` 有一個拋棄式 vault 測試：部署 → 改兩個 seed → 再部署 → 斷言兩個都被保留、一字不差。

### 5. `${2#$VAULT/}` 把路徑當成 glob

**症狀：** 拋棄式 vault 測試在 Windows 暫存路徑下，把 52 個檔案全部回報成「你改過」。

**原因：** bash 的 `${var#pattern}` 裡，未加引號的 `$VAULT` 是 **pattern**；`C:\Users\...` 的反斜線被當成跳脫字元，前綴剝不掉。真正的 vault 路徑剛好沒有反斜線，所以正式部署沒出事——純屬運氣。

**修法：** `${2#"$VAULT"/}`。

**要點：** 這個 bug 只有「用不同形狀的路徑跑一次」才看得到。安全保證要用測試釘住，不要只靠正式環境沒出事。

---

## 三、JEV 決策層的細節

### 6. Noul 沒有信心值，本機 provider 也不校準它

`jev` 規格明定 Noul 只回傳機率、沒有 `confidence`；技能的 `local` provider 只校準 Choice/Score。若直接用機率當信心，0.88 的 Noul 會在校準還是冷的時候就自動歸檔（第 3 階段已經踩過一次）。
**修法：** `layer.py` 用**同一個** `Calibrator` 把所有答案從原始分數重新校準；Noul 的原始分數是「決斷度」`|p−0.5|×2`。並在呼叫 provider 時暫時移除 `JEV_CALIBRATION` 環境變數，避免兩個校準檔各說各話。

### 7. 平坦的 Score 會偽裝成一個建議

沒有任何層級的字詞命中時，機率均勻分布，期望值剛好落在中間（5 級的第 2 級「這週內」），看起來像真的判斷。
**修法：** 原始信心為 0 時不提出建議，明說「沒有任何層級的 criteria 命中」。

### 8. Criteria 就是詞庫——也就是 bug 的所在

- Clippings 的描述寫了 `http` 沒寫 `https`，測試 `https://example.com/paper` 落到 `other`。
- 中文以單字＋雙字切詞，單字太常見：「張醫師」的「醫」把收件拉向「健康」領域；知識庫重複檢查一開始也因為單字重疊幾乎全部誤報（改成只算 ≥2 字的詞）。

**要點：** 準確度不夠時**改 criteria 文字，不要降門檻**。校準會讓不準的頻帶繼續問人，這才是安全的原因。

### 9. 問一個決策層根本答不了的問題

「知識庫是否已經有這一頁？」原本是 Noul，但本機 provider 讀不到 vault。改成 [C]：拿收件與 `知識庫/index.md` 每一行比對共同詞，命中就交給人。

### 10. 有些標籤永遠不該自動歸檔

per-label 門檻：`project` 0.85、`知識庫`／`Clippings`／`other` 設為 1.01（不可能達到）。知識庫新增頁面還要更新 index.md 與 log.md，這件事沒有自動化之前，就不該自動歸檔。

---

## 四、Windows／Shell

### 11. Heredoc 把 `\\n` 變成真的換行

Git Bash 的 heredoc 傳給 Python 時，反斜線被吃掉一層：JS 的 `"\n"` 變成字串裡的真換行 → `quicklinks.js` 語法錯誤；另一次中文 heredoc 直接 `Non-UTF-8 code`。
**修法：** 含反斜線或大量中文的產生器腳本，用 Write 工具寫成檔案再執行；必要時用 `chr(92)` 組出反斜線。

### 12. cp950 主控台印不出 emoji

`UnicodeEncodeError: 'cp950' codec can't encode '\U0001f3c6'`。資料本身沒問題，是主控台。`PYTHONIOENCODING=utf-8` 或 `sys.stdout.reconfigure(encoding="utf-8")`。

### 13. Dataview view 用頂層 await，`node --check` 會誤報

包成 `(async () => { ... })();` 再檢查，等同 Dataview 實際執行的方式。

### 14. CRLF 讓 diff 全部「不同」

比對 repo 與本機技能時 20 個檔案顯示不同；`diff --strip-trailing-cr` 後只剩 7 個真正的變更。

---

## 五、驗證要對真東西

### 15. 使用者說「儀表板出來了」，但磁碟和 app 都說沒有

讀設定檔：QuickAdd 0 個 choice、Dataview 不在啟用清單。再用 Local REST API 查**正在執行的** Obsidian 的指令清單（224 個）：沒有任何 `dataview:` 或 `quickadd:choice`。原因是使用者在**筆電**上設定，Google Drive 還沒同步。
**要點：** 使用者回報與證據不一致時，直接說，並查「正在執行的 app」而不是只查檔案。等同步的背景輪詢後來因系統記憶體不足被終止——不自動重啟，交給使用者決定。

### 16. 公開 repo 裡的技能比本機舊

Life OS 依賴的 `local` provider 與 `calibration.py` 只存在於 D 槽的技能，GitHub 上的 `jev-engineering` 還是舊版。如果只推 Life OS，從 repo clone 的人跑不起來。這次一併更新技能。

---

## 六、設計上的取捨

- **不裝 Templater／Periodic Notes／Tasks：** 舊日記模板就是死在 Templater 沒裝。改由 `quicklinks.js` 用模板自己建週記、季記、退修；Dataview 讀 Tasks 的 emoji 格式。
- **退修模板寫死了 `wheel_*`：** 違反 SSOT。改成建檔時從設定檔填入。
- **GTD 自動歸檔從第 31 天移到第 91 天**（上游 Tasks 層），但影子模式標註從第 1 天就開著——鎖住的三個月就是訓練期。
- **只量測日記層的一致性**作為所有後續層的 80% 門檻，是對上游規則的刻意窄化，已寫明。

---

## 七、可重用做法

1. **Vendor + 雜湊清單 + 「被繞過就失敗」的檢查**：確保依賴真的被用、而且沒被私改。
2. **code / seed / retired 三分法 + 出貨雜湊帳本**：任何會碰使用者檔案的部署都適用。
3. **[C]/[D]/[G] 分欄規則**：錯了算術抓得到→程式；答案是固定選項→決策層；答案是人要讀的文字→LLM。所有 prompt 的數字都由 `lifeos_status.py` 算好再給模型。
4. **兩邊實作的常數做 parity check**（Python `unlock.py` ↔ JS `gate.js`）。

---

## 八、還沒做完

- Obsidian 端在真實 app 裡跑一次（等筆電同步）：讀 console，確認 12 個 view、`nightly.js`、`capture.js`。
- 第一晚評分的資料是否正確寫入 frontmatter、臨床段落是否只留下兩個數字。
- 累積約 20 則真實收件後跑 `python scripts/triage.py --report`，依同意率修改 criteria。
- 第 91 天（2026-12-28）前：把決策「套用」到 vault 的寫入路徑。
