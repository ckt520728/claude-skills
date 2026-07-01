# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 專案定位

**專案名稱：** AI 內容永動機（AI Content Perpetual Engine）
**個人品牌：** 朱國大醫師
**專案目標：** 建立一套半自動化的內容生產系統——從多元知識來源萃取，經 Claude Skill 處理，產出多格式內容草稿，由本人審閱後手動發布。
**未來規劃：** 設計為可複製模板，供其他醫師移植使用（個人隱私資料不納入模板）。

---

## 永動機架構

```
知識來源（Input）
    │
    ▼
[ 萃取層 ] ── Claude Skill 將原始素材結構化
    │         （paper / book / video / NLM）
    ▼
[ 批判層 ] ── Phase 4 Adversarial Critique
    │         Fatal / Major weakness → 結構化研究問題
    │                  │
    │                  ▼
    │         [ NotebookLM 定向查詢 ]
    │         用 critique 問題精確打撈跨來源證據
    │                  │
    │                  ▼
    │         NLM 回應 → 補強分析材料
    │
    ▼
[ 生成層 ] ── Claude 依格式生成內容草稿
    │         （社群貼文 / 電子報 / 文章討論段落）
    ▼
[ 審閱層 ] ── 朱醫師審閱、修改、核准
    │
    ▼
[ 發布層 ] ── 手動發布至各平臺
```

### Phase 4 → NotebookLM 橋接工作流程

**發現日期：** 2026-06-30
**觸發情境：** 分析 Khunti 2026 MLTC/CKM 筆記本（47 來源）時發現

Multi-Engine Research（如 phcssm / Robin MAS）在 **Phase 4 Consensus Adversarial Critique** 產出三類批評者視角：

| 反思者 | 批評焦點 | 對應 NLM 查詢策略 |
|--------|---------|-----------------|
| R1 方法論嚴謹性 | 異質性、因果推論框架 | 查詢：「哪些研究提供了因果推論設計？」 |
| R2 實證有效性 | 文獻流整合、外推限制 | 查詢：「MASLD 與 MLTC 框架的整合點在哪？」 |
| R3 新穎性與可複製性 | 獨立驗證、時效性 | 查詢：「Ariadne Principles 的實施證據是否更新？」 |

**為何比一般查詢更有效：**
- Critique 問題已內建**領域脈絡**，不是空泛提問
- Fatal weakness = 最值得深挖的知識缺口
- NLM 的跨來源整合能力在此才真正發揮

**輸出的雙重用途：**
1. **知識補強**：回填分析報告的侷限性段落
2. **內容生成**：直接作為文章「討論」或「爭議觀點」素材，驅動高品質社群貼文

### 知識來源（Input Sources）

| 類型 | 來源 |
|------|------|
| 學術論文 | PubMed 搜尋 + 本地 PDF 資料庫 |
| 閱讀筆記 | Notion（MCP 已連線）|
| 知識整理 | NotebookLM（MCP 已連線）|
| 個人筆記 | Obsidian Second Brain（MCP 已連線）、Word 檔 |
| 影片內容 | YouTube 逐字稿 |
| 書籍 | 電子書 PDF / EPUB 摘要 |
| 臨床經驗 | 朱醫師手動輸入 |

### 輸出格式（Output Formats）

| 格式 | 平臺 | 備註 |
|------|------|------|
| 部落格長文 | Facebook（現階段）| 建議未來遷移至 Ghost 或 Substack |
| 社群長文 | Facebook | |
| 社群短文 | Instagram、其他平臺 | |
| 輪播圖 | Instagram + Facebook | 風格依內容定：學術感／科技藍／醫療白／品牌色 |
| 短影音腳本 | Sora / HeyGen / Higgsfield | Claude 產腳本，影片生成在平臺端操作 |

### 觸發方式

永動機為**半自動**，觸發點依情境而定：
- 讀完論文或書籍章節後手動觸發
- 有臨床案例或想法時隨時輸入
- 定期掃描 Notion / Obsidian 新增筆記

---

## 內容主題範疇

- 腎臟科臨床知識與最新文獻
- 認知神經科學研究與應用
- AI 工具（Claude Code、MCP、Skill 開發）教學
- 醫師 AI 工作流程實作
- 跨域學習經驗
- 人生哲學與思考框架

---

## 已連線 MCP 工具

| 工具 | 用途 | 備註 |
|------|------|------|
| **NotebookLM MCP** | 知識整理、來源摘要 | `nlm login` 重新驗證 |
| **Notion MCP** | 閱讀筆記讀寫 | |
| **Obsidian MCP** | Second Brain 讀寫 | Vault：`G:\我的雲端硬碟\Second Brain` |
| **Canva MCP** | 輪播圖設計生成 | `generate-design` 工具 |
| **GitHub CLI** | 版本控制、Skill 管理 | 帳號：`ckt520728` |
| **Firebase CLI** | 網站部署 | 主專案：`my-teaching-tools-ckt520728` |

### 影音生成平臺（手動操作，非 MCP）

| 平臺 | 用途 |
|------|------|
| **Sora** | 短影音生成 |
| **HeyGen** | AI 虛擬主播影片 |
| **Higgsfield** | 短影音生成 |

Claude 負責產出**影片腳本與旁白文字**，實際生圖／生影在平臺端操作。

### 圖片生成（Codex Image Gen）

Claude 生成優化英文 Prompt → 朱醫師貼至 Codva 生圖。
詳見 `codex-image-gen.skill`。

---

## Skill 庫

自訂 Skill 集中於 GitHub repo：[ckt520728/claude-skills](https://github.com/ckt520728/claude-skills)
本地備份同步至：`G:\我的雲端硬碟\Second Brain\創作庫\2026_Claude_code_skills\`

與本專案直接相關的 Skill：
- `codex-image-gen.skill` — 生成 Codex Image Gen prompt
- `paper-summary-extraction.skill` — 論文摘要萃取，輸出 Obsidian 卡片（Phase 1 ✅）
- `academic-paper-deep-analysis.skill` — 單篇論文七層深度分析
- `book-chapter-deep-analysis.skill` — 書籍逐章深度分析（概念→證據→範例→批判→意涵→引文）
- `video-talk-deep-analysis.skill` — 影片演講深度分析（概念→證據→範例→批判→科學意涵）
- `social-post-generation.skill` — 社群貼文生成：Facebook 長文（3 風格）× IG 短文（3 版本）× Substack 中英雙語（Phase 2 ✅）
- `carousel-design.skill` — 輪播圖設計：Canva MCP 生成多頁投影片（4 種品牌風格）（Phase 3 ✅）
- `master-orchestrator.skill` — 全管線編排：一個來源 → 完整 Content Package（Phase 5 ✅）
- `nlm-bridge.skill` — NLM Bridge：Adversarial Critique → 定向 NLM 查詢 → 雙軌合成（補強分析 + 爭議討論草稿）（Phase 4a ✅）
- `video-script.skill` — 短影音腳本：HeyGen AI 主播 / Reels 直拍 / Sora 視覺三格式（Phase 4b ✅）
- `paper-summary-extraction.skill` — 論文快速摘要 → Obsidian（Phase 1 永動機）
- `academic-paper-deep-analysis.skill` — 單篇論文七層深度分析（Master Prompt 20260106）

---

## 常用指令

```bash
# GitHub
gh repo list ckt520728

# Firebase
firebase use my-teaching-tools-ckt520728
firebase deploy

# NotebookLM
nlm login                        # 重新驗證
nlm login switch <profile>       # 切換 Google 帳號
```

---

## 模板化原則（供未來開源使用）

移植此系統給其他醫師時，需替換以下項目：

| 項目 | 原始值 | 替換為 |
|------|--------|--------|
| 個人品牌名稱 | 朱國大醫師 | `{{DOCTOR_NAME}}` |
| GitHub 帳號 | `ckt520728` | `{{GITHUB_USERNAME}}` |
| Firebase 專案 ID | `my-teaching-tools-ckt520728` | `{{FIREBASE_PROJECT_ID}}` |
| Obsidian Vault 路徑 | `G:\我的雲端硬碟\Second Brain` | `{{OBSIDIAN_VAULT_PATH}}` |
| 內容主題 | 腎臟科 × 認知神經科學 × AI | `{{CONTENT_DOMAIN}}` |
| 發布平臺帳號 | Facebook / Instagram（個人） | `{{SOCIAL_ACCOUNTS}}` |

---

## 部落格平臺規劃

| 平臺 | 語言 | 策略 | 狀態 |
|------|------|------|------|
| **Facebook** | 中文 | 現階段主力，長文發布 | 使用中 |
| **Substack** | 中英雙語 | 訂閱制電子報，國際讀者 | 待開設 |
| **方格子** | 繁體中文 | 台灣讀者，付費文章 | 待開設 |

Substack 有 API 可半自動發布；方格子目前需手動。

---

## 影音生成平臺

| 平臺 | 串接方式 | 狀態 | 需求 |
|------|---------|------|------|
| **HeyGen** | 官方 MCP（`heygen-mcp`） | ✅ 已安裝 | uvx heygen-mcp，API Key 已設定 |
| **Sora** | OpenAI API（`sora-2` / `sora-2-pro`） | 待安裝 | OpenAI API Key |
| **Higgsfield** | Python SDK CLI wrapper | 暫緩 | Creator 方案 $15+/月 |

Claude 負責產出**影片腳本與旁白文字**，生圖／生影在平臺端操作（HeyGen MCP 安裝後可直接在 Claude 觸發）。

### HeyGen MCP 安裝設定

在 `claude_desktop_config.json` 的 `mcpServers` 加入：

```json
"heygen-mcp": {
  "command": "npx",
  "args": ["-y", "heygen-mcp"],
  "env": {
    "HEYGEN_API_KEY": "{{HEYGEN_API_KEY}}"
  }
}
```

### Sora API 設定（與 Image Gen 共用 OpenAI Key）

```json
"openai-video-gen": {
  "command": "npx",
  "args": ["-y", "@openai/sora-mcp"],
  "env": {
    "OPENAI_API_KEY": "{{OPENAI_API_KEY}}"
  }
}
```

---

## Skill 開發路線圖

```
Phase 1 ✅：論文摘要萃取 Skill（paper-summary-extraction.skill）
             輸入：PubMed PMID/URL、本地 PDF、Notion 筆記、NotebookLM
             輸出：結構化繁中摘要卡片 → Obsidian 知識庫/

Phase 1b ✅：論文深度分析 Skill（academic-paper-deep-analysis.skill）
             輸入：單篇論文全文/PDF/摘要/NotebookLM 輸出
             輸出：七層結構化分析報告 → Obsidian 知識庫/

Phase 1c ✅：書籍逐章分析 Skill（book-chapter-deep-analysis.skill）
             輸入：電子書 PDF/EPUB、章節筆記、NotebookLM 輸出
             輸出：全書快照 + 逐章分析（概念→證據→範例→批判→意涵→引文）→ Obsidian 知識庫/

Phase 1d ✅：影片演講深度分析 Skill（video-talk-deep-analysis.skill）
             輸入：YouTube 逐字稿、部分逐字稿、個人筆記、NotebookLM 輸出
             輸出：五層結構分析（概念→證據→範例→批判→科學意涵）→ Obsidian 知識庫/

Phase 2 ✅：社群貼文生成 Skill（social-post-generation.skill）
             輸入：任何 Phase 1 Skill 輸出 / Obsidian 摘要卡片 / 用戶手動描述
             輸出：
               Facebook 長文：醫師科普版 / 學術同儕版 / 跨域思考版（3 風格）
               IG 短文：知識型 / 故事型 / 行動呼籲型（3 版本 + Hashtag）
               Substack：繁體中文版 + English version（中英雙語）
             草稿存至 Obsidian：G:\我的雲端硬碟\Second Brain\內容草稿\YYYY-MM\

Phase 3 ✅：  輪播圖設計 Skill（carousel-design.skill）
             輸入：Phase 1/2 Skill 輸出 / Obsidian 摘要卡片 / 用戶手動描述
             輸出：Canva MCP 多頁投影片設計
               風格：A 學術感 / B 科技藍 / C 醫療白 / D 品牌色（深藍+金色）
               Canva 流程：request-outline-review（Widget 審閱）→ generate-design-structured
               配套 [G]：呼叫 social-post-generation → IG 配套說明文

Phase 5 ✅：   Master Orchestrator（master-orchestrator.skill）
             輸入：任何知識來源（論文/書籍/影片/主題描述）
             模式：FULL / ANALYSIS / CONTENT / EXPRESS / CUSTOM
             執行：Stage 1→2→3→4→5 自動編排，Content Seed 跨 Stage 傳遞（≤300 字壓縮）
             輸出：完整 Content Package Dashboard + 建議發布排程

Phase 4a ✅：  NLM Bridge 獨立 Skill（nlm-bridge.skill）
             輸入：Phase 1 分析報告（[N] 選項觸發）/ 直接貼入批評文字 / 手動描述知識缺口
             核心邏輯：R1/R2/R3 批評 → 5 個定向 NLM 查詢 → 雙軌合成
             輸出 軌道 1：補強後侷限段落（寫回 Obsidian 原始報告）
             輸出 軌道 2：爭議討論草稿 → 觸發 social-post / carousel / video-script
             NLM MCP：自動執行（notebook_query）；未連線時輸出手動查詢清單

Phase 4b ✅：  短影音腳本 Skill（video-script.skill）
             輸入：Phase 1/2/3 輸出 / Obsidian 摘要卡片 / 用戶手動描述
             輸出（三格式）：
               [H] HeyGen AI 虛擬主播腳本（含 [PAUSE]/[EMOTION] 標記）
               [R] Reels/Shorts 直拍腳本（含視覺指示 + 螢幕字幕建議）
               [S] Sora 視覺場景腳本（英文 Visual Prompt + 中文旁白）
             時長：30 / 60 / 90 / 120 / 180 秒
             HeyGen MCP：已安裝（uvx heygen-mcp）；MCP 連線時自動呼叫，否則輸出純文字版手動貼入
```
