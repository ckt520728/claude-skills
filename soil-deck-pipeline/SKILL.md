---
name: soil-deck-pipeline
description: |
  研究素材到簡報的「總指揮」工作流 skill。把 NotebookLM 研讀成果，經 Claude Code
  整理成 SOIL 六大引擎大綱，圖像交給 ChatGPT/Codex 的 gpt-image-2 生成，最後在
  Claude Code 內整合成 HTML 互動簡報與 PowerPoint 簡報。本 skill 是「總流程編排」，
  負責串接 NotebookLM MCP、soil-html-deck / soil-image-deck / soil-teaching-deck，
  並內建 Windows / PowerShell / python-pptx 的踩坑解法。
  觸發詞：「從 NotebookLM 做簡報」「NotebookLM 匯出做 PPT」「研究資料到簡報的完整流程」
  「用 SOIL 做整套簡報」「HTML 簡報跟 PowerPoint 一起做」「簡報生圖交給 Codex」
  「NotebookLM MCP 匯出 studio」「把 notebook 整理成簡報」「研讀完做成投影片」
  「製作 HTML PPT 跟 PowerPoint PPT 的工作流」。
  也在這些建置踩坑時觸發：「python-pptx PIL 壞掉 / DLL load failed」
  「PowerShell 中文亂碼 / UTF-8 當 ANSI」「PowerPoint COM 失敗 / RPC_E_CALL_REJECTED」
  「msoTriState 轉型錯誤」「PPTX 被檔案鎖 / ~$ owner file」「base64 內嵌圖到 HTML」。
  不適用：單純只要一份 deck（直接用對應的 soil-* skill）、純文章寫作（用 article-writer）。
---

# SOIL Deck Pipeline（研究素材 → 簡報 總指揮工作流）

## 目的

把「在 NotebookLM 研讀 → 整理成資料夾 → 做 SOIL 大綱 → 生圖 → 整合成 HTML/PPTX 簡報」
這條完整路線編排成一個可重複的工作流。Claude Code 是**指揮中心（conductor）**，
負責呼叫工具、整理素材、寫程式、打包；NotebookLM 負責研讀與檢索，ChatGPT/Codex 負責生圖。

本 skill 不重寫 soil-* 三件套的內部邏輯，而是**串接它們**，並把今天累積的
Windows 建置踩坑解法集中在 [`docs/windows-build-pitfalls.md`](docs/windows-build-pitfalls.md)，
可重用腳本放在 [`scripts/`](scripts/)。

---

## 五步驟工作流（總覽）

```
1. NotebookLM 研讀      →  在 NotebookLM 對話、檢索、產 studio 輸出（人工 or MCP）
2. 匯出到資料夾         →  Claude Code 呼叫 notebooklm-mcp 匯出 studio/note 到 workspace 資料夾
3. SOIL 六引擎大綱      →  Claude Code 讀資料夾 → 產出逐頁 outline（停下來給使用者改）
4. 生圖（跨工具）       →  Claude 產 image_briefs.md → 使用者用 Codex/ChatGPT gpt-image-2 生圖
5. 整合成簡報           →  soil-html-deck（HTML）+ soil-teaching-deck（可編輯 pptx）+ soil-image-deck（全圖海報）
```

> **黃金分工：** 用 Claude 強的地方（規劃、寫程式、打包），用 Codex/ChatGPT 強的地方（生圖），
> 中間用**檔案**傳遞。詳見 `_shared/cross-tool-image-sop.md`。

---

## 🚨 鐵則（零捏造 + 環境守則）

1. **零捏造素材**：步驟 3 的大綱只能用步驟 2 真正匯入資料夾的內容。找不到對應出處的論點、數字、引用，一律標「待補」，不要編。
2. **生圖不假裝**：Claude **不能**直接呼叫 OpenAI / gpt-image-2。一律走跨工具 SOP：產 `image_briefs.md` → 停下來等使用者生圖 → 回來先 QA 再打包。絕不假裝圖已生好。
3. **大綱要先給使用者確認**：步驟 3 產出完整逐頁 outline 後**停下來**，等使用者點頭才進步驟 4/5。
4. **HTML 圖一律 base64 內嵌**：不要用相對路徑（預覽面板、搬移、分享都會壞）。
5. **Windows 建置先讀踩坑檔**：動到 PowerShell 寫檔、python-pptx、PowerPoint COM、影像壓縮前，先看 [`docs/windows-build-pitfalls.md`](docs/windows-build-pitfalls.md)，不要重踩。
6. **檔名約定不可協商**：跨工具圖檔一律 `page_NN_<role>.png`（NN 補零）。打包依此排序，命名錯就順序錯。
7. **push 是公開動作**：commit + push 到 GitHub Pages 前先讓使用者知道；除非使用者已明確授權自動推。

---

## 觸發後的工作流程（分 Step）

### Step 1 — 釐清業務問題與範圍（長流程前置）

開跑前先問清楚（一次問完）：
- 主題與**要回答的核心問題**是什麼？
- 受眾與時長（決定張數：30 min≈20-25 張、60 min≈35-45 張、90 min≈50+ 張）
- 三件套要做幾件？（預設：HTML 為主，teaching-deck 可編輯副本，image-deck 海報選做）
- 圖像生成器（預設 gpt-image-2，走跨工具 SOP）
- 既有圖檔（NotebookLM infographic、PNG）優先沿用，缺的才新生

### Step 2 — 用 NotebookLM MCP 匯出研讀成果到資料夾

Claude Code 作為指揮中心，呼叫 `notebooklm-mcp` 把指定 notebook 的對話/studio 成果匯出：

1. `notebook_list` → 找到目標 notebook id
2. `notebook_describe` / `source_list_drive` → 確認來源與 studio artifacts
3. `studio_status` / `download_artifact` / `export_artifact` → 把 studio 輸出（report / mind map / audio overview 文字稿等）落地到 workspace 資料夾
4. `source_get_content` → 需要時抽取個別 source 全文
5. 若 MCP 認證過期 / 連不上 → 走 `mcp-obsidian-setup` skill 的修復流程，或手動從 notebooklm.google.com 匯出後放進資料夾

> **降級路線：** 若 NotebookLM MCP 不可用，就請使用者手動把 NotebookLM 匯出的 .md/.txt/.pdf 丟進資料夾，Claude 直接讀資料夾。流程不中斷。

### Step 3 — 讀資料夾，產 SOIL 六引擎逐頁大綱

讀完資料夾全部素材後，依 SOIL 六大引擎產出逐頁 outline：

| 引擎 | 要決定的事 |
|---|---|
| ① 概念引擎 | One Big Idea（一句話貫穿全場） |
| ② 脈絡引擎 | Hook（從受眾痛點切入） |
| ③ 架構引擎 | 分段結構，每段結尾 take-home tile |
| ④ 認知引擎 | 一頁一概念、公式 ≤ 3、列表 ≤ 5 |
| ⑤ 風格引擎 | 配色、字體、視覺母題 |
| ⑥ 教學迴路 | Check-Point 互動投票位置（HTML 可接 classroom-vote） |

outline 每頁標註：**標題 / 核心訊息 / 視覺策略 / 素材來源（既有圖 or 新生圖 or 純 CSS/SVG）**。
**產完停下來給使用者改**，確認後才往下。

### Step 4 — 跨工具生圖（gpt-image-2）

依 `_shared/cross-tool-image-sop.md`：
1. 盤點哪些頁需要新生圖（既有 PNG / Chart.js / 純 SVG 能解決的就不要生）
2. 產出 `specs/image_briefs.md`，每張一個**獨立完整 prompt**（含統一風格段、`No readable text`、留文字疊放區、比例）
3. **停下來**，請使用者去 Codex CLI（批次）或 ChatGPT 網頁版（逐張）跑 gpt-image-2
4. 圖存成 `images/page_NN_<role>.png` 回來後，Claude **先逐張 QA** 再進 Step 5

### Step 5 — 整合成簡報（三件套）

| 產物 | 用哪個 skill / 工具 | 備註 |
|---|---|---|
| **HTML 互動簡報（主）** | `soil-html-deck` | base64 內嵌圖、Chart.js、投票、一鍵分享 |
| **可編輯 PPTX（副）** | `soil-teaching-deck` 概念 + `scripts/pptx_pil_stub.py` 模式 | 給只用 PowerPoint 的人 |
| **全圖海報 PPTX（選）** | `soil-image-deck` | 挑關鍵頁做全版單張圖，社群用 |

建置時遇到以下狀況，**直接套用** `docs/windows-build-pitfalls.md` 的解法：
- 影像壓縮 → `scripts/compress_images.ps1`（PowerShell + System.Drawing，避開壞掉的 PIL）
- 產 PPTX 但 PIL/python-pptx 壞掉 → `scripts/pptx_pil_stub.py`（import 前注入 PIL stub）
- 發布到 GitHub Pages + 雙向連結 → `scripts/sync_to_pages.ps1`（一鍵 build→copy→push）

---

## 重要的編輯原則

- **指揮中心心態**：Claude 串接工具、寫程式、把關品質；不自己硬幹本機沒有的能力（如直接生圖）。
- **既有資產優先**：NotebookLM 已產的 infographic、先前 deck 的 PNG、純 CSS/SVG 能解決的，就不要花錢新生圖。
- **檔案傳遞**：工具之間用 `specs/`（規劃）、`images/`（圖）、`output/`（成品）三層資料夾交換。
- **停得下來**：步驟 3（大綱）與步驟 4（生圖）各有一個強制暫停點讓使用者改方向。
- **可重跑**：所有建置都寫成腳本（不要手動一次性操作），方便使用者日後自己重跑同步。

---

## 跟其他 skill / MCP 的協作

- **notebooklm-mcp**（Step 2）：匯出 notebook studio / source 內容到資料夾。
- **mcp-obsidian-setup**：NotebookLM MCP 認證過期 / 連不上時的修復。
- **soil-html-deck / soil-image-deck / soil-teaching-deck**（Step 5）：實際產 deck。
- **classroom-vote**：HTML deck 的 Check-Point 投票可接真實即時投票。
- **knowledge-base / research-organizer**：把 NotebookLM 匯出的素材先做結構化整理（選用）。
- **article-writer + personal-medical-website**：把同一份素材延伸成部落格長文並發布（今天的延伸案例）。
- **跨工具 SOP**：[`_shared/cross-tool-image-sop.md`](../_shared/cross-tool-image-sop.md)。

---

## 不要做的事

- ❌ 不要直接呼叫 OpenAI API / `draw` skill 生圖（本機可能沒有）——一律走跨工具 SOP。
- ❌ 不要假裝圖已生好就打包。
- ❌ 不要在大綱裡編造素材沒有的論點或引用。
- ❌ 不要用 PowerShell `Compress-Archive`（會寫 `\` 分隔符，破壞 .skill）——用 `System.IO.Compression`。
- ❌ 不要在含中文的 `.ps1` 用預設編碼存（PS 5.1 當 ANSI 讀會亂碼）——腳本本體全 ASCII，中文抽到 UTF-8 sidecar。
- ❌ 不要用相對路徑放 HTML 圖——一律 base64 內嵌。
- ❌ 不要未告知就 push 到公開 GitHub Pages。

---

## 版本

| 日期 | 變更 |
|---|---|
| 2026-05-20 | 初版。整理自 David Sussillo 簡報 + 部落格實作的完整工作流與 Windows 建置踩坑。 |
