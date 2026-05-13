# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

行為準則 + 此工作區的硬性規則。改寫自 Andrej Karpathy 公開分享的 CLAUDE.md 模板,並合併個人踩坑紀錄。

**Tradeoff:** 這份規則偏向謹慎勝於速度。瑣碎任務自行判斷。

---

## 關於我

- 臨床醫師,專長腎臟病、糖尿病、複雜內科急症
- 認知神經科學博士
- 此資料夾 / repo 用於 **Claude Code Skill 開發**
- Obsidian 第二大腦另有獨立 CLAUDE.md 管理 vault 結構(知識庫 / 創作庫 / 每日筆記 / Templates),規則互不干擾

## 語言偏好

- 對話、文件、commit message、SKILL.md 正文一律**繁體中文**
- 技術專有名詞(API 名稱、變數、library 名)保留英文
- Skill `name:` 欄位、目錄名、檔名必須**純 ASCII**(見 §5)
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

## 5. Skill 開發的硬性規則(此工作區專屬)

### 5.1 Skill (.zip) 的四個上傳陷阱

製作或重新封裝 Skill 時必須**同時**滿足以下四點,否則 claude.ai 的 Upload skill 介面會擋下來。錯誤訊息常具誤導性(尤其 #3 與 #4 文字完全相同,但根因不同)。

| # | 規則 | 違反時的錯誤訊息 |
|---|------|----------------|
| 1 | zip 內必須有**單一根目錄**包住 `SKILL.md`(結構為 `<root>/SKILL.md`),不能巢狀過深,也不能裸放最外層 | `"SKILL.md file must be in the top-level folder"` |
| 2 | zip entry 路徑分隔符必須用 `/`。**禁用** PowerShell `Compress-Archive`(它寫 `\`),改用 `System.IO.Compression.ZipArchive` + 手動 `.Replace('\','/')` | `"Zip file contains path with invalid characters"` |
| 3 | zip 內**根目錄名**只能含 `[A-Za-z0-9_-]` | `"root directory name must contain only alphanumeric..."` |
| 4 | SKILL.md frontmatter `name:` 欄位也只能含 `[A-Za-z0-9_-]`,且**建議**與 zip 根目錄同名(Anthropic 把這個值當作安裝後的目錄 `~/.claude/skills/<name>/`) | 同 #3(訊息一字不差,但根因不同) |

H1 標題、`description`、正文**可保留中文**。**只有** `name:` 與目錄名必須 ASCII。

### 5.2 編碼

SKILL.md 一律用 **UTF-8 無 BOM**。PowerShell 的 `Set-Content` / `Out-File` 預設寫 UTF-16 LE with BOM,會破壞中文。必須:

```powershell
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($path, $content, $utf8NoBom)
```

Claude Code 內建的 `Write` 工具預設 UTF-8 無 BOM,可直接用。

### 5.3 Skill 設計的共同原則

此工作區內所有 skill 共享以下原則,新 skill 要遵守:

1. **零外部 LLM API 依賴**——不呼叫 OpenAI / Gemini / 其他 LLM API。Claude 本身就在執行,呼叫外部多一層失真且花錢。
2. **零捏造(Zero-Fabrication)**——每個 skill 在對應領域(數字、引用、承諾、技能、資料)都要有明確的零捏造規則寫入 SKILL.md。
3. **強制業務問題前置**——長流程開跑前讓使用者確認「要回答什麼問題」,避免空泛的「general observations」輸出。
4. **使用者干預點**——長流程一定有可暫停的位置改方向(outline review、gap 分析、triage 分類)。
5. **反 LLM 陳腐用詞清單**——每個 skill 維護對應領域的禁用詞庫(`delve into` / `leverage` / `祝商祺` / `In conclusion` ...)。
6. **協作整合**——輸出格式設計成可被其他 skill 消費(預設 Markdown)。

### 5.4 SKILL.md 標準結構

```
---
name: <ASCII kebab-case,與 root 同名>
description: <一段話含觸發詞,繁中為主>
---

# <Skill 標題>

## 目的
## 🚨 鐵則(該領域的零捏造規則)
## 觸發後的工作流程(分 Step)
## 重要的編輯原則
## 跟其他 skill 的協作(可選)
## 不要做的事
```

### 5.5 命名與輸出慣例

- skill 目錄:`<skill-name>/`,內含 `SKILL.md`
- 上傳檔:`<skill-name>.skill`(實為 zip,改副檔名以符合 repo 既有慣例)
- 輸出檔案編碼:UTF-8 無 BOM
- 日期格式:`YYYY-MM-DD`
- 路徑分隔符討論時用 `/`,實作時依平台
- 不主動加 emoji 到檔案內容,除非使用者明確要求

### 5.6 本地 Skill Loader 的 `description: |` 規則

本地安裝（`~/.claude/skills/`）時，`description` 欄位必須用 **literal block scalar（`|`）**，不能用 folded scalar（`>`）。

```yaml
# ✅ 正確
description: |
  第一行說明。
  第二行說明。

# ❌ 錯誤——loader 回報「Skill.md must start with YAML front matter」，但根因是這個
description: >
  第一行說明。
```

注意：§5.1 是 claude.ai **上傳介面**的規則；本節是**本地 loader** 的規則，兩者獨立。詳見 `docs/2026-05-09-install-pitfalls.md`。

---

## 6. Skill 清單（快速索引）

| Skill | 觸發語（節錄） | 輸出 | 關鍵依賴 |
|-------|--------------|------|---------|
| `admission-note` | admission note、住院病歷、入院紀錄 | `.docx` | `python-docx` |
| `lecture-notes` | lecture notes、課堂筆記、錄音轉筆記 | PDF / PPTX | `notebooklm-mcp` MCP（首選）；備援: Groq + OpenAI |
| `soil-image-deck` | 純圖片簡報、全圖簡報 | 全圖 `.pptx` | `gpt-image-2` + `pack_pptx.py` |
| `soil-teaching-deck` | 教學簡報、上課用投影片、用 SOIL 做簡報 | 可編輯 `.pptx` | PptxGenJS、`python-pptx`、`cairosvg` |
| `soil-html-deck` | HTML 簡報、互動式簡報、可分享連結的簡報 | 單一 `.html` | `gpt-image-2`、Pillow |
| `openclaw-automation` | OpenClaw 斷線、LINE webhook 掛掉 | 恢復腳本 | Node.js |
| `personal-medical-website` | 個人網站、醫師個人頁面、學術作品集 | 單一 `index.html` | 無（純 HTML/CSS/JS）|
| `research-organizer` | 整理研究素材、論文筆記 | 結構化 Markdown | 無外部 API |
| `article-writer` | 寫文章、Medium 發文 | 長文 Markdown | 無外部 API |
| `meeting-minutes` | 會議紀錄、逐字稿整理 | 結構化 Markdown | 無外部 API |
| `resume-tailor` | 客製履歷、根據 JD 調整 | 履歷 + 改動清單 | 無外部 API |
| `knowledge-base` | 知識庫寫入/查詢、Obsidian 筆記 | 原子化 Markdown | 無外部 API |
| `email-assistant` | 寫 Email、回信、整理收件夾 | 草稿（存 Gmail）| Gmail MCP；不主動送出 |
| `data-analyzer` | 資料分析、CSV 分析 | Markdown 報告 + PNG + Python 腳本 | 無外部 API |
| `dashboard-builder` | 個人看板、每日 briefing | Markdown 看板 | Gmail / Obsidian / Calendar MCP（可選）|

---

## 7. 架構快速參考

### SOIL 三件套（soil-image-deck / soil-teaching-deck / soil-html-deck）

共用 **六引擎流水線**：引擎 1（概念定位）→ 2（脈絡定位）→ 3（頁面架構）→ 4（認知編修）→ 5（風格建構）→ 6（生成）。引擎 1–5 是純規劃；引擎 6 才生成成品。

**圖像生成兩條路：**
1. **直接 API**：`draw` skill（`C:/Users/mathr/.claude/skills/draw/draw.py`）呼叫 `gpt-image-2`，需 `OPENAI_API_KEY`。
2. **跨工具協作 SOP**（無 API key 時）：Claude 跑完引擎 1–5 後產出 `specs/image_briefs.md`（每頁一個獨立 prompt），停下等使用者在 ChatGPT / Codex 生圖，圖放入 `images/` 後回來打包。完整流程見 `docs/cross-tool-image-sop.md`。

**跨工具圖檔命名不可協商**：`page_NN_<role>.png`（NN 補零）。`pack_pptx.py` 依此排序。

`soil-teaching-deck` 額外支援幾何圖渲染（`geometry_renderer.py` + `cairosvg`）——幾何子流程（G-1 至 G-5）必須在撰寫 PptxGenJS 腳本前完成。

```
<專案>/
├── specs/plan.md, page_layout.yaml, image_policy.yaml, image_briefs.md
├── images/page_NN_<role>.png
└── output/<title>.pptx or .html
```

### lecture-notes Skill

主路徑用 `notebooklm-mcp`：`notebook_create` → `source_add`（音檔 + PDF 並行，`wait=True`）→ `studio_create`（`artifact_type="slide_deck"`, `language="zh-TW"`）→ `ScheduleWakeup(delaySeconds=270)` 輪詢 `studio_status` → `download_artifact`。典型完成：5–15 分鐘。

備援 pipeline 在 `lecture-notes/scripts/`（Groq + GPT-4o），需 `GROQ_API_KEY` + `OPENAI_API_KEY`，僅在 MCP 不可用時使用。

### openclaw-automation Skill

`LINE → Cloudflare quick tunnel → proxy（:18790/line/webhook）→ OpenClaw Gateway（:18789）`。不直接對外暴露 Gateway。重開機後 tunnel URL 輪換，跑 `scripts/ensure-openclaw-line.ps1` 全自動恢復。

### 安裝 Skill 到本地

```powershell
# Windows
xcopy /E /I <skill-name> "C:\Users\User\.claude\skills\<skill-name>"

# Mac/Linux
cp -r <skill-name> ~/.claude/skills/
```

### 常用依賴速查

```bash
pip install python-pptx "markitdown[pptx]" Pillow cairosvg python-docx openpyxl
npm install -g pptxgenjs
# lecture-notes 備援 pipeline
pip install groq openai pymupdf jinja2 playwright && playwright install chromium
```

---

**這份規則有效的訊號:** diff 裡沒有多餘變動、不再因過度設計而重寫、釐清問題出現在實作之前而非錯誤之後。
