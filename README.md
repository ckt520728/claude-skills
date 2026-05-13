# Claude Skills

A collection of custom Claude Code skills.

## Skills

### openclaw-automation

Restores and operationalizes an OpenClaw + LINE assistant on Windows when the local proxy, Cloudflare quick tunnel, or LINE webhook endpoint stops working.

**Use for:**
- OpenClaw LINE webhook outage recovery
- Cloudflare quick tunnel URL rotation after reboot
- Windows startup/daily recovery task setup
- Codex heartbeat automation stale-thread diagnosis

**Included scripts:**
- `scripts/ensure-openclaw-line.ps1` restarts proxy/tunnel, updates LINE endpoint, and runs LINE official webhook test.
- `scripts/line-webhook-proxy.mjs` exposes only `/line/webhook` locally and forwards POST requests to OpenClaw Gateway.
- `scripts/run-openclaw-line-ensure.cmd` provides a stable Windows scheduled-task/Startup wrapper.

**Portable artifact:** `openclaw-automation.skill`

---

### admission-note

Automatically generates a hospital admission note (`.docx`) from patient data provided via:
- Screenshots / images
- Word files (`.docx`)
- Excel files (`.xlsx`)

**Trigger phrases:** "admission note", "住院病歷", "入院紀錄"

**Output:** A formatted Word document with sections:
Chief Complaint, HPI, PMH, PSH, Medications, Allergies, Family History, Social History, Review of Systems, Vital Signs, Physical Examination, Labs, Imaging, Assessment & Plan.

#### Installation

```bash
# macOS/Linux
cp -r admission-note ~/.claude/skills/

# Windows
xcopy /E /I admission-note "%APPDATA%\Claude\skills\admission-note"
```

Restart Claude Code. Alternatively, use the pre-packaged `admission-note.skill` file.

---

### lecture-notes

Transforms lecture audio recordings and presentation slides (PDF/PPT) into illustrated, structured PDF/PPTX notes in Traditional Chinese, styled after 黃鍔院士 academic report format.

**Primary pipeline (NotebookLM MCP):**
1. Create a notebook via `notebooklm-mcp`
2. Upload audio + PDF slides in parallel (`wait=True`)
3. Generate a `slide_deck` artifact with a custom `focus_prompt` (繁體中文 concept maps, colour-coded nodes, key-takeaway footers)
4. Poll with `ScheduleWakeup(delaySeconds=270)` until done (~5–15 min), then download PDF and/or PPTX

**Trigger phrases:** "lecture notes", "課堂筆記", "錄音轉筆記", "上課筆記"

**Requires:** `notebooklm-mcp` MCP server connected in Claude Code (`/mcp`)

**Fallback pipeline** (if MCP unavailable) — legacy scripts in `lecture-notes/scripts/`:

```bash
uv pip install groq openai pymupdf pillow jinja2 playwright
playwright install chromium
python lecture-notes/scripts/main.py \
  --audio recording.mp3 --slides slides.pdf --output notes.pdf \
  --groq-key $GROQ_API_KEY --openai-key $OPENAI_API_KEY \
  --title "Course Title" --speaker "Speaker Name" --date "2026-04-01"
```

**Output Style:** Each section contains a bold title, a colourful concept map (parchment background, colour-coded nodes, flow arrows), and conversational lecture transcript in Traditional Chinese.

---

## SOIL 三件套簡報 Skill（2026-05-09 新增）

依李俊儀教授 SOIL 教學設計六引擎 + 林長揚 30 條簡報原則打造的三種簡報生成 Skill。圖像生成統一呼叫 OpenAI `gpt-image-2`（ChatGPT/Codex 訂閱者免另設 API key 即可使用）。

### soil-image-deck

**用途：** 純圖片 `.pptx`，每頁一張 AI 生成的全版圖。適合直播暖場、社群貼文、視覺衝擊型開場。

**輸出：** 單一 `.pptx`，每張 slide 即一張 1536×1024 滿版圖。

**Trigger：** 「做純圖片簡報」、「全圖簡報」、「每頁都是 AI 生的圖」

**附帶腳本：** [`soil-image-deck/pack_pptx.py`](soil-image-deck/pack_pptx.py)（用 python-pptx 把 PNG 打包成 pptx）

### soil-teaching-deck

**用途：** 圖 + 可編輯文字的教學簡報。適合教學現場、需後續手動微調文字。

**輸出：** `.pptx`（文字物件可雙擊修改、AI 圖嵌入為插畫）。

**Trigger：** 「做教學簡報」、「上課用的投影片」、「文字可編輯的簡報」、「用 SOIL 做簡報」

### soil-html-deck

**用途：** 自由度最高的單一 `.html` 簡報。支援 Chart.js 互動圖表、可點擊表格、影片嵌入、RWD 跨裝置。圖像 base64 內嵌、可直接分享 URL。

**輸出：** 單一 `.html`（約 1.3–1.6 MB，base64 內嵌）。

**Trigger：** 「做 HTML 簡報」、「網頁版簡報」、「互動式簡報」、「可分享連結的簡報」

### 共同設計憲法

三個 Skill 都遵守：
1. **林長揚 30 原則**（字級 55/34/21/13、Z 字排版、強調色 1-2 種、進度條、標題 ≤10 字…）
2. **SOIL 六引擎**：概念定位 → 脈絡定位 → 頁面架構 → 認知編修 → 風格建構 → 總導演
3. **SOIL 三段式脈絡**：引起動機 → 維持注意 → 喚起行動

### 安裝

複製對應資料夾到 `~/.claude/skills/`，重啟 Claude Code 即可。例：

```bash
cp -r soil-image-deck soil-teaching-deck soil-html-deck ~/.claude/skills/
```

⚠️ **frontmatter 一律用 `description: |`（literal）而非 `>`（folded）**。詳見 [docs/2026-05-09-install-pitfalls.md](docs/2026-05-09-install-pitfalls.md)。

---

### personal-medical-website

**2026-05-10 新增**

從頭到尾只輸出單一 `index.html`，零 build 步驟，瀏覽器直接開啟。
適合臨床醫師、醫學研究者、雙專長學者建立中文個人作品集 + 知識教育網站。

**內建互動模組：**
- eGFR 計算器（CKD-EPI 2021 無種族因子）
- CKD 分期 Chart.js 水平長條圖（自定義 afterDraw marker plugin）
- 腎元 SVG 動畫（速率與 eGFR 連動）
- 大腦 SVG 互動地圖（6 腦區，點擊後資訊面板滑入）
- 認知功能雷達圖（典型老化 vs MCI 切換）
- 3 題 MCQ 測驗（即時回饋 + 解釋）
- 研究著作垂直時間軸、演講/課程 Tab 頁

**Trigger phrases：** 「幫我做個人網站」、「醫師個人頁面」、「學術作品集」、「互動式自我介紹網站」

**踩坑整理（9 個坑，見 SKILL.md）：** Edit 工具 old_string 精確匹配、圖片上傳路徑、onerror 回退鏈、Chart.js plugin 傳入方式、SVG pointer-events、AOS refresh、Chart destroy/recreate、gh 登入確認、YAML | vs >

#### 安裝

```bash
# macOS/Linux
cp -r personal-medical-website ~/.claude/skills/

# Windows
xcopy /E /I personal-medical-website "%APPDATA%\Claude\skills\personal-medical-website"
```
---

## 每日自動化八件套 Skill（2026-05-13 新增）

針對日常閱讀、寫作、會議、求職、資料分析、Email、知識管理、個人看板等場景設計的八個 Skill。設計上**不依賴外部 LLM API**——Claude Code 本身就執行所有任務,所以零 API 花費、零 token 計算、所有資料留在本地。

每個 Skill 都對應一份常見的 OpenAI API 範例,但設計上做了根本改進:強制零捏造數字、強制業務問題前置、強制使用者干預點、反 LLM 陳腐用詞清單、與其他 Skill 的協作整合點。

### research-organizer

把雜亂的研究素材(論文摘抄、會議筆記、調查資料、TXT/MD/PDF 抽出的文字)整理成結構化、可後續行動的研究筆記。固定 7 個區塊(摘要 / 核心論點 / 技術概念 / 可行動洞察 / 引用金句 / 未解問題 / 連結),空區塊整段刪掉。**節錄勝過改寫**,關鍵句直接引用標來源。

**Portable artifact:** `research-organizer.skill`

---

### article-writer

從一個題目或一份素材生出一篇可發布的長文,先產 outline 讓使用者改,再展開成完整文章。支援多平台格式(Medium / dev.to / LinkedIn / Hugo / Jekyll / Substack)。內建反 LLM 文風清單:`delve into` / `leverage` / `In conclusion` 通通禁掉。

**Portable artifact:** `article-writer.skill`

---

### meeting-minutes

把會議逐字稿、Zoom/Teams 自動轉錄、Otter.ai 匯出整理成結構化、可追蹤、可下次接續的會議紀錄。**強制規則**:每個 action item 必須有負責人 + 期限 + 完成標準。Decision vs Discussion 嚴格區分,保留決策理由。

**Portable artifact:** `meeting-minutes.skill`

---

### resume-tailor

把現有履歷根據特定 JD 做客製化調整——重新排序、調整用詞、補強關鍵字,**但絕不捏造**事實。**鐵則**:原文沒數字就不准加。寫前必跑 gap 分析,讓使用者確認哪些是「履歷沒寫但實際有」、哪些是「真的沒做過」。輸出客製履歷 + 改動清單兩份檔。

**Portable artifact:** `resume-tailor.skill`

---

### knowledge-base

個人知識庫的雙向工具:(A) 把外部素材整理成原子化、可連結、有引用的筆記寫入 Obsidian vault 或本地檔案系統;(B) 從現有知識庫查詢、跨筆記綜整、給出帶引用的答案。**走「結構化 + 連結」路線,不是 vector RAG**——Obsidian wikilinks 比 embedding 更適合個人長期知識管理。

**Portable artifact:** `knowledge-base.skill`

---

### email-assistant

處理 email 工作流——閱讀收件夾、回覆既有 thread、從零寫新信、批次分類待回覆信件。整合 Gmail MCP 讀 thread + 存草稿,**絕不主動寄出**。內建中英文反 LLM email 句型禁用清單(`I hope this email finds you well` / `祝商祺` 等)。

**Portable artifact:** `email-assistant.skill`

---

### data-analyzer

對結構化資料(CSV、Excel、JSON、Parquet、SQLite)做嚴謹的探索性分析。**鐵則:零數字捏造**——所有數字一律來自實際 pandas/numpy/scipy 計算,每個聲稱附 `(computed: ...)` 引用。強制問業務問題後才開跑分析。生成 PNG 視覺化 + Markdown 報告 + 可重跑的 Python 腳本。

**Portable artifact:** `data-analyzer.skill`

---

### dashboard-builder

為使用者建立個人化資訊看板——從既有資料來源(Gmail / Obsidian / Calendar / NotebookLM / 本地檔案)聚合成每日 briefing、每週回顧。**預設 Markdown 不是 Streamlit**(個人 dashboard 不該要求跑 server)。**鐵則:零虛擬資料**——資料來源連不上就顯示「⚠️ 連線失敗 @ 時間」,不留空也不塞假資料。

**Portable artifact:** `dashboard-builder.skill`

---

### 八個 Skill 的協作整合

```
日常閱讀     →  research-organizer    →  研究筆記
                                              ↓
寫作發布     →  article-writer         ←       │
                                              ↓
會議追蹤     →  meeting-minutes        →   決議 + actions
                                              ↓
求職應徵     →  resume-tailor                  │
                                              ↓
持久收藏     →  knowledge-base         ←  ─ ─ ┤  (樞紐)
                                              ↓
日常溝通     →  email-assistant        ←       │
                                              ↓
資訊處理     →  data-analyzer          →   報告 + 圖
                                              ↓
聚合呈現     →  dashboard-builder      ←  匯總前 7 個的輸出
```

### 共同設計原則

1. **零外部 API 依賴**:不呼叫 OpenAI / Gemini / 其他 LLM API——Claude 自己做
2. **零捏造**(資料分析的數字、履歷的成就、Email 的承諾、knowledge-base 的引用、dashboard 的數據)
3. **強制業務問題前置**:在資料分析、文章寫作、dashboard 設計時,先問「要回答什麼問題」
4. **使用者干預點**:長流程一定有暫停讓使用者改方向(outline 階段、gap 分析、triage 分類)
5. **反 LLM 陳腐用詞清單**:每個 Skill 都有對應領域的禁用詞庫
6. **協作整合**:每個 Skill 的輸出都可以是另一個 Skill 的輸入,組成完整工作流
