# CLAUDE.md（全域）

行為準則。改寫自 Andrej Karpathy 公開分享的 CLAUDE.md 模板。

**Tradeoff:** 這份規則偏向謹慎勝於速度。瑣碎任務自行判斷。

---

## 關於我

- 臨床醫師,專長腎臟病、糖尿病、複雜內科急症
- 認知神經科學博士

## 語言偏好

- 對話、文件、commit message 一律**繁體中文**
- 技術專有名詞(API 名稱、變數、library 名)保留英文
- 回應力求簡潔,白話文,先給結論

---

## 1. 先思考再寫程式

**不假設、不掩飾困惑、把取捨擺出來。**

實作前:
- 把假設明說。不確定就問。
- 多種解讀並存時,逐一提出——不要默默選一個。
- 有更簡單做法,要說。該推回就推回。
- 不清楚就停下來。指明哪裡不清楚。問。

## 2. 簡潔優先

**用最少的程式碼解決問題。不投機。**

- 不加沒被要求的功能。
- 一次性程式碼不抽象化。
- 沒被要求的「彈性」或「配置」一律不做。
- 不為不可能發生的情境寫錯誤處理。
- 200 行能寫成 50 行,就重寫。

自問:「資深工程師會不會說這寫太複雜?」會 → 簡化。

## 3. 外科手術式變更

**只動該動的。只清自己的爛攤子。**

編輯既有檔案時:
- 不「順手改善」鄰近程式碼、註解、格式。
- 沒壞就不重構。
- 即使不認同既有風格,還是配合它。
- 看到不相關的死碼,**提一下**——但不要刪。

你的變更若產生孤兒:
- 移除**你的**變更使其變成未使用的 import / 變數 / function。
- 不要刪除預先存在的死碼,除非被明確要求。

測試:每一行變更都能直接對應使用者的請求。

## 4. 目標驅動的執行

**定義成功標準。迴圈直到驗證通過。**

把任務轉成可驗證的目標:
- 「加驗證」→「先寫測試,再讓測試通過」
- 「修 bug」→「先寫能重現 bug 的測試,再讓測試通過」
- 「重構 X」→「重構前後測試都通過」

多步驟任務先列計畫:
```
1. [步驟] → 驗證:[檢查]
2. [步驟] → 驗證:[檢查]
3. [步驟] → 驗證:[檢查]
```

明確的成功標準讓你可以獨立迴圈。模糊的標準(「讓它能動」)需要不斷被打斷確認。

---

## 5. 研究論文產出管線（EEG/MEG × MCI/AD）

此節定義研究專案的標準產出方式。沿用 PHCSSM 專案的成功管線。

### 5.1 關於我（研究補充）

- 研究主軸:**用機器學習演算法分析 EEG/MEG 訊號**,做 MCI 與早期 AD 的**早期診斷**,並**預測 MCI 階段的進展(MCI→AD progression)**。
- 既有臨床醫師(腎臟病、糖尿病、複雜內科急症)+ 認知神經科學博士身分不變。

### 5.2 每個研究專案的標準三件產出

| 產出 | 語言 | 規格 |
|------|------|------|
| `academic paper` | **英文** | APA 7th:in-text citation `(Author, Year)` + 文末 alphabetical reference list(含 DOI、期刊、卷期頁) |
| `popular-science blog` | **繁體中文** | 一般讀者取向,白話、有故事性,不堆術語 |
| `wrap-up + pitfalls 文件` | 繁中 | 本次 session 的設計決策、執行統計(agents / 秒數 / tokens)、踩坑紀錄;沿用 PHCSSM session-notes 格式 |

### 5.3 多代理人工作流基礎

以 PHCSSM v3.0 為模板(`phcssm_multi_agent_analysis_workflow_v3.js`,Robin MAS 架構):structured JSON schemas、Grounding Check Gate(每個 claim 對應原文)、BTL Tournament(兩兩比對解矛盾,優於 LLM 直接評分)、Consensus Reflectors(≥2/3 同意才列入)、Self-Healing Synthesis(漏項自動 retry 一次)。

可直接複用的 schema(只需改 `description`):`ANALYSIS_SCHEMA`、`GROUNDING_SCHEMA`、`BTL_SCHEMA`、`CRITIQUE_SCHEMA`、`REFLECTOR_CONSENSUS_SCHEMA`、`SYNTHESIS_SCHEMA`。

### 5.4 兩種模式(每次 session 擇一)

- **Literature review**:跨多篇文獻綜整 → 原創 review / research paper,多來源 APA 參考清單。先讓使用者確認「要回答什麼研究問題」再開跑。
- **Single-paper critique**:PHCSSM 式,對單一目標論文做接地 / BTL / reflector 深度拆解。需在 Phase 0 把論文全文(非摘要)放進 `PAPER` 常數——見 §5.6 坑洞。

### 5.5 零捏造鐵則(APA 專屬)

延續工作區零捏造原則,對引用加嚴:

- 每個 claim 必須對應**真實來源**;**禁止捏造參考文獻、DOI、頁碼、數字、作者職稱**。
- in-text citation 與文末 reference list 必須**一一對應**,不得有對不上的條目。
- 無法從來源確認的 claim 一律**留空或標「待確認」**(沿用 PHCSSM 坑洞:科普稿曾把作者誤稱「研究生」,實為「教授」)。

### 5.6 命名與雙存(save)慣例

- 檔名:`YYYY-MM-DD_<project>_academic_analysis.md`、`_blog_popular_science.md`、`_Session.md`;workflow 為 `<project>_workflow_v#.js`。
- **雙存**:commit 到 repo `ckt520728/claude-skills`,**且**複製到 `G:\我的雲端硬碟\Second Brain\知識庫\2026 Claude code`。
- 編碼 UTF-8 無 BOM;英文 paper / 繁中 blog。
- 重要坑洞:`PAPER` / 數字常數要從**全文**抽取,不要從摘要手抄(PHCSSM 曾因此混入錯誤數字,靠 Grounding Gate 才攔下)。

### 5.7 環境更新註記

舊踩坑「G: 槽無法從 Claude Code shell 存取」**已過時**:現在 Bash 工具能直接讀寫 `G:\我的雲端硬碟\Second Brain\知識庫\2026 Claude code`(POSIX 掛載為 `/g/我的雲端硬碟/...`)。

⚠️ 正確路徑含 **`我的雲端硬碟`**(Google Drive「我的雲端硬碟」根),不是最初寫的 `G:\Second Brain\...`。

---

**這份規則有效的訊號:** diff 裡沒有多餘變動、不再因過度設計而重寫、釐清問題出現在實作之前而非錯誤之後。
