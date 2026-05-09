---
name: soil-html-deck
description: |
  HTML 簡報技能(自由度天花板)。用單一 HTML 檔案模擬簡報的呈現邏輯,
  圖像由 gpt-image-2 生成並 base64 內嵌,排版/文字/互動全部由 HTML + CSS + JS 處理,
  支援互動圖表(Chart.js)、可點擊表格、影片嵌入、RWD 跨裝置、一鍵分享 URL。
  當使用者說「做 HTML 簡報」、「網頁版簡報」、「互動式簡報」、「線上簡報」、
  「可分享連結的簡報」、「要有互動圖表的簡報」、「不受 PowerPoint 限制的簡報」、
  「最自由的簡報格式」、「直播用的簡報」、「研習線上版簡報」時,
  請一定要使用此技能。
  本技能與 soil-image-deck(全圖 .pptx)、soil-teaching-deck(可編輯 .pptx)的差別:
  本技能輸出是單一 .html,自由度最高、可嵌互動、可立即線上分享,
  但需要瀏覽器環境播放,不適合給只用 PowerPoint 的對象。
---

# SOIL HTML 簡報工作流(soil-html-deck)

以 SOIL 教學設計邏輯為骨架,用 **HTML + gpt-image-2 圖像 + JS 互動** 產出單一 `.html` 簡報檔。
所有設計決策都遵循 **林長揚 30 原則** 與 **SOIL 六引擎**。

> **三種 SOIL 簡報技能的分工**
> - `soil-image-deck`:每頁一張 AI 圖,打包成 .pptx(無法編輯)
> - `soil-teaching-deck`:AI 圖 + 可編輯 PowerPoint 文字物件
> - `soil-html-deck`(本技能):單一 .html,自由度最高、可互動、可線上分享

---

## 適用情境

| 情境 | 為什麼用本技能 |
|------|----------------|
| 線上研習 / 直播教學 | 觀眾用手機/電腦打開 URL 即可同步看 |
| 互動展演 | 嵌入 Chart.js 互動圖表、可點擊表格 |
| 數據視覺化導向 | HTML 原生支援 SVG / Canvas / D3 |
| 想脫離 PowerPoint 框架 | 任何網頁能做的,簡報就能做 |
| 跨裝置呈現 | RWD,手機平板桌機都能看 |

**不適用**:對方只能用 PowerPoint 接收檔案、需要離線投影但無瀏覽器、講者不熟悉 HTML 排版。

---

## 輸入

使用者需提供:
- **內容素材**(必要):Markdown / `.mb` / `.md` 大綱檔,或一段主題描述
- **頁數預期**(選填,預設 8-12 頁)
- **風格關鍵字**(選填,例:「黑板粉筆」「日系扁平」「電影感」「科技藍」)
- **輸出檔名**(選填,預設 `slides.html`)

---

## 必守的設計憲法

### A. 林長揚 30 原則(必套用清單)
| # | 原則 | 實作方式 |
|---|------|----------|
| #1 | 字級階層 55 / 34 / 21 / 13 | CSS 變數 `--t1: 55px; --t2: 34px; --t3: 21px; --t4: 13px` |
| #3 | 標題 ≤10 字 | 每頁主標壓在 10 字內 |
| #4 | 一張一重點 | 每頁只一個主訊息,不堆疊 |
| #6 | 內容有層級 | kicker(小標)→ h2(主標)→ 內文 → 註解 |
| #13 | Z 字排版 | 連續類型詳解頁,左圖右文 ↔ 左文右圖 交錯 |
| #14 | 元素對齊 | 三欄卡用 `display:grid` 嚴格對齊 |
| #15 | 圖看趨勢 | Chart.js 雷達圖、折線圖代替數字表 |
| #17 | 表格框線越少越好 | 只留 `border-bottom`,移除外框 |
| #18 | 多圖對齊、人像切圓 | `aspect-ratio:1/1; border-radius` |
| #19 | 三方案讓觀眾選 | 決策頁用 3 張並排卡 + SVG 連線 |
| #20 | 用問句促進思考 | 痛點頁、決策頁用大問句開場 |
| #23 | 進度條減壓 | 頂部 3px 漸層條 + 章節標籤 |
| #24-26 | 強調色 1-2 種 | 1 主 cyan + 1 輔 magenta,其餘淡灰 |
| #27 | 滿版圖片 | 用於封面、段落分隔、結尾 |
| #28 | 用比較幫判斷 | 對比表 + 對比視覺圖搭配 |
| #30 | 推動下一步行動 | 結尾必有 CTA |

### B. SOIL 三段式脈絡(必照順序)
- **引起動機**(20%):封面 → 痛點問句 → 核心命題
- **維持注意**(50%):總覽 → 詳解(Z 字排版)→ 對比 → 視覺化
- **喚起行動**(30%):決策樹 → 方法論流程 → CTA 結語

左上角必設章節標籤,即時顯示當前段落(`— 引起動機 —` 等)。

### C. 認知編修六字訣(每頁自檢)
降雜訊 / 區塊化 / 增資訊 / 結構化 / 順脈絡 / 步驟化

---

## 執行流程

### 第 1 步:讀懂素材、規劃章節

讀取素材後,先輸出 **章節骨架**給使用者確認,每頁標註:
- 標題(≤10 字)
- 核心訊息(1-2 句)
- 所屬 SOIL 段(動機/注意/行動)
- 是否需要 AI 生圖
- 是否需要互動元件

**等使用者點頭再進下一步。**

### 第 2 步:統一視覺風格(產出 CSS 變數區塊)

```css
:root{
  --bg:#0a0e27; --bg-2:#11163a;
  --ink:#eef3ff; --ink-2:#b8c5e0; --ink-3:#7a8bb8; --ink-4:#4a5680;
  --accent:#00d4ff;   /* 主強調色,僅 1 種 */
  --accent-2:#ff006e; /* 輔強調色,僅 1 種 */
  --t1:55px; --t2:34px; --t3:21px; --t4:13px;
  --s1:80px; --s2:48px; --s3:24px; --s4:12px;
}
```

### 第 3 步:批次平行生圖(用 draw 技能)

**所有圖像呼叫一次性平行發出**,不要序列等待。預設參數:
- `--quality low`(99% 場景夠用)
- `--size 1536x1024`(滿版/對比圖)或 `1024x1024`(類型卡)
- 存到 `slides/generated/`

**Prompt 原則**:
- 風格詞統一(例:`Premium futuristic tech aesthetic, dark navy background, cyan and magenta neon accents`)
- 寫明 `No readable text`(避免亂碼文字)
- 留出文字疊放區域(`with negative space at bottom for text overlay`)
- 比例配合用途(滿版用 16:9,卡片用 1:1)

### 第 4 步:Base64 內嵌圖像(關鍵步驟)

⚠️ **不要用相對路徑**。預覽面板、檔案搬移、跨環境分享都會壞掉。
一律用 Pillow 壓縮 + base64 內嵌成 `data:image/jpeg;base64,...`:

```python
from PIL import Image
import base64, io
img = Image.open(path).convert('RGB')
w, h = img.size
target_w = 1280 if is_full_bleed else 900
if w > target_w:
    img = img.resize((target_w, int(h*target_w/w)), Image.LANCZOS)
buf = io.BytesIO()
img.save(buf, 'JPEG', quality=78, optimize=True)
b64 = base64.b64encode(buf.getvalue()).decode()
data_uri = f"data:image/jpeg;base64,{b64}"
```

5 張圖內嵌後 HTML 約 1.3-1.6 MB,完全可攜。

### 第 5 步:產出單一 HTML(架構模板)

**整體結構**:
```html
<body>
  <div id="progress"></div>          <!-- 頂部進度條 #23 -->
  <div id="section-tag"></div>       <!-- 左上 SOIL 章節標籤 -->
  <div id="pageInfo"></div>          <!-- 右下頁碼 -->
  <div id="hint"></div>              <!-- 左下快捷鍵提示 -->

  <section class="slide active" data-slide="1" data-section="引起動機">...</section>
  <section class="slide" data-slide="2" data-section="引起動機">...</section>
  ...

  <script>切頁 / 排序 / Chart.js 邏輯</script>
</body>
```

**slide 容器(滿版,不要做 1920×1080 縮放)**:
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

⚠️ **不要使用固定 1920×1080 + scale 縮放舞台的架構**。
理由:在小型預覽面板(如 Claude Code 的 Launch preview)會被縮成極小,字會擠成一團,觀感極差。
直接用 `position:absolute; inset:0` 滿版,讓內容跟著視窗大小撐滿就好。

**必備 UI 功能**:
1. **左右鍵 / 空白鍵切頁**(JS keydown)
2. **點擊畫面左右側切頁**(`x > 0.7*innerWidth → next`)
3. **F 鍵全螢幕**
4. **頁碼顯示**(右下角 `當前 / 總數`)
5. **頂部進度條**(切頁時動畫)
6. **章節標籤**(左上,讀 `data-section` 即時切換)
7. **每頁淡入動畫**

### 第 6 步:加入互動元件(這就是本技能的價值)

依章節骨架,在對應頁加入:

| 元件 | 適用頁型 | 實作 |
|------|----------|------|
| **三欄卡片** | 總覽頁、決策頁 | `display:grid; grid-template-columns:repeat(3,1fr)` + AI 圖嵌入卡內 |
| **左右並排圖文** | 類型詳解頁 | `display:grid; grid-template-columns:1fr 1fr` + Z 字翻轉 |
| **可排序表格** | 對比頁 | 點 `<th>` 觸發 sort,搭配 AI 對比視覺圖 |
| **Chart.js 雷達 / 折線圖** | 數據頁 | lazy render(切到該頁才初始化) |
| **SVG 決策樹** | 決策頁 | 中央問句 + SVG `<line>` 連到三張結果卡 |
| **滿版背景圖** | 封面、結尾 | 圖層 `position:absolute;inset:0` + 漸層遮罩 |
| **流程卡 2×3 grid** | 方法論頁 | 不要用 1×6,會太擠 |

### 第 7 步:版面溢出檢查(逐頁驗收)

每頁打開後檢查:
- [ ] 內容是否在標準 1920×1080 / 1366×768 視窗下完整顯示
- [ ] 沒有元素被視窗高度截掉
- [ ] 字級階層清楚(主標明顯大於內文)
- [ ] 圖文比例舒適(不擠不空)
- [ ] 章節標籤、頁碼、進度條都正常更新

如果某頁溢出,**優先做的事**:
1. 換成 2×N grid(避免 1×N 一字排開太擠)
2. 把長文字拆成兩頁
3. 縮短 padding(從 100px → 60px)
4. 圖片改成 `aspect-ratio:1/1` 縮成正方形

⚠️ **不要動全域字級變數來救溢出**,那會破壞整體階層。

### 第 8 步:驗收與輸出

1. 用 Bash 開啟產出的 HTML(`start slides.html`)
2. 切完每一頁,確認互動元件都正常
3. 報告檔案路徑與功能清單給使用者

---

## 輸出規範

```
專案資料夾/
├── slides.html              ← 單一 HTML(base64 內嵌圖,~1.5 MB)
├── slides/
│   └── generated/           ← AI 生成圖原始 PNG(備份用)
│       ├── slide-1-cover.png
│       └── ...
└── README.md                ← 使用說明 + 鍵盤快捷鍵
```

---

## 風格範本(預設「現代深色 + 霓虹點綴」)

| 項目 | 值 |
|------|----|
| 背景 | `#0a0e27`(深藍黑) |
| 主色 | `#00d4ff`(霓虹青) |
| 輔色 | `#ff006e`(亮粉) |
| 警示 | `#ffb800` / `#ff4466` |
| 標題字體 | `Noto Sans TC` 700/900 |
| 內文字體 | `Noto Sans TC` 400 |
| Mono 字體 | `JetBrains Mono`(用於 kicker、頁碼、tag) |
| 卡片 | 玻璃擬態(`backdrop-filter: blur(10px)`) |

---

## 與其他技能的串接

- **draw**(必要):平行批次生成所有頁面的 AI 圖
- **chart-maker**(選用):需要靜態 SVG 圖表時
- **lesson-prep / NotebookLM**(選用):素材來自課本 PDF 時
- **soil-teaching-deck**(姊妹):同時要產 .pptx 版本可平行呼叫

---

## 給其他 Agent 的呼叫提示

如本技能被其他 agent(如 GPT Codex)讀取使用,請遵守:
1. 每頁的 HTML 結構必須一致(`<section class="slide" data-slide="N" data-section="...">`)
2. 圖像一律 base64 內嵌,**不用相對路徑**
3. 所有 JS / CSS 內嵌或用 CDN(Chart.js / Google Fonts),不要產生需要 build 的 React/Vue 專案
4. 預設輸出單一 `.html`,使用者要的是「打開即用」,不是 dev server
5. 不要用固定 1920×1080 + transform scale 的架構,直接用 `position:absolute; inset:0` 滿版
6. 每頁要遵守林長揚 30 原則 + SOIL 三段式脈絡

---

## 踩坑紀錄(2026-05-02 直播 demo 累積)

| 坑 | 解法 |
|----|------|
| 預覽面板看不到圖(中文路徑或沙箱) | base64 內嵌,**不用** 相對路徑 |
| AI 圖只當背景太可惜 | 用 grid 把圖跟內容區塊**並排融合**,圖片要切圓角 + 加角標 |
| 1920×1080 scale 在小視窗變超小 | 改用滿版 `inset:0`,內容跟視窗撐滿 |
| 決策樹用 ASCII 字符不夠視覺 | 改成中央問句 + SVG 連線 + 三張顏色不同的結果卡 |
| 6 引擎排成 1×6 太擠 | 改 2×3 grid,搭配左側 AI 視覺圖 |
| 對比頁只有表格太枯燥 | 左側放「左舊右新」對比視覺圖,右側放可排序表 |
| 標題太長破版 | 嚴守 ≤10 字原則 |
| 強調色超過 2 種畫面亂 | 主 cyan + 輔 magenta + 警示色,其餘一律淡灰 |

---

## 安裝踩坑紀錄

### 2026-05-09 | YAML frontmatter 解析失敗

**症狀：** 安裝過程出現 `Skill.md must start with YAML front matter` 警示，雖然檔案開頭明明就是 `---`。

**根因：** frontmatter 中 `description` 欄位用了 folded block scalar（`description: >`）寫法。雖然語法上合法，Claude Code 的 skill loader 對此欄解析較嚴格，遇到折疊型多行字串會誤判為「沒有 frontmatter」。

**修正：** 把 `description: >` 改成 `description: |`（literal block scalar），保留換行、loader 可正常解析。

**教訓：** 寫 Skill 時 frontmatter 統一用 `|`（literal）而非 `>`（folded），降低相容性風險。

**前置依賴：** 本 skill 需要 `draw` skill（呼叫 OpenAI gpt-image-2）；ChatGPT/Codex 訂閱者免另設 API key 即可使用 gpt-image-2（OpenAI 2026-04-21 公告）。HTML 簡報的圖像必須 base64 內嵌。
