# Image Deck 模式（純圖片簡報）

> 使用情境：每頁都是一張 gpt-image-2 整張圖、文字燒在圖裡不可編輯、打包成 .pptx
>
> 適用：直播暖場、社群貼文、視覺衝擊型開場、快速原型
> 不適用：需後續編輯文字、大量精細資料、需要動畫互動 → 改用 teaching 模式或 html 模式

本檔案接續主 SKILL.md 的引擎 1–5，提供 image 模式專屬的引擎三補充規格 + 引擎六執行流程。

---

## 引擎三補充：每頁要產出 image brief

每頁除了主 SKILL.md 列的共用欄位，**額外**指定：

- **on_image_text**：圖上要出現的文字（**極少！**通常只有一個標題 + 0–2 個關鍵詞）
- **image_brief**：這張圖的核心構圖（主角、場景、動作、象徵物）
- **layout_hint**：版面佈局（置中大標／左文右圖／上圖下標／全版背景＋浮字／分格對比…）

### YAML 規格範例

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
> gpt-image-2 文字渲染雖正確但仍有上限，**每張圖建議中文字 ≤ 20 字、片段 ≤ 3 段**。
> 超過要拆成多頁，或改用 teaching 模式。

---

## 引擎四補充：六詞如何對應「圖像語言」

| 認知詞 | 在純圖片簡報裡怎麼問 |
|-------|---------------------|
| 降雜訊 | image_brief 有沒有多餘的裝飾物、次要角色？可刪除 |
| 區塊化 | layout_hint 有沒有明確的視覺分群（上下／左右／中心）？ |
| 增資訊 | 需要補符號（→、vs、✓、✗）、數字、色差嗎？ |
| 結構化 | 一看就知道主角和配角嗎？對比度夠嗎？ |
| 順脈絡 | layout_hint 有安排視線起點與終點嗎？ |
| 步驟化 | 流程頁是否有編號、箭頭指引？ |

逐頁用六詞檢視 `image_brief` 與 `on_image_text`，必要時回去修引擎三的規格。

---

## 引擎五補充：image_policy 完整規格

```yaml
image_policy:
  # 風格描述（會串接進每張生圖 prompt）
  style_tokens: "扁平向量插畫、16:9 橫版、深夜藍#0D1B2A 背景、亮青藍#00C6FF 主色、金黃#FFD700 點綴、現代教育科技風"

  # 負面提示
  negative: "不要逼真照片、不要雜亂背景、不要英文字、不要亂碼"

  # 固定設定
  size: "1536x1024"            # 16:9 橫版
  quality: "low"               # 預設 low；封面或關鍵頁可升 medium
  font_feel: "粗體無襯線、標題大字"

  # 配色提示
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

---

## 引擎六：純圖片版總導演（I-1 → I-2 → I-3）

### I-1：批次生圖

對每一頁，合併 `style_tokens` + `on_image_text` + `image_brief` + `layout_hint` 組成最終 prompt：

```
{layout_hint}。
圖像內容：{image_brief}。
圖上文字：標題「{on_image_text.title}」、{其他文字描述}。
風格：{style_tokens}。
避免：{negative}。
```

批次呼叫 `draw.py`：

```bash
mkdir -p slides/images
DRAW="python C:/Users/mathr/.claude/skills/draw/draw.py"
SIZE="1536x1024"

# 頁 1（封面升 medium）
$DRAW "左文右圖。圖像內容：Q版機器人老師...。圖上文字：標題「把 ChatGPT 生圖偷進 Claude Code」、副標「gpt-image-2 × 教學工作流」、標籤「EP15」。風格：扁平向量插畫、16:9 橫版、深夜藍#0D1B2A 背景、亮青藍#00C6FF 主色...。避免：不要逼真照片、不要亂碼。" \
  --size $SIZE --quality medium --name page_01 --outdir slides/images/

# 頁 2 起（low）
$DRAW "全版插畫 + 大問句。圖像內容：一個卡通老師站在兩條岔路前...。圖上文字：標題「能偷進來嗎？」。風格：...。" \
  --size $SIZE --quality low --name page_02 --outdir slides/images/
```

**並行加速**：頁數多時，每 3–4 張用 `&` 背景跑 + `wait`，可省一半時間。

**成本估算**：
- 預設 10 頁：9 張 low + 1 張 medium ≈ NT$(0.3×9 + 1.3) = **NT$4.0**
- 15 頁：14 張 low + 1 張 medium ≈ **NT$5.5**

### I-2：視覺確認（必做）

批次生完後，**逐張用 view 工具檢查**：

- 圖上文字是否正確、無亂碼？
- 風格是否與 `image_policy` 一致？
- 佈局是否符合 `layout_hint`？
- 關鍵頁（封面、結語）品質是否夠？

**不合格處理**：
- 文字錯字 → 改 prompt 中文字部分，重跑該頁
- 風格偏移 → 檢查 style_tokens 是否被截斷
- 品質不足 → 升級 quality 為 medium

> ⚠️ 不要讓任何一張不合格的圖進入 I-3。

### I-3：打包成 PPTX（baked 模式）

使用內建腳本 `pack_pptx.py`：

```bash
python ../scripts/pack_pptx.py \
  --images-dir slides/images \
  --output slides/我的簡報.pptx \
  --mode baked
```

**腳本行為**（baked 模式）：
- 讀取 `slides/images/page_NN_*.png`（依檔名前綴排序）
- 每張圖以 full-bleed（滿版）方式填入一張 16:9 slide
- 不加任何文字（文字已在圖上）
- 輸出單一 .pptx 檔

---

## 進階：plate 模式（AI 底圖 + 可編輯文字）

如果使用者要「整體設計感像純圖簡報，但文字要可編輯」，這其實是 image / teaching 兩模式的**混合**。
推薦走 image 模式但用 plate 子模式：

### plate 子模式的引擎五改動

`image_policy` 要**強化負面提示**，並在 prompt 中明確要求留白區：

```yaml
image_policy:
  style_tokens: "..."
  negative: "不要任何文字、不要任何英文字母、不要任何符號、不要 logo"
  reserve_zones: "左側 40% 留空為純色底（供標題疊加）；上方 15% 與下方 15% 留純色底"
  size: "1536x1024"
  quality: "low"
```

### plate 子模式的 spec.yaml 格式

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
    img_x: 0
    img_y: 0
    img_w: 13.333
    img_h: 7.5
    bg: bg

    blocks:
      - type: badge          # 圓角徽章（底色 + 白字）
        text: "EP15"
        x: 0.7
        y: 0.7
        w: 2.2
        h: 0.5
        bg: primary
        color: bg
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

**可用 block type**：
- `title` / `subtitle` / `body` / `muted` / `highlight`：純文字框
- `badge`：圓角底色徽章 + 文字
- `card`：圓角卡片底色（無文字，視覺分區）
- `bar`：細橫條（裝飾線）
- `progress`：進度條（林長揚 #23）

**通用欄位**：`x, y, w, h`（單位：英吋）、`size`（pt）、`bold`、`color`、`align`（left/center/right）、`anchor`（top/middle/bottom）

**顏色欄位**接受 palette key（`primary`、`highlight` …）或 hex（`#FF0000`）

### plate 子模式打包指令

```bash
python ../scripts/pack_pptx.py \
  --mode plate \
  --spec spec.yaml \
  --images-dir slides/images \
  --output slides/我的簡報.pptx
```

---

## 自動化模式（使用者給主題就全自動跑）

當使用者說「**幫我用主題 XX 做一份純圖片簡報**」且不想逐步確認時：

1. 快速跑完引擎 1–2（內心規劃、不詳細輸出）
2. 直接產出引擎三的 YAML 規格，**呈現給使用者確認**
3. 使用者確認後，一次跑完 I-1 → I-2 → I-3
4. 回報最終 pptx 路徑 + 總成本

---

## 最終檢查清單（image 模式）

- [ ] 每頁只有一個主重點
- [ ] `on_image_text` 中文字 ≤ 20 字
- [ ] 三段式脈絡完整（動機→注意→行動）
- [ ] 所有圖用 view 工具預覽過、無亂碼、無風格偏差
- [ ] 封面與行動頁已升級為 medium quality
- [ ] pptx 內每張 slide 都是 full-bleed、無黑邊
- [ ] 檔案大小合理（10 頁約 5–15 MB）
- [ ] 林長揚 #1 字級階層、#3 標題 ≤ 10 字、#13 Z 字、#21 品牌色、#25 強調色 ≤ 2、#27 滿版圖、#2 動機、#30 行動

---

## 踩坑紀錄

| 坑 | 解法 |
|----|------|
| AI 圖中文字亂碼 | 縮短文字（≤ 20 字），降低字數密度，必要時拆兩頁 |
| 風格偏移（後幾張變成不同畫風） | 檢查 `style_tokens` 是否被 prompt 截斷；可拆成多次 `--name` 重跑 |
| pptx 打開後比例變形 | `pack_pptx.py` 已用 `crop_to_ratio` 自動裁切；確認 slide_width/height 都用 13.333×7.5 |
| 想要文字可編輯 | 改用 plate 子模式（本檔末段）或 teaching 模式 |
