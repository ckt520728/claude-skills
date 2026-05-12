---
name: lecture-notes
description: |
  Generate beautifully formatted lecture notes (PDF/PPTX) from audio recordings and presentation slides,
  using NotebookLM's multimodal understanding and Slide Deck generator (powered by Gemini + Nano Banana
  image generation). Produces illustrated, structured notes in 黃鍔院士-report style.

  USE THIS SKILL whenever the user wants to:
  - Convert lecture recordings into formatted notes
  - Create lecture notes from audio + slides
  - Transcribe a class recording and make study notes
  - Generate visual concept maps / illustrated slides from lecture content
  - Turn a presentation + recording into a study document
  - Process 錄音檔/上課錄音 into 筆記/講義
  - Create 課堂筆記 from 投影片 and 錄音

  Also trigger when the user mentions: lecture notes, class notes, 課堂筆記, 上課筆記, 講義製作,
  錄音轉筆記, 投影片筆記, 黃鍔院士筆記風格.
---

# Lecture Notes Generator (NotebookLM-powered)

Transform a lecture audio recording + presentation slides into an illustrated notes document.
Uses NotebookLM under the hood — its Slide Deck generator handles transcription, segmentation,
concept mapping, and illustration (via Nano Banana) in one step, producing higher-quality output
than a self-built Groq+OpenAI pipeline.

## Required Inputs

| Input | Format | Required |
|-------|--------|----------|
| Audio recording | `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac` | Yes |
| Presentation slides | `.pdf` (convert from PPT first if needed) | Yes |
| Course / speaker / date | Text | Optional (passed into focus_prompt) |

If given a `.pptx`, convert to PDF first:
`soffice --headless --convert-to pdf <file>` (LibreOffice).

## Tools Used

All from the `notebooklm-mcp` MCP server (prefix `mcp__notebooklm-mcp__`):
- `notebook_create` — create a new notebook
- `source_add` (source_type=`file`) — upload audio + PDF
- `studio_create` (artifact_type=`slide_deck`) — generate illustrated slide deck
- `studio_status` — poll generation progress
- `download_artifact` — download final PDF/PPTX

## Workflow

### Step 1: Create Notebook

```
mcp__notebooklm-mcp__notebook_create(title="<課程名>-<日期>-<講者>")
```
Save the returned `notebook_id`.

### Step 2: Upload Sources (in parallel)

Upload both files with `wait=True` so processing finishes before moving on. These can be
called in the same tool-call turn (parallel).

```
mcp__notebooklm-mcp__source_add(
  notebook_id=<id>, source_type="file",
  file_path="<audio path>", wait=True, wait_timeout=600
)
mcp__notebooklm-mcp__source_add(
  notebook_id=<id>, source_type="file",
  file_path="<slides PDF path>", wait=True, wait_timeout=300
)
```

Audio transcription inside NotebookLM takes longer than PDF ingest — bump `wait_timeout`
for large recordings (>1 hr audio can need 600s+).

### Step 3: Generate Slide Deck

```
mcp__notebooklm-mcp__studio_create(
  notebook_id=<id>,
  artifact_type="slide_deck",
  slide_format="detailed_deck",
  slide_length="default",
  language="zh-TW",
  focus_prompt=<STYLE_PROMPT>,
  confirm=True
)
```

Use **this `focus_prompt`** (tuned to the 黃鍔院士 report style the user wants):

> 請製作一份繁體中文的課堂筆記投影片，風格模仿學術報告手寫筆記：
> 1. 每個主題一頁，頁首是簡潔有力的中文標題（例如「三大研究假設」「反應時間分析」）
> 2. 主體是一張彩色的結構化概念圖，用方框、箭頭、分組表現概念之間的關係
> 3. 色彩語義：紅=關鍵字/核心概念、綠=補充說明、藍=流程/連結、橘=警告、紫=人物/歷史
> 4. 中文為主，重要英文術語用括號標註（例如「素流 (Turbulence)」）
> 5. 保留講者的語氣、比喻、例子和個人軼事，不要過度摘要
> 6. 遇到公式、統計結果（p值、相關係數、AUC 等）要直接呈現
> 7. 每張投影片底部加一句 key takeaway 總結該主題
> 8. 頁面背景可以用米白/羊皮紙色調，排版寬鬆不擁擠
> 9. 搭配插圖：對比喻、流程、物體可用手繪風格小插圖（避免寫實人臉）
>
> 章節結構參考：課程介紹 → 背景理論 → 研究假設 → 方法 → 結果 → 討論 → 結論

If the user provides context/date/speaker, prepend them to the prompt:
> 本筆記來自 <講者> 於 <日期> 的報告：<課程/主題>。

### Step 4: Poll Until Ready

```
mcp__notebooklm-mcp__studio_status(notebook_id=<id>)
```

Slide deck generation typically takes 2–8 minutes. Find the artifact of type `slide_deck`
and check `status == "completed"`, then grab its `artifact_id`.

Use `ScheduleWakeup(delaySeconds=270)` between polls (stays in 5-min cache window).
Don't poll tighter than 60s.

### Step 5: Download

Default: PDF
```
mcp__notebooklm-mcp__download_artifact(
  notebook_id=<id>,
  artifact_type="slide_deck",
  artifact_id=<id>,
  output_path="<course>_筆記.pdf",
  slide_deck_format="pdf"
)
```

Ask whether they also want `.pptx` — if yes, call again with `slide_deck_format="pptx"`.

### Step 6 (Optional): Companion Artifacts

Offer these extras (same notebook, no re-upload):
- `artifact_type="audio"` → podcast-style deep-dive (good for commute review)
- `artifact_type="report"`, `report_format="Study Guide"` → written study guide
- `artifact_type="mind_map"` → overall mind map for whole lecture
- `artifact_type="flashcards"` → active-recall cards

## Poll-and-Wait Pattern

`studio_create` is asynchronous. Confirm the call succeeded, then poll `studio_status`.
Prefer `ScheduleWakeup` with `delaySeconds=270` over tight polling loops. Typical total
wall time: **5–15 minutes per slide deck**.

## Error Handling

- **Source upload fails / timeout**: large audio (>1 hr) may need `wait_timeout=900`. If still
  failing, split audio first (`ffmpeg -i in.mp3 -ss <start> -t <dur> -c copy chunk.mp3`) and upload
  segments.
- **`studio_create` returns `awaiting_confirmation`**: must pass `confirm=True`.
- **Artifact stuck in_progress >20 min**: re-run `studio_create` — NotebookLM occasionally drops jobs.
- **Language comes out in English**: pass `language="zh-TW"` AND include 繁體中文 instruction
  in `focus_prompt`.

## Style Tuning

The `focus_prompt` is the main lever. If output is wrong:
- Too summary-like → add 「保留講者原話和例子，不要過度濃縮」
- Too plain / no illustrations → add 「每頁加入手繪風格小插圖表達概念比喻」
- Wrong colour scheme → specify colours explicitly
- Too many/few slides → tune `slide_length` (short|default)

When the user approves a `focus_prompt` variant, save it to `references/<name>-prompt.md`
so it becomes reusable.

## Fallback: Self-Built Pipeline

If NotebookLM MCP is unavailable or explicitly requested, legacy Groq+OpenAI scripts live in
`scripts/` (transcribe.py, extract_pdf.py, segment.py, generate_concept_map.py, compile_pdf.py).
Requires GROQ_API_KEY and OPENAI_API_KEY. Lower illustration quality. Only use as last resort —
see `scripts/README.md` for the old workflow.
