# Claude Skills

A collection of custom Claude Code skills.

## Skills

### admission-note

Automatically generates a hospital admission note (`.docx`) from patient data provided via:
- Screenshots / images
- Word files (`.docx`)
- Excel files (`.xlsx`)

**Trigger phrases:** "admission note", "住院病歷", "入院紀錄"

**Output:** A formatted Word document with sections:
Chief Complaint, HPI, PMH, PSH, Medications, Allergies, Family History, Social History, Review of Systems, Vital Signs, Physical Examination, Labs, Imaging, Assessment & Plan.

#### Installation

1. Copy the `admission-note/` folder into your Claude Code skills directory:
   ```
   %APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\<session-id>\skills\
   ```
2. Register the skill in `manifest.json` by adding:
   ```json
   { "skillId": "admission-note", "enabled": true }
   ```
3. Restart Claude Code.

Alternatively, use the pre-packaged `admission-note.skill` file.

---

### lecture-notes

Transforms lecture audio recordings and presentation slides (PDF/PPT) into beautifully formatted PDF notes with structured concept maps and organized transcripts.

**Pipeline:**
1. **Audio Transcription** — Groq Whisper API (`whisper-large-v3`)
2. **Slide Extraction** — PyMuPDF text + image extraction
3. **Content Segmentation** — GPT-4o segments transcript into topic sections aligned with slides
4. **Concept Map Generation** — HTML/CSS structured infographics rendered to PNG via Playwright, with optional AI decorative illustrations (DALL-E)
5. **PDF Compilation** — WeasyPrint / Playwright PDF output

**Trigger phrases:** "lecture notes", "課堂筆記", "錄音轉筆記", "上課筆記"

**Required API Keys:**
- Groq API Key (for Whisper STT)
- OpenAI API Key (for GPT-4o segmentation + DALL-E illustrations)

**Quick Start:**
```bash
# Install dependencies
uv pip install groq openai pymupdf pillow jinja2 playwright
playwright install chromium

# Run full pipeline
python lecture-notes/scripts/main.py \
  --audio recording.mp3 \
  --slides slides.pdf \
  --output notes.pdf \
  --groq-key $GROQ_API_KEY \
  --openai-key $OPENAI_API_KEY \
  --title "Course Title" \
  --speaker "Speaker Name" \
  --date "2026-04-01"
```

**Output Style:** Each section contains a bold title, a colorful concept map (parchment background, color-coded nodes, flow arrows), and conversational lecture transcript in Traditional Chinese.

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