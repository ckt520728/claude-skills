---
name: materials-to-pptx
description: Use this skill whenever the user wants to turn raw research/study materials (TXT files, PDF documents, NotebookLM exports, lecture notes, academic summaries, merged text dumps) plus accompanying images (PNG, SVG, JPG) into a polished PowerPoint presentation. Trigger on phrases like "幫我做成 PowerPoint"、"製作簡報"、"把這些資料做成投影片"、"用這個 zip 做 PPT"、"把這份 PDF 整理成簡報"、"這些 TXT 變成投影片"、"NotebookLM 匯出做 PPT"、"上課筆記做投影片"、"研究資料整理成簡報", and similar requests where the deliverable is a .pptx file built from supplied source materials. Also trigger when the user uploads a folder/zip containing TXT/PDF + images and asks for a presentation, or mentions "資料彙整成 PPT", "research 整理成投影片", or wants academic/clinical-style decks generated from merged content. Skill handles: extracting from zip, merging multi-file TXT, reading PDF text, rasterising SVG, designing slide structure, generating via pptxgenjs, embedding images, verifying output, and saving to the user's vault.
---

# Materials to PPTX — 把研究資料變成簡報

把使用者提供的 TXT/PDF 內容 + PNG/SVG 圖片，自動整理成一份結構化、可演講的 PowerPoint。

這份 skill 是從「把 NotebookLM 匯出的 Sussillo 神經科學筆記做成 22 頁學術簡報」的成功流程萃取出來的——已驗證可重現。

---

## 何時觸發這份 skill

當使用者上傳：
- 一個 zip 檔，內含多個 TXT 摘要 + 圖片（典型：NotebookLM 匯出、上課筆記）
- 或一份 merged TXT / PDF + 幾張示意圖
- 或一個資料夾路徑

並要求「做成 PowerPoint / 簡報 / PPT」時。

---

## 工作流程（六步驟）

### 步驟 1：盤點素材

**先別急著寫程式碼**，把所有素材列出來。

```bash
# 解壓 zip（如果是 zip）
EXTRACT="/tmp/<topic>_extracted"; rm -rf "$EXTRACT"; mkdir -p "$EXTRACT"
cd "$EXTRACT" && unzip -q "<path/to/zip>"

# 列出所有檔案類型
find "$EXTRACT" -type f | awk -F. '{print $NF}' | sort | uniq -c

# 找所有圖片
find "$EXTRACT" -iname "*.png" -o -iname "*.jpg" -o -iname "*.svg"

# 找主要文字檔（通常是 merged 或最大的 .txt）
ls -laS "$EXTRACT"/*.txt | head -3
```

**辨識「主文字檔」的線索**：
- 檔名含 `merged`, `combined`, `all`, `complete`
- 檔案明顯比其他大（10×–1000× 以上）
- 內容包含結構化章節（# 開頭）

### 步驟 2：讀懂內容結構

**不要把整個 merged.txt 讀進 context**——可能是上百 MB。改用以下策略：

```bash
# 看主章節骨架
grep -n "^#" "$MAIN_TXT" | head -50

# 看小檔案（個別摘要通常更精煉）
for f in "$EXTRACT"/*.txt; do
    if [ "$f" != "$MAIN_TXT" ] && [ $(stat -c%s "$f") -lt 20000 ]; then
        echo "=== $(basename $f) ==="
        head -5 "$f"
    fi
done

# 找 JSON outline（如果有，通常是最好的結構參考）
cat "$EXTRACT"/*.json 2>/dev/null
```

**目標**：摘要出 5–8 個核心主題，每個主題 1–3 個關鍵點。這些會對應投影片章節。

### 步驟 3：規劃投影片結構

**典型學術/研究簡報結構（15–25 張）**：

| 區塊 | 張數 | 內容 |
|---|---|---|
| 封面 + 大綱 | 2 | 標題、副標、來源、本講大綱 |
| 核心命題 | 1–2 | 一句話總結 / 核心問題 |
| 主要內容 | 8–14 | 每個核心主題 1–3 張 |
| 視覺化重點 | 1–2 | 滿版插入主要 PNG/SVG |
| 評價與展望 | 2–3 | 優缺點 / 臨床應用 / 未來 |
| 參考文獻 | 1 | 表格列出 |

**寫一個 plan 給使用者確認**（除非他們已經明確指示）：

```
我打算做這 N 張：
1. 封面 — ...
2. 大綱 — ...
...
要調整哪幾張？
```

### 步驟 4：選擇配色與字體

**不要每次都用同一個 palette**。根據主題選：

| 主題類型 | 推薦 palette | 範例 |
|---|---|---|
| 學術 / 神經科學 / 嚴謹 | Midnight Executive (`1E2761` + `CADCFC` + `F4B400`) | Sussillo 簡報 |
| 醫學 / 臨床 | Ocean Gradient (`065A82` + `1C7293` + `21295C`) | 病例分析 |
| 復健 / 自然科學 | Forest & Moss (`2C5F2D` + `97BC62` + `F5F5F5`) | 環境議題 |
| 警示 / 重症 | Cherry Bold (`990011` + `FCF6F5` + `2F3C7E`) | 急症報告 |
| 商管 / 企業 | Charcoal Minimal (`36454F` + `F2F2F2` + `212121`) | 一般 |

字體配對：
- **學術**: Georgia (標題) + Calibri (內文) + Consolas (公式/代碼)
- **醫學**: Cambria + Calibri
- **現代**: Trebuchet MS + Calibri

詳見 `references/design_patterns.md`。

### 步驟 5：生成 .pptx

**用 pptxgenjs**（Node.js 套件）。如果已裝就直接用，沒裝就裝：

```bash
node -e "console.log(require('pptxgenjs').version)" 2>/dev/null || npm install -g pptxgenjs
```

**起手式：複製模板再改**

```bash
cp ~/.claude/skills/materials-to-pptx/scripts/build_template.js /tmp/<topic>_pptx/build.js
```

`build_template.js` 已包含：
- LAYOUT_WIDE (13.3 × 7.5 吋) 設定
- 全域 helper：`addSlideTitle()` 標題列、`addFooter()` 頁腳
- 6+ 種驗證過的版面（封面、雙欄、卡片網格、表格、滿版圖、結語）
- 顏色變數區塊（換色只改頂端）

**修改原則**：把模板每張投影片的內容換成這次主題的內容，**不要從零寫**。

詳見 `scripts/build_template.js` 與 `references/design_patterns.md`。

### 步驟 6：驗證與交付

```bash
cd /tmp/<topic>_pptx && node build.js
# 應該印出: PPTX written: ... + Size: ... + Slides: N
```

**必做的驗證**（即使沒有 LibreOffice 可以渲染 PDF）：

```bash
# pptx 本質是 zip，先檢查結構
PPTX="<output_path>.pptx"
unzip -l "$PPTX" | grep -c "slides/slide"      # 應該等於投影片張數
unzip -l "$PPTX" | grep -E "\.png|\.jpg|\.svg" # 確認圖片都嵌入了
unzip -l "$PPTX" | grep -c "notesSlide"        # 確認講者備忘存在
```

**若有 LibreOffice 可裝**，做完整視覺 QA：

```bash
soffice --headless --convert-to pdf "$PPTX"
pdftoppm -jpeg -r 150 "${PPTX%.pptx}.pdf" slide
# 然後用 Read 工具看每張 jpg
```

**搬到使用者目的地**（典型是 vault 的 `創作庫/`）：

```bash
cp "$PPTX" "/g/我的雲端硬碟/Second Brain/創作庫/"
```

---

## PDF 輸入處理

如果使用者給的是 PDF 而非 TXT：

**方法 A：pdftotext（最簡單，poppler 工具）**

```bash
pdftotext -layout "input.pdf" "output.txt"
```

**方法 B：Read 工具讀 PDF（適合短文件）**

如果 PDF 在 20 頁以內，直接：
```
Read({ file_path: "input.pdf", pages: "1-20" })
```

**方法 C：pypdf / pdfplumber**（如果 layout 複雜）

```python
import pypdf
reader = pypdf.PdfReader("input.pdf")
text = "\n".join(p.extract_text() for p in reader.pages)
```

**多份 PDF + 多份 TXT 混合**：把全部讀進來後手動整合成一份「概念摘要」，**不要**把全文塞到 LLM 上下文。

---

## 圖片處理

### PNG / JPG（直接用）

```javascript
// 計算寬度保留長寬比
const origW = 2752, origH = 1536;
const maxH = 5.0;  // inches
const calcW = maxH * (origW / origH);
const centerX = (W - calcW) / 2;

slide.addImage({
  path: 'C:\\path\\to\\image.png',
  x: centerX, y: 1.6, w: calcW, h: maxH
});
```

**先用 `file <image>`** 確認真實尺寸，**不要相信檔名暗示的尺寸**。

### SVG 處理

pptxgenjs 在現代 PowerPoint 上可直接讀 SVG，但 PowerPoint 2019 以下會壞。**為了相容性，建議轉成 PNG**：

```bash
# 用 sharp（npm install -g sharp）
node -e "
const sharp = require('sharp');
sharp('input.svg').resize(2000).png().toFile('output.png')
  .then(() => console.log('done'));
"

# 或用 ImageMagick / Inkscape
inkscape input.svg --export-type=png --export-width=2000 --export-filename=output.png
```

### 多張圖片如何分配

- **1 張 PNG** → 做 1 張滿版視覺化投影片（深色背景襯托）
- **2–3 張** → 各做一張 + 在相關章節的角落引用為示意
- **4+ 張** → 做一張 grid 投影片（2×2 或 3×2）+ 散落於對應章節

---

## 模板可改的部分

`scripts/build_template.js` 設計為「改頂端常數即可換主題」：

```javascript
// 主題配色（換主題只改這裡）
const NAVY = '1E2761';
const ICE = 'CADCFC';
const ACCENT = 'F4B400';
// ...

// 版面（13.3 x 7.5 吋寬版；不改也 OK）
pres.layout = 'LAYOUT_WIDE';
```

接著每張 slide 的 `IIFE` 區塊（`{ let s = pres.addSlide(); ... }`）獨立可替換。新增、刪除、重排都不會互相影響。

---

## 常見陷阱（必看）

1. **檔案路徑**：Node.js 寫檔用 Windows 反斜線並雙重轉義 `'C:\\Users\\...'`，不要用 `/c/Users`（Node 認的是 Windows 原生路徑）。

2. **NODE_PATH for global pptxgenjs**：腳本開頭要加：
   ```javascript
   process.env.NODE_PATH = require('child_process').execSync('npm root -g').toString().trim();
   require('module')._initPaths();
   ```

3. **不要對 pptxgenjs option 物件重複使用**——它會 mutate 物件，第二次呼叫會壞。每次都用 fresh literal 或 helper function。

4. **Hex color 不要加 `#`**——會壞檔案。寫 `'1E2761'` 不是 `'#1E2761'`。

5. **不要用 unicode bullet `•`**——用 `bullet: true` 選項。否則會變成「兩個 bullet」。

6. **大檔案先縮抓重點，不要全文塞進 context**——一個 200 MB 的 merged.txt 不可能讀完。用 `grep -n "^#"` 看骨架就好。

7. **影片檔（.mp4）不要嵌入 pptx**——會讓檔案爆大且常常播不出來。改成「截圖嵌入 + 連結」。

8. **講者備忘要寫**——每張投影片都加 `s.addNotes('...')`。是醫師/講者上台用的提示，比投影片本身更重要。

---

## 為什麼這份 skill 這樣寫

- **「先盤點再寫」** — 直接寫 build.js 容易遺漏重要素材或誤解結構
- **「複製模板再改」** — 從零寫每張投影片排版會 debug 到天荒地老；模板已驗證
- **「驗證 zip 結構」** — 沒 LibreOffice 也能確認檔案沒壞、圖片有嵌、備忘有寫
- **「不要把整份 merged.txt 讀進 context」** — 大型 NotebookLM 匯出常常 100+ MB

---

## 變更紀錄

- **2026-05-06 v1.0** — 初版，從 Sussillo 神經科學簡報（22 張、嵌入 NotebookLM PNG、繁體中文）的成功流程萃取
