# Teaching Deck 模式（可編輯文字 .pptx）

> 使用情境：底圖是 AI 生成、文字是 PowerPoint 文字物件（雙擊可改）、可加幾何圖形（國高中數學）
>
> 適用：教學現場、教師研習、需要交付給其他教師後續微調、多版本維護
> 不適用：純社群素材、視覺衝擊型開場 → 改用 image 模式

本檔案接續主 SKILL.md 的引擎 1–5，提供 teaching 模式專屬的引擎三補充規格 + 引擎六執行流程，
並包含**診斷修改模式**的完整工作流。

---

## 引擎三補充：visuals 與 geometry 標記

### ▶ AI 視覺素材標記規則（visuals 欄位）

當頁面需要**非幾何**的視覺素材時，使用 `visuals` 欄位（可多個）。引擎六將自動呼叫 `draw` skill（gpt-image-2）生成並嵌入投影片。

**視覺不等於「小插圖」**——本模式支援六種 `role`，每種有不同的視覺重量與排版功能：

| role | 用途 | 視覺重量 | 尺寸建議 | 典型位置 |
|------|------|---------|---------|---------|
| `illustration` | 傳統小插畫，搭配文字 | 中 | `1024x1024` | 右欄 `x=5.1 w=4.5` |
| `background` | **全版底圖**，文字疊加其上 | 最高 | `1536x1024` | 全版 `0,0,13.333,7.5` |
| `hero` | 半版主視覺，左右或上下分割 | 高 | `1536x1024` | 右半版 `x=6.7 w=6.7` |
| `side_panel` | **細長側條**（裝飾、氛圍） | 中 | `1024x1536`（直）| 左側 `x=0 w=3` |
| `section_divider` | 章節過場、全版視覺分隔 | 高 | `1536x1024` | 全版 |
| `accent` | **小型裝飾圖示**（角落、重點旁）| 低 | `1024x1024` | 自訂小區塊 |

**何時用哪一種：**
- **封面頁** → `hero`（半版主視覺）或 `background`（全版，文字疊上）
- **問題引入頁** → `background`（全版情境氛圍）或 `hero`（角色分明）
- **案例頁** → `illustration`（小場景）或 `hero`（情境較重要時）
- **迷思澄清頁** → 兩個 `accent`（左錯右正）
- **比較頁** → 兩個 `illustration`（雙欄）
- **章節過場／段落分隔** → `section_divider`
- **資訊密集頁邊裝飾** → `side_panel`（細長直版，讓不會空）
- **行動／結語頁** → `background` + 大字疊加

**visuals 欄位格式：**

```yaml
第 N 頁：[頁面標題]
- 頁面角色：問題引入頁
- visuals:
    - id: slide_N_bg
      role: background
      prompt: "一個國中生在黑板前看著數學題目困惑思考的扁平插畫，左側 40% 為純深藍色塊留白（供文字疊加）"
      size: 1536x1024
      quality: low
      opacity: 1.0
    - id: slide_N_accent
      role: accent
      prompt: "一個紅色大問號圖示，扁平向量"
      size: 1024x1024
      quality: low
      x: 8.5
      y: 4.5
      w: 2.0
      h: 2.0
```

> 一頁可以同時有 `geometry` 與 `visuals`、或多個 `visuals`（例如 background + accent）。
> 風格一致性由引擎五的 `image_policy` 統一控管。

### 典型頁面 × 視覺組合（Layout Recipes）

| 頁面角色 | 建議組合 |
|---------|---------|
| 封面頁 | `background` 或 `hero` + 大標題疊加 |
| 問題引入 | `background` + 大問句文字 |
| 迷思澄清 | 兩個 `accent`（左❌右✅）+ 說明文字 |
| 雙欄比較 | 兩個 `illustration` + 雙欄文字 |
| 流程頁 | `side_panel` + 中央流程圖 |
| 數據頁 | `hero` + 大字數據 |
| 案例頁 | `illustration` + 內文 |
| 總結頁 | `background`（半透明）+ 條列 |
| 行動頁 | `background` + 大字口號 |
| 章節過場 | `section_divider` + 章節標題 |

### ▶ 幾何圖形標記規則（數學教學內容專用）

當頁面內容涉及幾何圖形（三角形、四邊形、圓、立體圖等），加入 `geometry` 欄位：

```yaml
第 N 頁：[頁面標題]
- 頁面角色：案例頁
- geometry:
    mode: single          # single（單圖）/ side_by_side（並排最多 3 圖）
    figures:
      - id: slide_N_fig1
        type: triangle
        config:
          subtype: right
          vertex_labels: ["A", "B", "C"]
          right_angle_at: "C"
          side_labels: {AB: "5", BC: "3", CA: "4"}
        canvas: {width: 360, height: 280}
        caption: "直角三角形 ABC"
        insert_at: right    # right（右欄）/ center（置中）/ left（左欄）
        width_cm: 10.0
```

> 完整圖形類型與 config 參數見本檔末「幾何圖形參數速查」。

---

## 引擎六：teaching 版總導演

### 兩種技術路徑

| 路徑 | 工具 | 適用 |
|------|------|------|
| **A. python-pptx + spec.yaml**（簡單） | 內建 `scripts/pack_pptx.py`（plate 模式） | 純 plate 用法，使用者只需要 AI 底圖 + 文字塊 |
| **B. PptxGenJS + base64**（進階） | Node.js + pptxgenjs npm | 需要複雜佈局、幾何圖、多種視覺角色混用 |

**選 A**：使用者只想要簡單的 plate（AI 底圖 + 標題副標 body）→ 用 image-deck.md 的 plate 子模式

**選 B**：使用者要混用多種 role（background + accent + illustration + geometry）→ 走下面的完整流程

### B 路徑：PptxGenJS 完整流程

> ⚠️ **若頁面角色表中有任何 `geometry` 欄位，必須先完整跑完「幾何圖形整合子流程（G-1 至 G-4）」。**
>
> ⚠️ **若頁面角色表中有任何 `visuals` 欄位，必須先完整跑完「AI 視覺素材整合子流程（I-1 至 I-3）」。**
>
> 兩個子流程彼此獨立，可並行執行。最終 PptxGenJS 腳本同時載入 `geo_b64.json` 與 `illus_b64.json`。

---

### ▶ 幾何圖形整合子流程（G-1 ~ G-5）

#### G-1：安裝依賴

```bash
pip install cairosvg Pillow --break-system-packages -q

GEOM_RENDERER="/mnt/skills/user/jh-math-geometry/scripts/geometry_renderer.py"
echo "幾何渲染器：$GEOM_RENDERER"
```

#### G-2：批次生成標準幾何圖形

```bash
mkdir -p /home/claude/geo_out

cat > /home/claude/geo_spec.json << 'SPEC'
{
  "figures": [
    {
      "id": "slide_N_figX",
      "type": "triangle",
      "config": {
        "subtype": "general",
        "vertex_labels": ["A", "B", "C"],
        "angle_arcs": {"A": 1, "B": 1, "C": 1}
      },
      "canvas": {"width": 360, "height": 280}
    }
  ],
  "options": {"format": "png", "dpi": 150}
}
SPEC

python3 "$GEOM_RENDERER" /home/claude/geo_spec.json /home/claude/geo_out/
ls /home/claude/geo_out/*.png
```

> **視覺確認**：用 `view` 工具逐一查看生成的 `.png`，確認標籤、角弧、等邊記號正確。如有問題，調整 spec 重新生成，**不要繼續到下一步**。

#### G-3：生成自訂幾何圖形（renderer 不支援的）

需要「兩直線相交」、「帶延長線的外角圖」、「多角標色」等時，用 Python 直接呼叫 `SVGCanvas` 手繪：

```python
# /home/claude/geo_custom.py
import math, sys
sys.path.insert(0, '/mnt/skills/user/jh-math-geometry/scripts')
from geometry_renderer import SVGCanvas
import cairosvg
from pathlib import Path

OUT = Path("/home/claude/geo_out")

def save(c, name):
    svg = c.render()
    (OUT / f"{name}.svg").write_text(svg)
    cairosvg.svg2png(bytestring=svg.encode(),
                     write_to=str(OUT / f"{name}.png"), dpi=150)

# 範例：兩直線相交（對頂角）
def make_vertical_angles():
    c = SVGCanvas(360, 280, 'white')
    cx, cy = 180, 140
    angle1, angle2 = math.radians(35), math.radians(110)
    r = 130
    c.line(cx + r*math.cos(angle1), cy - r*math.sin(angle1),
           cx - r*math.cos(angle1), cy + r*math.sin(angle1))
    c.line(cx + r*math.cos(angle2), cy - r*math.sin(angle2),
           cx - r*math.cos(angle2), cy + r*math.sin(angle2))
    c.dot(cx, cy, r=3.5)
    c.text(cx+8, cy+14, 'O', size=12, bold=True)
    save(c, 'vertical_angles')

make_vertical_angles()
```

#### G-4：轉換為 base64

```python
# /home/claude/geo_to_b64.py
import base64, json
from pathlib import Path

geo_dir = Path("/home/claude/geo_out")
figure_ids = ["slide_N_figX", "vertical_angles"]

result = {}
for fid in figure_ids:
    png = geo_dir / f"{fid}.png"
    if png.exists():
        result[fid] = "image/png;base64," + base64.b64encode(png.read_bytes()).decode()

with open('/home/claude/geo_b64.json', 'w') as f:
    json.dump(result, f)
```

#### G-5：在 PptxGenJS 用 addImage 嵌入

```javascript
const fs = require("fs");
const geo = JSON.parse(fs.readFileSync('/home/claude/geo_b64.json', 'utf8'));

slide.addImage({
  data: geo["slide_N_figX"],
  x: 0.4, y: 1.5, w: 4.2, h: 3.2,
  sizing: { type: "contain", w: 4.2, h: 3.2 }
});
```

**位置對照（LAYOUT_WIDE 16:9，13.333" × 7.5"）：**

| 圖形位置 | x | w |
|---------|---|---|
| 左欄（雙欄佈局） | 0.3 | 4.2 |
| 右欄（雙欄佈局） | 5.1 | 4.5 |
| 置中（全版圖） | 1.5 | 7.0 |
| 右側小圖（文字為主） | 6.5 | 3.0 |

---

### ▶ AI 視覺素材整合子流程（I-1 ~ I-4）

#### I-1：批次生成 AI 視覺素材

針對引擎三標記的每個 `visuals` 條目，**合併 `image_policy.style_tokens` 與該 visual 的 `prompt`**：

```
最終 prompt = "{page_prompt}，{style_tokens}，{negative}"
```

依 role 對應表決定 size/quality：

| role | draw.py 參數 | pptx 嵌入位置 |
|------|------------|--------------|
| `illustration` | size=`1024x1024`, quality=`low` | x=5.1, y=1.5, w=4.5, h=4.0 |
| `background` | size=`1536x1024`, quality=`low/medium` | 全版 `(0,0,13.333,7.5)` |
| `hero` | size=`1536x1024`, quality=`low` | x=6.7, y=0, w=6.7, h=7.5 |
| `side_panel` | size=`1024x1536`（直）, quality=`low` | x=0, y=0, w=3.0, h=7.5 |
| `section_divider` | size=`1536x1024`, quality=`medium` | 全版 |
| `accent` | size=`1024x1024`, quality=`low` | 依 block 自訂 x/y/w/h |

> **background / section_divider 的提示詞要求**：必須強制 negative「不要任何文字」並指定留白區（例如「左側 40% 為純深色色塊供文字疊加」），否則文字疊在插畫主體上會難讀。

範例批次指令：

```bash
mkdir -p slides/images

STYLE="扁平向量插畫、深夜藍#0D1B2A 背景、亮青藍#00C6FF 線條、金黃#FFD700 點綴、教室或數位科技情境"
NEG="不要逼真照片、不要雜亂背景"
DRAW="python C:/Users/mathr/.claude/skills/draw/draw.py"

$DRAW "國中生在黑板前看著數學題目困惑思考，${STYLE}，${NEG}" \
  --size 1024x1024 --quality low --name slide_3_illus1 --outdir slides/images/

$DRAW "一張發光的火箭向上飛，象徵學習突破，${STYLE}，${NEG}" \
  --size 1536x1024 --quality low --name slide_10_illus1 --outdir slides/images/

ls slides/images/*.png
```

> **成本**：low 一張 NT$0.3；10 頁中 4 頁有插畫約 NT$1.2
> **並行加速**：張數多（>5）時 `$DRAW ... &` 背景啟動 + `wait`

#### I-2：視覺確認（必做）

用 `view` 工具或直接開檔逐一檢視 PNG。檢查：

- 風格是否與 `image_policy.style_tokens` 一致？
- 是否符合頁面教學用途？
- 是否有不該出現的文字／亂碼？
- 配色是否與簡報主色協調？

若不合格，調整 prompt 或升級 quality 為 `medium`，重跑 I-1 該張。**不帶不合格的圖進入 I-3。**

#### I-3：轉 base64

```python
# illus_to_b64.py
import base64, json, glob
from pathlib import Path

img_dir = Path("slides/images")
illus_ids = ["slide_3_illus1", "slide_10_illus1"]  # 依引擎三標記補齊

result = {}
for iid in illus_ids:
    candidates = sorted(glob.glob(str(img_dir / f"{iid}_*.png")))
    if not candidates:
        print(f"⚠️  找不到 {iid}")
        continue
    latest = Path(candidates[-1])
    result[iid] = "image/png;base64," + base64.b64encode(latest.read_bytes()).decode()

with open('illus_b64.json', 'w', encoding='utf-8') as f:
    json.dump(result, f)
```

#### I-4：在 PptxGenJS 嵌入

```javascript
const pptxgen = require("pptxgenjs");
const fs = require("fs");

const geo = fs.existsSync('geo_b64.json')
  ? JSON.parse(fs.readFileSync('geo_b64.json', 'utf8')) : {};
const illus = fs.existsSync('illus_b64.json')
  ? JSON.parse(fs.readFileSync('illus_b64.json', 'utf8')) : {};

// illustration（小插畫）
slide.addImage({
  data: illus["slide_3_illus1"],
  x: 5.1, y: 1.5, w: 4.5, h: 3.0,
  sizing: { type: "contain", w: 4.5, h: 3.0 }
});

// background（全版底圖 + 暗化遮罩）
slide.addImage({
  data: illus["slide_1_bg"],
  x: 0, y: 0, w: 13.333, h: 7.5,
  sizing: { type: "cover", w: 13.333, h: 7.5 }
});
slide.addShape(pptx.shapes.RECTANGLE, {
  x: 0, y: 0, w: 6.5, h: 7.5,
  fill: { type: "solid", color: "0D1B2A", transparency: 30 },
  line: { color: "0D1B2A", transparency: 100 }
});

// hero（半版主視覺）
slide.addImage({
  data: illus["slide_1_hero"],
  x: 6.7, y: 0, w: 6.63, h: 7.5,
  sizing: { type: "cover", w: 6.63, h: 7.5 }
});

// side_panel（側邊細條）
slide.addImage({
  data: illus["slide_3_panel"],
  x: 0, y: 0, w: 3.0, h: 7.5,
  sizing: { type: "cover", w: 3.0, h: 7.5 }
});

// accent（小裝飾）
slide.addImage({
  data: illus["slide_2_q"],
  x: 8.5, y: 4.5, w: 2.0, h: 2.0,
  sizing: { type: "contain", w: 2.0, h: 2.0 }
});
```

---

### 第一輪：用 PptxGenJS 生骨架

```bash
# 讀取 PptxGenJS 完整 API（如有 pptx skill）
# cat /mnt/skills/pptx/pptxgenjs.md
```

**字級標準（林長揚 #1 對應）**

| 元素 | 字級 | 用法 |
|------|------|------|
| **封面大標題** | 72–84pt bold | 封面頁、關鍵行動頁 |
| **一般標題** | 44–56pt bold | 每頁主訊息 |
| **副標** | 28–34pt bold | 主標下方補充 |
| **內文（body）** | 18–21pt | 條列、說明 |
| **註解（muted）** | 14–16pt | 底部署名、備註 |
| **徽章（badge）** | 18–22pt bold | 頁面角色標籤 |
| **強調（highlight）** | 24–28pt bold | 金黃／強調色句子 |

**字型選擇（林長揚 #7）**

| 用途 | 建議字型 |
|------|---------|
| 標題／副標／徽章／強調 | `GenSekiGothic2 TW H`（源石黑體 Heavy）|
| 內文／註解 | `Microsoft JhengHei`（微軟正黑體）|

**其他規範**
- 使用 `LAYOUT_WIDE`（16:9，13.333" × 7.5"）
- 行距 `line_spacing=1.2`（林長揚 #5）
- 0.5" 最小邊距
- 深色封面 + 結語，淺色內容頁（三明治結構）
- 每頁都要有視覺元素（`visuals` 或 `geometry`）
- 固定 x 格點（林長揚 #14）：左 `0.6/0.7`、雙欄 `5.1/7.2`、三欄 `0.6/4.85/9.1`

**根據頁面角色選擇佈局：**

| 頁面角色 | 建議佈局 |
|---------|---------|
| 封面頁 | 深色全版背景 + 大標題居中 |
| 問題引入頁 | 大字問句 + 留白 |
| 迷思澄清頁 | 雙欄（❌ 誤解 vs ✅ 正確） |
| 比較頁 | 雙欄或上下對照 |
| 流程頁 | 橫向箭頭步驟 或 時間軸 |
| 分類頁 | 2×2 或 2×3 網格 |
| 案例頁 | 圖片/情境 + 說明 |
| 數據頁 | 大數字 60–72pt + 小標籤 |
| 總結頁 | 條列收攏 + 帶走一句話 |
| 行動頁 | 深色背景 + 行動指引 |
| 過渡頁 | 全版色塊 + 一句話 |

### 第二輪：修頁面（視覺 QA）

```bash
# 文字內容檢查
python -m markitdown output.pptx

# 轉成圖片逐頁檢查
soffice --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
ls -1 slide-*.jpg
```

逐張檢查：
- 元素是否重疊
- 文字是否溢出
- 間距是否一致
- 對比是否足夠
- 頁面角色是否清楚
- **幾何圖形是否正確對齊、比例合適**
- **AI 插畫是否風格一致、不與文字重疊**

修正後重新生成。

### 第三輪：最終檢查

- [ ] 每頁只有一個主重點
- [ ] 三段式脈絡完整（動機→注意→行動）
- [ ] 頁面角色多元
- [ ] 關鍵投影片有被突顯
- [ ] 帶走一句話有出現在總結頁
- [ ] 常見誤解有被處理
- [ ] 風格一致（配色、字型、標題位置）
- [ ] 無純文字頁
- [ ] 有 geometry 標記頁，幾何圖預覽過正確才嵌入
- [ ] 幾何圖在投影片內對齊正確、比例合適、不與文字重疊
- [ ] 有 visuals 標記頁，AI 插畫均通過 I-2 視覺確認
- [ ] 所有 AI 插畫風格一致，符合 image_policy
- [ ] 封面、問題引入、案例、行動頁有主視覺，不是純文字

---

## 診斷修改模式（使用者帶現有 .pptx 進來）

當使用者上傳現有簡報詢問「哪裡可以改」、「認知負荷太高」時：

### Step 1：讀取現有簡報

```bash
python -m markitdown input.pptx
```

同時轉成圖片檢視視覺佈局。

### Step 2：用引擎四做認知編修診斷

逐頁用六個認知詞（降雜訊、區塊化、增資訊、結構化、順脈絡、步驟化）檢查。

### Step 3：補做引擎三的頁面角色分析

檢查每頁是否有明確角色，是否頁型過於單調。

### Step 4：輸出認知編修報告

```
## 認知編修報告

### 第 N 頁：[頁面標題]
- 降雜訊：[具體建議，不要只說「字太多」]
- 區塊化：[具體建議]
- 增資訊：[具體建議]
- 結構化：[具體建議]
- 順脈絡：[具體建議]
- 步驟化：[具體建議]
- 修改優先級：高 / 中 / 低
```

### Step 5：確認後執行修改

使用者確認要改哪些之後，才進行實際修改。修改後再 QA 驗證。

---

## 幾何圖形參數速查（內嵌）

> 撰寫引擎三的 `geometry` 標記時直接查閱，無需讀取外部檔案。

### 通用結構

```json
{
  "id": "fig1",
  "type": "<圖形類型>",
  "config": { ... },
  "canvas": { "width": 360, "height": 280 }
}
```

> 簡報用圖建議 canvas：`360×280`；並排比較圖各用 `240×200`

### 1. triangle（三角形）

| 參數 | 說明 | 可選值 |
|------|------|--------|
| `subtype` | 種類 | `general`（預設）、`right`、`isosceles`、`equilateral` |
| `vertex_labels` | 頂點標籤 | 字串陣列，預設 `["A","B","C"]` |
| `right_angle_at` | 直角符號頂點 | 頂點標籤字串 |
| `angle_arcs` | 各頂點角弧數 | `{"A":1, "B":2}` |
| `side_labels` | 各邊文字標籤 | `{"AB":"5", "BC":"3"}` |
| `equal_marks` | 等邊刻度數 | `{"AB":1, "CD":2}` |
| `altitude_from` | 畫高的頂點 | 頂點標籤字串 |
| `median_from` | 畫中線的頂點 | 頂點標籤字串 |
| `dashed_sides` | 畫成虛線的邊 | `["AB"]` |
| `show_dots` | 頂點黑點 | `true`（預設）|

### 2. quadrilateral（四邊形）

| 參數 | 說明 |
|------|------|
| `subtype` | `parallelogram` / `rectangle` / `rhombus` / `square` / `trapezoid` / `right_trapezoid` / `general` |
| `vertex_labels` | 預設 `["A","B","C","D"]` |
| `side_labels`、`equal_marks`、`right_angles` | |
| `diagonals` | 是否畫對角線 |
| `diagonal_labels` | `{"AC":"m","BD":"n"}` |

### 3. circle（圓）

| 參數 | 說明 |
|------|------|
| `center_label` | 圓心標籤，預設 `"O"` |
| `points` | 圓周上各點：`{"A": 60, "B": 160}`（角度，0=右，90=上，逆時針）|
| `radius_lines` | 畫半徑線的點陣列 |
| `chords` | 弦：`[["A","B"],["C","D"]]` |
| `diameter` | 直徑端點 `["A","C"]` |
| `tangent_at` | 切線點 |
| `central_angle` | 填色扇形（圓心角） |
| `inscribed_angle` | 圓周角：`{"vertex":"C","arc":["A","B"]}` |

### 4. coordinate_plane（坐標平面）

| 參數 | 說明 |
|------|------|
| `x_range` / `y_range` | 軸範圍 |
| `show_grid` | 顯示格線 |
| `tick_interval` | 刻度間隔 |
| `points` | `[{"x":1,"y":2,"label":"A","color":"#cc0000"}]` |
| `lines` | `[{"slope":2,"intercept":-1,"label":"y=2x-1"}]` |
| `parabolas` | `[{"a":1,"b":0,"c":-2,"label":"y=x²-2"}]` |
| `segments` | `[{"x1":0,"y1":0,"x2":3,"y2":4}]` |

### 5. solid_3d（立體圖形）

| subtype | 頂點順序 |
|---------|---------|
| `rectangular_prism` | ABCD（上）EFGH（下）|
| `cylinder` | labels: radius, height |
| `cone` | labels: apex, base, radius, slant, height |
| `triangular_prism` | ABC（後）DEF（前）|
| `square_pyramid` | ABCD（底）P（頂）|
| `triangular_pyramid` | ABCD |

共用：`show_hidden`（虛線稜）、`vertex_labels`、`labels`

### 6. parallel_lines（平行線截角）

| 參數 | 說明 |
|------|------|
| `n_parallel` | 通常 2 |
| `line_labels` | `["l","m"]` |
| `transversal_angle` | 截線角度（度）|
| `angle_marks` | `[{"line":0,"position":"upper_left","label":"A"}]` |

### 7. triangle_center（三角形的心）

| `center_type` | 預設標籤 |
|--------------|---------|
| `centroid` | G |
| `circumcenter` | O |
| `incenter` | I |

### 8. similar_triangles（相似三角形）

兩三角形各自 config，相同角弧表示相等角。

### 快速複製區（最常用）

| 情境 | spec |
|-----|------|
| 畢氏定理 | `{"type":"triangle","config":{"subtype":"right","vertex_labels":["A","B","C"],"right_angle_at":"C","side_labels":{"AB":"c","BC":"a","CA":"b"}}}` |
| 圓心角＋圓周角 | `{"type":"circle","config":{"center_label":"O","points":{"A":30,"B":150,"C":270},"radius_lines":["A","B"],"central_angle":["A","B"],"inscribed_angle":{"vertex":"C","arc":["A","B"]}}}` |
| 平行四邊形對角線 | `{"type":"quadrilateral","config":{"subtype":"parallelogram","vertex_labels":["A","B","C","D"],"diagonals":true}}` |
| 四角柱 | `{"type":"solid_3d","config":{"subtype":"rectangular_prism","vertex_labels":["A","B","C","D","E","F","G","H"],"show_hidden":true}}` |
| 重心 | `{"type":"triangle_center","config":{"center_type":"centroid","center_label":"G","triangle":{"subtype":"general","vertex_labels":["A","B","C"]}}}` |
| 一次函數 | `{"type":"coordinate_plane","config":{"x_range":[-3,5],"y_range":[-4,8],"lines":[{"slope":2,"intercept":-1,"label":"y=2x-1"}]}}` |
| 拋物線 | `{"type":"coordinate_plane","config":{"x_range":[-2,5],"y_range":[-5,6],"parabolas":[{"a":1,"b":-2,"c":-3,"label":"y=x²-2x-3"}]}}` |
