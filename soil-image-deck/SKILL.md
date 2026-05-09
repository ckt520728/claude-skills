---
name: soil-image-deck
description: |
  SOIL 純圖片教學簡報技能。遵循 SOIL Teaching Deck Workflow 六顆引擎的教學設計邏輯，
  但每一頁都是由 gpt-image-2 完整生成的 PNG 圖片（包含標題、內文、視覺），
  最後打包成 .pptx（每張 slide 是一張全版圖）。
  當使用者說「做純圖片簡報」、「全圖簡報」、「每頁都是 AI 生的圖」、
  「用 gpt-image-2 做整份簡報」、「做一份像海報一樣的教學簡報」、
  「快速做一份視覺震撼的簡報」或任何要求「整頁都是 AI 圖像」的教學簡報需求時，
  請一定要使用此技能。
  本技能與 soil-teaching-deck 不同：soil-teaching-deck 產出「文字可編輯 + AI 插圖」的
  混合簡報；本技能產出「每頁都是單張 AI 圖」的純圖片簡報，適合
  快速產出、社群貼文、視覺強烈的開場、或不需後續文字編輯的場合。
---

# SOIL 純圖片教學簡報（soil-image-deck）

以 SOIL 六顆引擎的教學判斷為骨架，用 gpt-image-2 逐頁生成**整頁圖像**，最後打包成 .pptx。

> **與 soil-teaching-deck 的差別**
> - `soil-teaching-deck`：引擎 6 寫 PptxGenJS/python-pptx，產出「文字 + 插圖」的 editable pptx
> - `soil-image-deck`（本技能）：引擎 6 逐頁生出「整頁圖」，打包成 pptx（每 slide 就是一張 full-bleed 圖）

---

## 適用情境

| 情境 | 為什麼用本技能 |
|------|----------------|
| 直播開場、研習暖場 | 要視覺衝擊，不需要台下帶回去編輯 |
| 社群分享、FB / IG 貼文 | 每張圖就是一則獨立素材 |
| 快速原型、腦力激盪 | 4 分鐘出 10 張，不糾結排版 |
| YouTube 影片章節過場 | 風格統一、節奏清楚 |
| 節慶／宣傳海報簡報 | 圖像為主、文字為輔 |

**不適合**：需要台下老師後續修改文字、有大量精細資料、需要動畫互動——這些用 `soil-teaching-deck` 或 `pptx`。

---

## 第一步：判斷工作模式

**問使用者（只問這一題）：**

> 請問你目前的狀況是？
> 1. 我有素材（文字、教材、腳本），想做成純圖片簡報
> 2. 我只有一個主題或一句話，想從頭開始
> 3. 我有現成的 YAML 規格，直接跑生圖與打包

| 回答 | 跑哪幾顆引擎 |
|-----|--------------|
| 1 | 引擎 1→2→3→4→5→6 |
| 2 | 先協助擴充內容 → 引擎 1→2→3→4→5→6 |
| 3 | 跳過引擎 1–5，直接進入引擎 6（I-1 批次生圖 → I-2 QA → I-3 打包）|

---

## 第二步：進入引擎前補問

### 進引擎一前補問：

> 1. **教學對象是誰？**（國中生、高中生、老師研習、一般觀眾、社群受眾）
> 2. **簡報總頁數？**（預設 10 頁；社群貼文通常 6–9 頁；研習暖場 10–12 頁）
> 3. **有預算上限嗎？**（low 品質每張 NT$0.3，10 頁約 NT$3；若要高品質請說）

### 進引擎五前補問：

> 1. **有偏好的視覺風格嗎？**（例如：扁平插畫、手繪粉筆風、新聞風、科技感、水彩）
> 2. **有參考圖片或既有簡報可以給我嗎？**
> 3. **主要色系？**（例如：深藍 + 金黃、米色 + 墨綠、粉色系）

---

## 引擎一：概念定位師

同 soil-teaching-deck 引擎一。產出：總概念、三個子概念、三個常見誤解、帶走一句話、最小事實包。

> 本技能特別注意：因為每頁都是圖，**文字量要極度壓縮**。最小事實包列出的事實，最後只會保留最核心的 1–2 條/頁。

---

## 引擎二：脈絡定位師

同 soil-teaching-deck 引擎二。三段節奏（引起動機／維持注意／喚起行動），比例 2:6:2 左右（10 頁時）。

---

## 引擎三：頁面架構師（**本技能核心差異**）

每頁指定角色後，本技能額外產出「**image brief**」，作為引擎六生圖的基礎。

### 每頁要指定

- 頁碼
- 頁面角色（同 soil-teaching-deck 的頁型清單：封面／問題引入／迷思澄清／比較／流程／分類／案例／數據／總結／行動／過渡）
- 本頁主重點（一句話）
- **on-image text**：圖上要出現的文字（**極少！**通常是一個標題 + 0–2 個關鍵詞）
- **image brief**：這張圖的核心構圖（主角、場景、動作、象徵物）
- **layout hint**：版面佈局（置中大標、左文右圖、上圖下標、全版背景 + 浮字、分格對比…）

### 輸出格式

```yaml
pages:
  - page: 1
    role: 封面
    core_point: "把 ChatGPT 生圖偷進 Claude Code"
    on_image_text:
      title: "把 ChatGPT 生圖偷進 Claude Code"
      subtitle: "gpt-image-2 × 教學工作流"
      tag: "EP15"
    image_brief: "Q版機器人老師站在發光黑板前手持畫筆，黑板上有數學公式與電路圖案"
    layout_hint: "左文右圖；標題置左上 1/3，圖像置右 2/3"

  - page: 2
    role: 問題引入
    core_point: "ChatGPT 發布 Image 2，能搬進 Claude Code 嗎？"
    on_image_text:
      title: "能偷進來嗎？"
    image_brief: "一個卡通老師站在兩條岔路前，左路 ChatGPT 訂閱方塊，右路 Claude Code 齒輪"
    layout_hint: "全版插畫 + 大問句浮於上方"
```

### 文字最小化原則

> [!important]
> 由於 gpt-image-2 文字渲染雖正確但仍有上限，**每張圖建議中文字 ≤ 20 字、片段 ≤ 3 段**。超過要拆成多頁或改用 soil-teaching-deck。

---

## 引擎四：認知編修師

六個認知詞仍然適用，但修正建議要對應「圖像語言」而非「文字排版」。

| 認知詞 | 在純圖片簡報裡怎麼問 |
|-------|---------------------|
| 降雜訊 | image_brief 有沒有多餘的裝飾物、次要角色？可刪除 |
| 區塊化 | layout_hint 有沒有明確的視覺分群（上下/左右/中心）？ |
| 增資訊 | 需要補符號（→、vs、✓、✗）、數字、色差嗎？ |
| 結構化 | 一看就知道主角和配角嗎？對比度夠嗎？ |
| 順脈絡 | layout_hint 有安排視線起點與終點嗎？ |
| 步驟化 | 流程頁是否有編號、箭頭指引？ |

逐頁用六詞檢視 image_brief 與 on_image_text，必要時回去修引擎三的規格。

---

## 引擎五：風格建構師（產出 image_policy）

**必填輸出**（本技能不可略過）：

```yaml
image_policy:
  # 風格描述（會串接進每張生圖 prompt）
  style_tokens: "扁平向量插畫、16:9橫版、深夜藍#0D1B2A背景、亮青藍#00C6FF主色、金黃#FFD700點綴、現代教育科技風"

  # 負面提示
  negative: "不要逼真照片、不要雜亂背景、不要英文字、不要亂碼"

  # 固定設定
  size: "1536x1024"            # 16:9 橫版
  quality: "low"               # 預設 low；封面或關鍵頁可升 medium
  font_feel: "粗體無襯線、標題大字"  # 中文字風格提示

  # 配色提示（影響 gpt-image-2 的色彩選擇）
  palette:
    primary: "#0D1B2A"
    accent: "#00C6FF"
    highlight: "#FFD700"
    text: "#FFFFFF"

  # 關鍵頁升級規則
  upgrade_rules:
    - page: 1                  # 封面升 medium
      quality: "medium"
    - role: "行動"              # 行動頁升 medium
      quality: "medium"
```

### 風格預設庫（無偏好時自動選）

| 教學場景 | 風格預設 |
|---------|---------|
| 國中/國小 | 彩色扁平插畫、粉色＋綠色對比、可愛角色 |
| 高中 | 清晰扁平、深藍＋橘色、知性感 |
| 老師研習 | 溫暖粉筆風、米色＋墨綠、黑板質感 |
| 直播暖場 | 科技感、深藍＋亮青藍＋金黃（同 EP15） |
| 社群貼文 | 高彩對比、粉紅＋紫藍、吸睛優先 |

---

## 引擎六：簡報總導演（純圖片版）

### 生成流程（三階段：I-1 → I-2 → I-3）

#### I-1：批次生圖

對每一頁，合併 `image_policy.style_tokens` + `on_image_text` + `image_brief` + `layout_hint` 組成最終 prompt：

```
{layout_hint}。
圖像內容：{image_brief}。
圖上文字：標題「{on_image_text.title}」、{其他文字描述}。
風格：{style_tokens}。
避免：{negative}。
```

批次呼叫 `draw.py`（路徑 `C:/Users/mathr/.claude/skills/draw/draw.py`）：

```bash
mkdir -p slides/images
DRAW="python C:/Users/mathr/.claude/skills/draw/draw.py"
SIZE="1536x1024"

# 頁 1（封面升 medium）
$DRAW "左文右圖。圖像內容：Q版機器人老師...。圖上文字：標題「把 ChatGPT 生圖偷進 Claude Code」、副標「gpt-image-2 × 教學工作流」、標籤「EP15」。風格：扁平向量插畫、16:9橫版、深夜藍#0D1B2A背景、亮青藍#00C6FF主色...。避免：不要逼真照片、不要亂碼。" \
  --size $SIZE --quality medium --name page_01 --outdir slides/images/

# 頁 2 起（low）
$DRAW "全版插畫 + 大問句。圖像內容：一個卡通老師站在兩條岔路前...。圖上文字：標題「能偷進來嗎？」。風格：...。" \
  --size $SIZE --quality low --name page_02 --outdir slides/images/

# ... 其餘頁
```

**並行加速**：頁數多時，每 3–4 張用 `&` 背景跑 + `wait`，可省一半時間。

**成本估算**：
- 預設 10 頁：9 張 low + 1 張 medium ≈ NT$(0.3×9 + 1.3) = **NT$4.0**
- 15 頁：14 張 low + 1 張 medium ≈ **NT$5.5**

#### I-2：視覺確認（必做）

批次生完後，**逐張用 view 工具檢查**：

- 圖上文字是否正確、無亂碼？
- 風格是否與 `image_policy` 一致？
- 佈局是否符合 `layout_hint`？
- 關鍵頁（封面、結語）品質是否夠？

**不合格處理**：
- 文字錯字 → 改 prompt 中文字部分，重跑該頁
- 風格偏移 → 檢查 style_tokens 是否被截斷
- 品質不足 → 升級 quality 為 medium

**重點**：不要讓任何一張不合格的圖進入 I-3。

#### I-3：打包成 PPTX

使用內建腳本 `pack_pptx.py`：

```bash
python C:/Users/mathr/.claude-skills/soil-image-deck/pack_pptx.py \
  --images-dir slides/images \
  --output slides/我的簡報.pptx \
  --title "簡報標題"
```

**腳本行為**：
- 讀取 `slides/images/page_NN_*.png`（依檔名前綴排序）
- 每張圖以 full-bleed（滿版）方式填入一張 16:9 slide
- 不加任何文字（文字已在圖上）
- 輸出單一 .pptx 檔

---

## 自動化模式（使用者給主題就全自動跑）

當使用者說「**幫我用主題 XX 做一份純圖片簡報**」且不想逐步確認時：

1. 快速跑完引擎 1–2（內心規劃、不詳細輸出）
2. 直接產出引擎三的 YAML 規格，**呈現給使用者確認**
3. 使用者確認後，一次跑完 I-1 → I-2 → I-3
4. 回報最終 pptx 路徑 + 總成本

---

## 林長揚 30 條簡報原則整合

本技能依林長揚提出的「AI 還不會的 30 個簡報秘訣」進行規則化分層整合。
來源：[知識庫/AI工作流/簡報設計 30 原則 — AI 做不到的人類判斷]

### A 層：硬規則（已寫入 pack_pptx.py 預設值）

| # | 原則 | 實作位置 |
|---|------|---------|
| 1 | 文字比例 55/34/21/13 | `defaults`：title=72、subtitle=34、body=21、muted=14 |
| 5 | 行距 50–75% | `line_spacing=1.2` 預設 |
| 7 | 黑體粗體 | `title_font: "GenSekiGothic2 TW H"`、title/subtitle/badge 強制 `bold=True` |
| 14 | 元素對齊 | 建議 spec 採固定 x 格點：左 `0.6/0.7`、雙欄 `5.1/7.2`、三欄 `0.6/4.85/9.1` |
| 17 | 表格框線越少越好 | `card` 預設無邊框（除非指定 `border`）|
| 21 | 固定品牌色 | `style.palette` 集中定義 |
| 24 | 淡灰 + 強調色聚焦 | `muted` 預設灰白、`primary/highlight` 強調 |
| 25 | 強調色 1–2 種 | palette 僅 primary + highlight 兩色 |
| 27 | 滿版圖片用於封面/段落/結尾 | baked 模式全頁滿版；plate 模式封面/行動頁建議滿版底圖 |

### B 層：軟規則（引擎三／引擎五自我檢查）

| # | 原則 | 檢查位置 |
|---|------|---------|
| 3 | 標題 ≤ 10 字 | 引擎三頁面架構 `on_image_text.title` 字數檢查 |
| 4 | 一張一重點 | 引擎三的 `core_point` 是否能壓縮成一句話 |
| 6 | 內容層級（主標、內文、註解） | 每頁 blocks 至少含 title + 一個其他類型 |
| 11 | 每秒 8 字 → 推算字數 | 引擎二估算每段朗讀時間 |
| 13 | Z 字排版順序 | 引擎三 `layout_hint` 安排視線起迄 |
| 18 | 多圖對齊、人像切圓 | 引擎六 I-4 插入規則 |
| 23 | 進度條減壓 | 用 `progress` block type（current/total）|

### C 層：純人類判斷（引擎一／二策略）

| # | 原則 | 在哪顆引擎 |
|---|------|----------|
| 2 | 先講觀眾在意的事 | 引擎二「引起動機」段規劃重點 |
| 19 | 準備三方案讓觀眾選 | 引擎三頁面類型可考慮「比較頁」|
| 20 | 用問句促進思考 | 引擎三「問題引入頁」大量使用 |
| 22 | 先痛苦後好處（避凶趨吉） | 引擎二三段節奏中設計 |
| 28 | 用比較幫判斷 | 引擎三「比較頁」當主要頁型 |
| 29 | 真實經驗帶來獨特 | 引擎一「最小事實包」可加入個人案例 |
| 30 | 簡報推動下一步行動 | 引擎二「喚起行動」段明確出口 |

### 整合使用方式

1. 跑引擎一前，先讀 `知識庫/AI工作流/簡報設計 30 原則` 記憶 C 層原則
2. 引擎三產出 YAML 時，自動套用 B 層檢查
3. 引擎五產出 `image_policy` 與 `spec.yaml` 時，pack_pptx.py 自動套 A 層
4. 最終檢查清單含 30 條對照（見下方）

### 進度條 block 範例（#23）

```yaml
- type: progress
  x: 0.6
  y: 7.15
  w: 12.2
  h: 0.12
  current: 5        # 目前第幾頁
  total: 10         # 總頁數
  color: primary    # 填充色（已完成）
  track: card       # 底條色（未完成）
```

---

## 最終檢查清單

- [ ] 每頁只有一個主重點
- [ ] on_image_text 中文字 ≤ 20 字
- [ ] 三段式脈絡完整（動機 → 注意 → 行動）
- [ ] 所有圖用 view 工具預覽過、無亂碼、無風格偏差
- [ ] 封面與行動頁已升級為 medium quality
- [ ] pptx 內每張 slide 都是 full-bleed、無黑邊
- [ ] 檔案大小合理（10 頁約 5–15 MB）

### 林長揚 30 條對照檢查（重點項）

- [ ] **#1** 文字比例：標題 >> 副標 >> 內文，階級明顯？
- [ ] **#3** 每頁標題 ≤ 10 字？（超過要拆）
- [ ] **#4** 一張一重點？（不是條列摘要頁）
- [ ] **#5** 行距足夠（不擠在一起）？
- [ ] **#13** 視線從左上到右下（Z 字）？
- [ ] **#14** 同類元素 x 座標一致（固定格點）？
- [ ] **#21** 整份簡報色系一致（品牌色）？
- [ ] **#25** 強調色 ≤ 2 種（不超過亮青藍＋金黃）？
- [ ] **#27** 封面／段落／結尾用滿版圖？
- [ ] **#2** 引起動機段有先講觀眾在意的事？
- [ ] **#30** 行動頁有清楚的下一步？

---

## 依賴

- `draw` skill（路徑 `C:/Users/mathr/.claude/skills/draw/draw.py`，gpt-image-2）
- `pack_pptx.py`（本技能內建，位於 skill 目錄下）
- Python 套件：`openai`、`python-pptx`、`Pillow`

```bash
pip install openai python-pptx Pillow --break-system-packages
```

前置：
- `OPENAI_API_KEY` 已設（shell / `.env` / `~/.openai.env`）
- OpenAI 組織已完成 Individual 驗證

---

## 模式選擇：baked vs plate

本技能有兩種產出模式，視使用情境選擇：

| 模式 | 圖內是否含文字 | 文字是否可編輯 | 產出腳本參數 | 適用 |
|------|--------------|--------------|------------|------|
| `baked`（預設） | ✅ 文字由 AI 生成在圖裡 | ❌ 不可編輯 | `--mode baked` | 社群貼文、直播、一次性素材 |
| `plate` | ❌ 純插畫底圖、無文字 | ✅ 文字是 pptx 文字框 | `--mode plate --spec spec.yaml` | 正式簡報、需交付給他人編輯、多版本 |

### plate 模式的引擎五改動

`image_policy` 要**強化負面提示**，並在 prompt 中明確要求留白區：

```yaml
image_policy:
  style_tokens: "..."
  negative: "不要任何文字、不要任何英文字母、不要任何符號、不要 logo"
  reserve_zones: "左側 40% 留空為純色底（供標題疊加）；上方 15% 與下方 15% 留純色底"
  size: "1536x1024"
  quality: "low"
```

### plate 模式的引擎六生圖 prompt 範本

```
{layout_hint}，整張圖不要任何文字。
留白規則：{reserve_zones}
圖像內容：{image_brief}
風格：{style_tokens}
避免：{negative}
```

### plate 模式的 spec.yaml 格式

```yaml
style:
  palette:
    bg: "#0D1B2A"
    primary: "#00C6FF"
    highlight: "#FFD700"
    text: "#FFFFFF"
    muted: "#A5B4CB"
    card: "#1E3A5F"
  font: "Microsoft JhengHei"

pages:
  - page: 1
    image: page_01           # 對應 images/page_01_*.png
    # 底圖定位（預設 full-bleed 0,0,13.333,7.5 英吋）
    img_x: 0
    img_y: 0
    img_w: 13.333
    img_h: 7.5
    bg: bg                   # 若底圖不滿版，背景色用 palette 的哪個鍵

    blocks:
      - type: badge          # 圓角徽章（底色 + 白字）
        text: "EP15"
        x: 0.7
        y: 0.7
        w: 2.2
        h: 0.5
        bg: primary          # 徽章底色
        color: bg            # 文字色
        size: 14

      - type: title          # 大標題
        text: "把 ChatGPT 生圖\n偷進 Claude Code"
        x: 0.7
        y: 1.6
        w: 6.5
        h: 2.5
        size: 48
        color: text
        bold: true

      - type: subtitle       # 副標
        text: "gpt-image-2 × 教學工作流"
        x: 0.7
        y: 4.75
        w: 6.5
        h: 1
        size: 22
        color: primary

      - type: bar            # 金色分隔線
        x: 0.7
        y: 4.5
        w: 1.2
        h: 0.05
        color: highlight

      - type: muted          # 底部署名
        text: "三師爸 Sense Bar"
        x: 0.7
        y: 6.8
        w: 6.5
        h: 0.4
        size: 14
```

**可用的 block type**：
- `title` / `subtitle` / `body` / `muted` / `highlight`：純文字框
- `badge`：圓角底色徽章 + 文字
- `card`：圓角卡片底色（無文字，用於視覺分區）
- `bar`：細橫條（裝飾線）

**通用欄位**：`x, y, w, h`（單位：英吋）、`size`（pt）、`bold`、`color`、`align`（left/center/right）、`anchor`（top/middle/bottom）
**顏色欄位**接受 palette key（`primary`、`highlight`...）或 hex（`#FF0000`）

### plate 模式的推薦工作流

1. 引擎 1–5 跑完，在引擎五特別強調 `reserve_zones`
2. 引擎三的 `on_image_text` 這次不丟給 AI，而是直接寫入 `spec.yaml` 的 blocks
3. 批次生圖（純底圖，無文字）
4. I-2 視覺確認：檢查留白區是否乾淨、無 AI 亂生文字
5. 撰寫 `spec.yaml`（用範本產出）
6. `python pack_pptx.py --mode plate --spec spec.yaml --images-dir images --output out.pptx`

### 三種模式的完整對照

| 產出模式 | 使用的 Skill | 文字來源 | 圖像角色 |
|---------|-------------|---------|---------|
| 文字為主 + 插圖 | `soil-teaching-deck` | pptx 文字框 | 小插圖（inset） |
| 整頁 AI 圖 | `soil-image-deck` + `baked` | AI 生在圖裡 | 全版主視覺 |
| **AI 底圖 + 可編輯文字** | **`soil-image-deck` + `plate`** | **pptx 文字框** | **全版設計底圖** |

---

## 與其他 Skill 的串接

| 上游 Skill | 串接方式 |
|-----------|---------|
| `lesson-prep` | 備課包產出後，把核心概念摘要丟進來做純圖片簡報 |
| `jh-math-exam` | 出題後，把題目轉成「題目情境卡片」純圖簡報（社群推廣用）|
| `teaching-minigames` | 遊戲規則用純圖簡報說明，當作遊戲開場 |

本技能也可以獨立使用，不需上游。

---

## 安裝踩坑紀錄

### 2026-05-09 | YAML frontmatter 解析失敗

**症狀：** 安裝過程出現 `Skill.md must start with YAML front matter` 警示，雖然檔案開頭明明就是 `---`。

**根因：** frontmatter 中 `description` 欄位用了 folded block scalar（`description: >`）寫法。雖然語法上合法，Claude Code 的 skill loader 對此欄解析較嚴格，遇到折疊型多行字串會誤判為「沒有 frontmatter」。

**修正：** 把 `description: >` 改成 `description: |`（literal block scalar），保留換行、loader 可正常解析。對照 `lecture-notes/SKILL.md` 也是用 `|` 寫法，跟它對齊即可。

**教訓：** 寫 Skill 時 frontmatter 統一用 `|`（literal）而非 `>`（folded），降低相容性風險。

**前置依賴：** 本 skill 需要 `draw` skill（呼叫 OpenAI gpt-image-2）；ChatGPT/Codex 訂閱者免另設 API key 即可使用 gpt-image-2（OpenAI 2026-04-21 公告）。


---

## 跨工具協作模式（推薦）

如果使用者**沒有設定 OpenAI API key**或明確說「圖像我自己用 Codex/ChatGPT 生」，本 skill 改走「跨工具協作 SOP」：

- Claude 跑引擎 1–5，產出 `specs/image_briefs.md`（每張圖一個獨立完整 prompt）
- 使用者去 ChatGPT 網頁版或 Codex CLI 跑 gpt-image-2 生圖，存到 `images/page_NN_<role>.png`
- 使用者回來說「圖好了」後，Claude 做 QA + 打包（image-deck 跑 `pack_pptx.py`、teaching-deck 寫 python-pptx、html-deck 寫 base64 內嵌 HTML）

**完整 SOP 請讀：** [`_shared/cross-tool-image-sop.md`](../_shared/cross-tool-image-sop.md)

**關鍵守則：**
1. 跑完引擎 5 一定要**停下來**等使用者生圖，不要假裝圖已生好
2. 嚴守檔名 `page_NN_<role>.png`（NN 補零）
3. 圖回來後**先 QA 再打包**（逐張檢查文字、風格、佈局）