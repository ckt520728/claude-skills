# HTML Deck 模式（網頁版互動簡報）

> 使用情境：單一 .html 檔、圖像 base64 內嵌、支援 Chart.js / 可點擊表格 / 影片 / RWD / 一鍵分享 URL
>
> 適用：線上研習、直播教學、互動展演、數據視覺化、跨裝置呈現
> 不適用：對方只能用 PowerPoint、需離線投影但無瀏覽器、講者不熟 HTML

本檔案接續主 SKILL.md 的引擎 1–5，提供 html 模式專屬的引擎三補充規格 + 引擎六執行流程。

---

## 必守的設計憲法（html 模式專屬）

### A. 林長揚 30 原則 → CSS 對應表

| # | 原則 | 實作方式 |
|---|------|----------|
| #1 | 字級階層 55 / 34 / 21 / 13 | CSS 變數 `--t1: 55px; --t2: 34px; --t3: 21px; --t4: 13px` |
| #3 | 標題 ≤ 10 字 | 每頁主標壓在 10 字內 |
| #4 | 一張一重點 | 每頁只一個主訊息 |
| #6 | 內容有層級 | kicker（小標）→ h2（主標）→ 內文 → 註解 |
| #13 | Z 字排版 | 連續詳解頁，左圖右文 ↔ 左文右圖 交錯 |
| #14 | 元素對齊 | 三欄卡用 `display:grid` 嚴格對齊 |
| #15 | 圖看趨勢 | Chart.js 雷達圖、折線圖代替數字表 |
| #17 | 表格框線越少越好 | 只留 `border-bottom`，移除外框 |
| #18 | 多圖對齊、人像切圓 | `aspect-ratio:1/1; border-radius` |
| #19 | 三方案讓觀眾選 | 決策頁用 3 張並排卡 + SVG 連線 |
| #20 | 用問句促進思考 | 痛點頁、決策頁用大問句開場 |
| #23 | 進度條減壓 | 頂部 3px 漸層條 + 章節標籤 |
| #24-26 | 強調色 1-2 種 | 1 主 cyan + 1 輔 magenta，其餘淡灰 |
| #27 | 滿版圖片 | 用於封面、段落分隔、結尾 |
| #28 | 用比較幫判斷 | 對比表 + 對比視覺圖搭配 |
| #30 | 推動下一步行動 | 結尾必有 CTA |

### B. SOIL 三段式脈絡（必照順序）

- **引起動機**（20%）：封面 → 痛點問句 → 核心命題
- **維持注意**（50%）：總覽 → 詳解（Z 字排版）→ 對比 → 視覺化
- **喚起行動**（30%）：決策樹 → 方法論流程 → CTA 結語

左上角必設**章節標籤**，即時顯示當前段落（`— 引起動機 —` 等）。

---

## 引擎三補充：每頁要產出 interactive 與 visual 標記

每頁除了主 SKILL.md 列的共用欄位，**額外**指定：

- **interactive**：互動元件類型（chart、sortable_table、svg_decision_tree、video、none）
- **visual_role**：AI 圖角色（cover_full、hero_split、card_thumb、divider_full、none）
- **chart_config**（若 interactive=chart）：Chart.js 設定（type、data、options 簡述）

### 章節骨架輸出格式（給使用者確認）

```
## 章節骨架（共 N 頁）

### 第 1 頁（引起動機）：標題≤10 字
- 核心訊息：1-2 句
- AI 圖：cover_full（封面滿版）
- 互動：none

### 第 2 頁（引起動機）：痛點問句
- 核心訊息：...
- AI 圖：hero_split（左半）
- 互動：none

### 第 5 頁（維持注意）：三類比較
- 核心訊息：...
- AI 圖：card_thumb × 3
- 互動：sortable_table

### 第 8 頁（維持注意）：數據視覺化
- 核心訊息：...
- AI 圖：none
- 互動：chart（Chart.js 雷達圖）

### 第 11 頁（喚起行動）：決策樹
- 核心訊息：...
- AI 圖：none
- 互動：svg_decision_tree（中央問句 + 3 結果卡）
...
```

**等使用者點頭再進下一步。**

---

## 引擎五補充：CSS 變數區塊

```css
:root{
  --bg:#0a0e27; --bg-2:#11163a;
  --ink:#eef3ff; --ink-2:#b8c5e0; --ink-3:#7a8bb8; --ink-4:#4a5680;
  --accent:#00d4ff;   /* 主強調色，僅 1 種 */
  --accent-2:#ff006e; /* 輔強調色，僅 1 種 */
  --t1:55px; --t2:34px; --t3:21px; --t4:13px;
  --s1:80px; --s2:48px; --s3:24px; --s4:12px;
}
```

### 預設風格（「現代深色 + 霓虹點綴」）

| 項目 | 值 |
|------|----|
| 背景 | `#0a0e27`（深藍黑）|
| 主色 | `#00d4ff`（霓虹青）|
| 輔色 | `#ff006e`（亮粉）|
| 警示 | `#ffb800` / `#ff4466` |
| 標題字體 | `Noto Sans TC` 700/900 |
| 內文字體 | `Noto Sans TC` 400 |
| Mono 字體 | `JetBrains Mono`（kicker、頁碼、tag）|
| 卡片 | 玻璃擬態（`backdrop-filter: blur(10px)`）|

---

## 引擎六：HTML 版總導演（H-1 → H-6）

### H-1：批次平行生圖（用 draw skill）

**所有圖像呼叫一次性平行發出**，不要序列等待。預設：

- `--quality low`（99% 場景夠用）
- `--size 1536x1024`（滿版／對比圖）或 `1024x1024`（類型卡）
- 存到 `slides/generated/`

**Prompt 原則**：
- 風格詞統一（例：`Premium futuristic tech aesthetic, dark navy background, cyan and magenta neon accents`）
- 寫明 `No readable text`（避免亂碼文字）
- 留出文字疊放區域（`with negative space at bottom for text overlay`）
- 比例配合用途（滿版用 16:9，卡片用 1:1）

範例：

```bash
mkdir -p slides/generated
DRAW="python C:/Users/mathr/.claude/skills/draw/draw.py"

# 並行批次（用 & + wait）
$DRAW "Premium futuristic tech cover, dark navy background, cyan neon accent, abstract data flow, no readable text" \
  --size 1536x1024 --quality low --name slide-1-cover --outdir slides/generated/ &

$DRAW "Three category icons set, dark navy, cyan and magenta gradients, no readable text" \
  --size 1024x1024 --quality low --name slide-5-card1 --outdir slides/generated/ &

$DRAW "Comparison illustration showing old vs new approach, dark navy, cyan vs magenta, no readable text" \
  --size 1536x1024 --quality low --name slide-7-compare --outdir slides/generated/ &

wait
ls slides/generated/*.png
```

### H-2：Base64 內嵌圖像（**關鍵步驟**）

> ⚠️ **不要用相對路徑。** 預覽面板、檔案搬移、跨環境分享都會壞掉。
> 一律用 Pillow 壓縮 + base64 內嵌成 `data:image/jpeg;base64,...`：

```python
from PIL import Image
import base64, io
from pathlib import Path

def to_data_uri(path: str, full_bleed: bool = False) -> str:
    img = Image.open(path).convert('RGB')
    w, h = img.size
    target_w = 1280 if full_bleed else 900
    if w > target_w:
        img = img.resize((target_w, int(h*target_w/w)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=78, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"

# 把所有圖編碼成 dict，準備塞進 HTML 模板
images = {}
for png in Path("slides/generated").glob("*.png"):
    full_bleed = "cover" in png.stem or "divider" in png.stem
    images[png.stem] = to_data_uri(str(png), full_bleed)

print(f"已編碼 {len(images)} 張圖")
```

5 張圖內嵌後 HTML 約 1.3–1.6 MB，完全可攜。

### H-3：產出單一 HTML（架構模板）

**整體結構**：

```html
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SOIL 簡報</title>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    /* 引擎五的 :root CSS 變數 */
    /* slide 容器、章節標籤、進度條、頁碼 */
  </style>
</head>
<body>
  <div id="progress"></div>          <!-- 頂部進度條 #23 -->
  <div id="section-tag"></div>       <!-- 左上 SOIL 章節標籤 -->
  <div id="pageInfo"></div>          <!-- 右下頁碼 -->
  <div id="hint"></div>              <!-- 左下快捷鍵提示 -->

  <section class="slide active" data-slide="1" data-section="引起動機">...</section>
  <section class="slide" data-slide="2" data-section="引起動機">...</section>
  <section class="slide" data-slide="3" data-section="維持注意">...</section>
  ...

  <script>
    /* 切頁邏輯、Chart.js 初始化、可排序表、SVG 決策樹 */
  </script>
</body>
</html>
```

### H-4：slide 容器 CSS（**滿版，不要做 1920×1080 縮放**）

```css
.slide{
  position:absolute; inset:0;
  display:flex; align-items:center; justify-content:center;
  padding:80px 100px;
  opacity:0; pointer-events:none;
  transition:opacity .55s ease, transform .55s ease;
  transform:translateY(16px);
  overflow:hidden;
}
.slide.active{ opacity:1; pointer-events:auto; transform:translateY(0); }
.slide-inner{ width:100%; max-width:1320px; }
```

> ⚠️ **不要使用固定 1920×1080 + scale 縮放舞台的架構。**
> 在小型預覽面板（如 Claude Code 的 Launch preview）會被縮成極小，字會擠成一團。
> 直接用 `position:absolute; inset:0` 滿版。

### H-5：必備 UI 功能（JS）

1. **左右鍵 / 空白鍵切頁**（`keydown` 事件）
2. **點擊畫面左右側切頁**（`x > 0.7*innerWidth → next`）
3. **F 鍵全螢幕**
4. **頁碼顯示**（右下角 `當前 / 總數`）
5. **頂部進度條**（切頁時動畫）
6. **章節標籤**（左上，讀 `data-section` 即時切換）
7. **每頁淡入動畫**

範例 JS 骨架：

```javascript
const slides = document.querySelectorAll('.slide');
const total = slides.length;
let current = 0;

function go(idx) {
  current = (idx + total) % total;
  slides.forEach((s, i) => s.classList.toggle('active', i === current));
  document.getElementById('progress').style.width = `${(current+1)/total*100}%`;
  document.getElementById('section-tag').textContent =
    '— ' + slides[current].dataset.section + ' —';
  document.getElementById('pageInfo').textContent = `${current+1} / ${total}`;
  // 切到該頁才初始化 Chart.js（lazy）
  initChartIfNeeded(slides[current]);
}

document.addEventListener('keydown', e => {
  if (e.key === 'ArrowRight' || e.key === ' ') go(current + 1);
  if (e.key === 'ArrowLeft')                   go(current - 1);
  if (e.key === 'f' || e.key === 'F') document.documentElement.requestFullscreen();
});

document.addEventListener('click', e => {
  if (e.target.closest('a,button,input')) return;
  if (e.clientX > innerWidth * 0.7)      go(current + 1);
  else if (e.clientX < innerWidth * 0.3) go(current - 1);
});

go(0);
```

### H-6：加入互動元件（這就是本模式的價值）

依章節骨架，在對應頁加入：

| 元件 | 適用頁型 | 實作 |
|------|----------|------|
| **三欄卡片** | 總覽頁、決策頁 | `display:grid; grid-template-columns:repeat(3,1fr)` + AI 圖嵌入卡內 |
| **左右並排圖文** | 類型詳解頁 | `display:grid; grid-template-columns:1fr 1fr` + Z 字翻轉 |
| **可排序表格** | 對比頁 | 點 `<th>` 觸發 sort，搭配 AI 對比視覺圖 |
| **Chart.js 雷達 / 折線圖** | 數據頁 | lazy render（切到該頁才初始化）|
| **SVG 決策樹** | 決策頁 | 中央問句 + SVG `<line>` 連到三張結果卡 |
| **滿版背景圖** | 封面、結尾 | 圖層 `position:absolute;inset:0` + 漸層遮罩 |
| **流程卡 2×3 grid** | 方法論頁 | 不要用 1×6，會太擠 |

#### Chart.js lazy render 範例

```javascript
const chartInitMap = new Map();
function initChartIfNeeded(slide) {
  const canvas = slide.querySelector('canvas[data-chart]');
  if (!canvas || chartInitMap.has(canvas)) return;
  const cfg = JSON.parse(canvas.dataset.chart);
  new Chart(canvas, cfg);
  chartInitMap.set(canvas, true);
}
```

---

## H-7：版面溢出檢查（逐頁驗收）

每頁打開後檢查：
- [ ] 內容是否在標準 1920×1080 / 1366×768 視窗下完整顯示
- [ ] 沒有元素被視窗高度截掉
- [ ] 字級階層清楚（主標明顯大於內文）
- [ ] 圖文比例舒適（不擠不空）
- [ ] 章節標籤、頁碼、進度條都正常更新

如果某頁溢出，**優先做的事**：
1. 換成 2×N grid（避免 1×N 一字排開太擠）
2. 把長文字拆成兩頁
3. 縮短 padding（從 100px → 60px）
4. 圖片改成 `aspect-ratio:1/1` 縮成正方形

> ⚠️ **不要動全域字級變數來救溢出**，那會破壞整體階層。

---

## H-8：驗收與輸出

1. 用 Bash 開啟產出的 HTML
   - Windows：`start slides.html`
   - macOS：`open slides.html`
   - Linux：`xdg-open slides.html`
2. 切完每一頁，確認互動元件都正常
3. 報告檔案路徑與功能清單給使用者

---

## 輸出規範

```
專案資料夾/
├── slides.html              ← 單一 HTML（base64 內嵌圖，~1.5 MB）
├── slides/
│   └── generated/           ← AI 生成圖原始 PNG（備份用）
│       ├── slide-1-cover.png
│       └── ...
└── README.md                ← 使用說明 + 鍵盤快捷鍵
```

---

## 給其他 Agent 的呼叫提示

如本模式被其他 agent（如 GPT Codex）讀取使用，請遵守：

1. 每頁的 HTML 結構必須一致（`<section class="slide" data-slide="N" data-section="...">`）
2. 圖像一律 base64 內嵌，**不用相對路徑**
3. 所有 JS / CSS 內嵌或用 CDN（Chart.js / Google Fonts），不要產生需要 build 的 React/Vue 專案
4. 預設輸出單一 `.html`，使用者要的是「打開即用」，不是 dev server
5. 不要用固定 1920×1080 + transform scale 的架構，直接用 `position:absolute; inset:0` 滿版
6. 每頁要遵守林長揚 30 原則 + SOIL 三段式脈絡

---

## 踩坑紀錄（2026-05-02 直播 demo 累積）

| 坑 | 解法 |
|----|------|
| 預覽面板看不到圖（中文路徑或沙箱） | base64 內嵌，**不用** 相對路徑 |
| AI 圖只當背景太可惜 | 用 grid 把圖跟內容區塊**並排融合**，圖片要切圓角 + 加角標 |
| 1920×1080 scale 在小視窗變超小 | 改用滿版 `inset:0`，內容跟視窗撐滿 |
| 決策樹用 ASCII 字符不夠視覺 | 改成中央問句 + SVG 連線 + 三張顏色不同的結果卡 |
| 6 引擎排成 1×6 太擠 | 改 2×3 grid，搭配左側 AI 視覺圖 |
| 對比頁只有表格太枯燥 | 左側放「左舊右新」對比視覺圖，右側放可排序表 |
| 標題太長破版 | 嚴守 ≤10 字原則 |
| 強調色超過 2 種畫面亂 | 主 cyan + 輔 magenta + 警示色，其餘一律淡灰 |

---

## 最終檢查清單（html 模式）

- [ ] 每頁只有一個主重點
- [ ] 三段式脈絡完整（動機→注意→行動）
- [ ] 所有圖 base64 內嵌、無相對路徑
- [ ] slide 容器是 `position:absolute; inset:0` 滿版（非 1920×1080 scale）
- [ ] 左右鍵 / 空白鍵 / 點擊兩側 / F 全螢幕全部能用
- [ ] 章節標籤、進度條、頁碼即時更新
- [ ] Chart.js / sortable_table / SVG 決策樹（如有）lazy render 不卡頓
- [ ] 1920×1080 與 1366×768 兩種視窗下無溢出
- [ ] 林長揚 #1 字級階層、#3 標題 ≤ 10 字、#13 Z 字、#23 進度條、#25 強調色 ≤ 2、#30 結尾 CTA
- [ ] HTML 大小合理（10 頁約 1.3–1.6 MB）
