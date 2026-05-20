# 設計模式參考（針對 build_template.js）

這份檔案專門講「在 `build_template.js` 裡可以重用的版面模式」與「換主題時改什麼」。

---

## 換主題：只動頂端 5 個常數

```javascript
const NAVY = '1E2761';      // 主色（深）
const NAVY_DEEP = '14193F'; // 更深背景（封面、深色頁）
const ICE = 'CADCFC';        // 副色（淺）
const ACCENT = 'F4B400';     // 重點色（裝飾、年份標籤）
// 其他色（基本不動）：WHITE, TEXT_DARK, TEXT_MUTED, BG_LIGHT, RULE
```

### 配色備選（複製貼上替換上面 4 行）

**Midnight Executive（學術，預設）**
```javascript
const NAVY = '1E2761'; const NAVY_DEEP = '14193F';
const ICE = 'CADCFC'; const ACCENT = 'F4B400';
```

**Ocean Gradient（醫學/臨床）**
```javascript
const NAVY = '065A82'; const NAVY_DEEP = '21295C';
const ICE = 'B8DDEE'; const ACCENT = 'F4B400';
```

**Forest & Moss（自然/復健）**
```javascript
const NAVY = '2C5F2D'; const NAVY_DEEP = '1A3D1A';
const ICE = 'D6E5C2'; const ACCENT = 'F96167';
```

**Cherry Bold（急症/警示）**
```javascript
const NAVY = '990011'; const NAVY_DEEP = '5C0009';
const ICE = 'FCD9DD'; const ACCENT = 'F4B400';
```

**Charcoal Minimal（商管）**
```javascript
const NAVY = '36454F'; const NAVY_DEEP = '212121';
const ICE = 'D3D9DD'; const ACCENT = 'D4A017';
```

---

## 字體配對（換字型只動 3 行）

```javascript
const HFONT = 'Georgia';     // 標題字型
const BFONT = 'Calibri';     // 內文字型
const MONOFONT = 'Consolas'; // 代碼/公式字型
```

| 風格 | HFONT | BFONT |
|---|---|---|
| 學術正統（預設） | Georgia | Calibri |
| 醫學嚴謹 | Cambria | Calibri |
| 現代簡潔 | Trebuchet MS | Calibri |
| 強烈個性 | Impact | Arial |
| 古典優雅 | Palatino | Garamond |

---

## 模板內建的 8 種版面

每種對應 `build_template.js` 內一個 IIFE 區塊。換內容時找最像的版面複製改。

### 1. 封面（深色全屏 + 金色裝飾條）
**用於**：第一張投影片  
**特徵**：左側金色直條 + 大標 56pt + 副標 38pt + 來源資訊

### 2. 大綱（2×3 卡片網格）
**用於**：第二張，目錄  
**特徵**：6 張卡片，每張左側有大數字 + 標題 + 一行描述

### 3. 雙卡並列（Q1 / Q2 對比）
**用於**：核心問題、雙主題對比  
**特徵**：兩張等寬大卡，Q1/Q2 大徽章、頂部色條、長描述

### 4. 深色全頁引言（金色裝飾撇號）
**用於**：一句話總結、強烈聲明  
**特徵**：深背景 + 巨大撇號 `"` + 多色階層段落 + 細分隔線

### 5. 三柱式（年份卡片）
**用於**：三大貢獻 / 三階段歷程  
**特徵**：3 張等寬卡，每張有頂部深色標題列含年份徽章 + 中央英文副標 + 金色細分隔 + 底部描述

### 6. 時間軸（4×2 格 + 連接箭頭）
**用於**：歷史演進、研究脈絡  
**特徵**：8 個時間格，每格深色年份徽章 + 標題 + 描述；同列之間有金色右箭頭

### 7. 滿版圖片視覺化
**用於**：嵌入主要 PNG/SVG  
**特徵**：深色背景 + 標題在頂、圖在中、caption 在底；圖長寬比保留

### 8. 對比表格 / 數據表
**用於**：方法論比較、文獻清單  
**特徵**：addTable() + 表頭深色 + 資料列輪替 + 評分用紅綠

---

## 版面選擇決策樹

```
要呈現的是…
├── 一句很重要的話 → 第 4 種（深色引言）
├── 多個並列概念
│   ├── 2 個 → 第 3 種（雙卡）
│   ├── 3 個 → 第 5 種（三柱）
│   ├── 4 個 → 2×2 卡片網格（修改第 2 種）
│   ├── 5 個 → 5 卡並列（橫向）
│   └── 6+ 個 → 第 2 種（2×3）或 3×2
├── 時序 / 流程
│   ├── 線性 4-8 步 → 第 6 種（時間軸）
│   └── 3 步 → 三步驟卡（修改第 5 種，把年份換成數字）
├── 對照比較
│   ├── 兩方對立 → 第 3 種雙卡（左紅右綠）
│   ├── 多列數據 → 第 8 種（表格）
│   └── 問題→解答 → 三段式：問題卡 + 箭頭 + 解答卡
├── 重點圖片 → 第 7 種（滿版圖）
└── 結論 / 致謝 → 第 4 種（深色全頁）
```

---

## 字級規範（這個尺寸下視覺最舒服）

| 元素 | 字級 | 粗細 |
|---|---|---|
| 封面主標 | 56pt | bold |
| 封面副標 | 38pt | normal |
| 投影片標題 | 28pt | bold |
| 投影片副標 | 13pt | italic |
| 大型數字 / 引言 | 36–48pt | bold |
| 區段標題 | 18–22pt | bold |
| 卡片標題 | 14–16pt | bold |
| 內文 | 12–13pt | normal |
| 副註 / 圖說 | 10–11pt | italic |
| 頁腳 | 9pt | normal |

---

## Sandwich 結構（強烈建議）

把投影片分成「深淺夾心」：

```
深 — 封面
淺 — 大綱
淺 — 內容 1
淺 — 內容 2
深 — 一句話總結（強調）
淺 — 內容 3
...
深 — 未來展望（結論）
淺 — 參考文獻
```

**規則**：每 5–8 張淺色內容，插一張深色（強調 / 過渡）。讓觀眾的眼睛有節奏感。

---

## 圖片尺寸計算（保留長寬比）

```javascript
const origW = 2752, origH = 1536;  // 原圖實際像素
const maxH = 5.0;                   // 想要的最大高（吋）
const calcW = maxH * (origW / origH);
const centerX = (W - calcW) / 2;    // W 是 slide 寬

slide.addImage({
  path: imgPath,
  x: centerX, y: 1.6, w: calcW, h: maxH
});
```

**先跑一次** `file <image>` 確認真實尺寸：

```bash
file "your_image.png"
# 範例輸出：PNG image data, 2752 x 1536, 8-bit/color RGB, non-interlaced
```

---

## 講者備忘的範本

每張投影片都要 `s.addNotes('...')`。範本：

```
[這張的核心訊息]。[要強調什麼 / 為什麼放這裡]。
```

範例：
- 封面：「揭示主題核心——Sussillo 將大腦皮層的高維神經計算，從實驗現象提升為可逆向工程的動力系統理論。」
- 三柱式：「三大貢獻彼此承接：FORCE 是工具、DSA 是理論、CTD 是框架。」
- 結論：「Sussillo 把研究弧線拉到 NeuroAI 的最遠端，這也是領域融合的方向。」

**寫作原則**：1–2 句，講「為什麼這張在這裡」而不是重複投影片內容。

---

## QA 檢查清單

跑完 `node build.js` 後：

- [ ] 終端機輸出無 ERROR
- [ ] `Slides:` 數字符合預期
- [ ] `unzip -l <pptx> | grep -c "slides/slide"` 等於投影片張數
- [ ] `unzip -l <pptx> | grep -E "\.png|\.jpg"` 列出所有預期的圖片
- [ ] `unzip -l <pptx> | grep -c "notesSlide"` 等於投影片張數（每張都有備忘）
- [ ] 檔案大小合理（純文字 ~200 KB，含 1 張大圖 ~5–10 MB）
- [ ] 在 PowerPoint 開檔不報錯
- [ ] 視覺檢查至少封面、大綱、滿版圖、結論 4 張

如果有 LibreOffice：

```bash
soffice --headless --convert-to pdf "<pptx>"
pdftoppm -jpeg -r 150 "<pdf>" slide
ls slide-*.jpg | xargs -I {} echo "$(pwd)/{}"
# 用 Read 工具看每張 jpg
```
