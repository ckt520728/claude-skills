---
name: soil-teaching-deck
description: |
  SOIL 教學簡報工作流技能。以李俊儀教授的 SOIL Teaching Deck Workflow 六顆引擎為核心，
  引導使用者從素材或主題出發，經過概念定位、脈絡定位、頁面架構、認知編修、風格建構，
  最終產出一份有教學力的 .pptx 簡報。
  當使用者說「幫我做教學簡報」、「做一份上課用的投影片」、「幫我把教材做成簡報」、
  「這份簡報哪裡可以改」、「幫我分析這份教材的教學重點」、「用 SOIL 做簡報」、
  「幫我設計教學投影片」或任何涉及教學目的之簡報製作請求時，請一定要使用此技能。
  即使使用者只說「做簡報」但內容明顯是教學性質（如課程內容、學生學習、教材轉化），
  也應優先使用此技能而非一般簡報技能。
  此技能也處理教學簡報的診斷與改善：當使用者上傳現有簡報並詢問「哪裡可以改」、
  「幫我檢查這份簡報」、「這份投影片的認知負荷太高」時，同樣使用此技能。
---

# SOIL Teaching Deck Workflow

以李俊儀教授的 SOIL 教學心法為基礎的教學簡報工作流。
六顆引擎、一條清楚的路徑：先想清楚教什麼，再安排怎麼教，最後才處理怎麼呈現。

> 完整理論請參考 SOIL 工作流原始資料（本 skill 內未附 references 子目錄；若需要可請使用者提供）。

---

## 第一步：判斷工作模式

收到使用者請求後，不要直接開始做。先透過一個問題判斷工作模式。

**問使用者（只問這一題）：**

> 請問你目前的狀況是？
> 1. 我有素材（文字、教材、文件），想做成教學簡報
> 2. 我有現成簡報（.pptx），想改得更好
> 3. 我只有一個主題，想從頭開始
> 4. 我想定義一套簡報風格（YAML）給之後反覆使用

根據回答，進入對應路徑：

| 回答 | 工作模式 | 跑哪幾顆引擎 |
|-----|---------|------------|
| 1 | 全流程模式 | 引擎 1→2→3→4→5→6 |
| 2 | 診斷修改模式 | 引擎 4（+3 補頁面角色）→ 修改 .pptx |
| 3 | 全流程模式 | 先協助蒐集資料 → 引擎 1→2→3→4→5→6 |
| 4 | 風格定義模式 | 引擎 5 |

如果使用者的請求已經非常明確（例如直接貼了一大段教材說「做成簡報」），可以跳過這題，直接進入全流程模式，但在進入引擎一之前，先補問引擎一需要的細節。

---

## 第二步：在進入每顆引擎前，補問關鍵細節

不要一次問完所有問題。在進入對應引擎前，才問那顆引擎需要的最少資訊。

### 進入引擎一之前，補問：

> 關於這份教學簡報，我需要確認兩件事：
> 1. **教學對象是誰？**（例如：國中生、高中生、大學生、教師研習、一般成人）
> 2. **上課時間大約多長？**（例如：一節課 45 分鐘、兩節課、半天工作坊）

這兩個資訊會影響概念壓縮的深度和頁數規劃。

### 進入引擎五之前，補問：

> 你有偏好的簡報風格嗎？
> - 有參考簡報或圖片可以給我嗎？
> - 還是讓我根據教學內容自動配置？

如果使用者沒有偏好，就由系統自動決定，不需要再追問。

---

## 引擎一：SOIL 概念定位師

> 目標：從素材中抓出教學主軸，回答「這堂課到底要學生帶走什麼」

### 輸入
使用者提供的教材、文字、文件、或主題描述。

### 要做的事

分析素材，產出「概念定位稿」，包含以下六項：

1. **總概念**：這份內容最核心的 1 個概念（一句話）
2. **子概念**：支撐總概念的 3 個子概念
3. **常見誤解**：學生最容易產生的 3 個誤解
4. **帶走一句話**：如果學生最後只能記住一句話，那句話是什麼
5. **最小事實包**：支撐理解所需的最少事實
6. **投影片 vs 講稿**：哪些內容適合放投影片，哪些適合口頭補充

### 輸出格式

```
## 概念定位稿

### 總概念
[一句話]

### 三個子概念
1. [子概念 A]
2. [子概念 B]
3. [子概念 C]

### 三個常見誤解
1. [誤解 A] → 正確理解：[...]
2. [誤解 B] → 正確理解：[...]
3. [誤解 C] → 正確理解：[...]

### 帶走一句話
[那句話]

### 最小事實包
- [事實 1]
- [事實 2]
- ...

### 投影片 vs 講稿分配
| 內容 | 建議位置 | 原因 |
|-----|---------|------|
| ... | 投影片 | ... |
| ... | 講稿/口頭 | ... |
```

完成後，將概念定位稿呈現給使用者確認，再進入下一步。

---

## 引擎二：SOIL 脈絡定位師

> 目標：安排理解節奏，不是排章節

### 輸入
引擎一的概念定位稿 + 教學對象 + 時間長度。

### 要做的事

將整份簡報規劃成三段理解節奏：

| 節奏 | 功能 | 佔比建議 |
|-----|------|---------|
| **引起動機** | 讓學生知道這件事跟自己有關 | 15-20% |
| **維持注意** | 幫學生把資料組成關係 | 60-70% |
| **喚起行動** | 讓理解轉成可說、可判斷、可應用的結果 | 15-20% |

### 每段要說明

- 本段的教學目的
- 本段適合放入哪些內容（從概念定位稿中選取）
- 本段學生應完成的理解任務
- 本段建議頁數
- 本段的入口（怎麼開始）與出口（怎麼收）
- 本段最容易出現的設計錯誤

### 輸出格式

```
## 脈絡定位稿

### 第一段：引起動機（第 1-N 頁）
- 教學目的：...
- 放入內容：...
- 學生理解任務：...
- 建議頁數：N 頁
- 入口：...
- 出口：...
- 常見錯誤：...

### 第二段：維持注意（第 N-M 頁）
[同上格式]

### 第三段：喚起行動（第 M-末 頁）
[同上格式]
```

完成後呈現給使用者，確認節奏安排後再進入下一步。

---

## 引擎三：SOIL 頁面架構師

> 目標：給每一頁一個任務，不是列大綱

### 輸入
引擎二的脈絡定位稿。

### 要做的事

把三段式脈絡拆成具體頁面。每頁是一個「教學單位」，不只是「內容容器」。

### 可用的頁面角色

| 角色 | 用途 |
|-----|------|
| 封面頁 | 標題、副標、講師資訊 |
| 問題引入頁 | 用問題讓學生產生好奇 |
| 迷思澄清頁 | 呈現常見誤解，再翻轉為正確理解 |
| 比較頁 | 兩個概念並排對照 |
| 流程頁 | 步驟、順序、時間軸 |
| 分類頁 | 多個項目的歸類整理 |
| 案例頁 | 具體例子說明抽象概念 |
| 數據頁 | 大數字、統計、關鍵數據展示 |
| 總結頁 | 收攏重點，帶走一句話 |
| 行動頁 | 請學生做什麼（練習、討論、反思） |
| 過渡頁 | 章節之間的銜接（極簡，只有一句話） |

### 每頁要指定

- 頁碼
- 頁面標題
- 頁面角色
- 本頁唯一主重點（只能一個）
- 建議頁型（全版圖、雙欄、圖示列、大數字、時間軸等）
- 本頁要幫學生完成的理解任務
- 與前一頁的銜接
- 與下一頁的銜接
- 是否為關鍵投影片（★ 標記）
- **幾何圖形需求**（見下方「幾何圖形標記規則」）
- **AI 插畫需求**（見下方「AI 插畫標記規則」）

### ▶ AI 視覺素材標記規則（visuals 欄位）

當頁面需要**非幾何**的視覺素材時，使用 `visuals` 欄位（可多個）。引擎六將自動呼叫 `draw` skill（gpt-image-2）生成並嵌入投影片。

**視覺不等於「小插圖」**——本技能支援六種 `role`，每種有不同的視覺重量與排版功能，用來讓頁面更豐富：

| role | 用途 | 視覺重量 | 尺寸建議 | 典型位置 |
|------|------|---------|---------|---------|
| `illustration` | 傳統小插畫，搭配文字 | 中 | `1024x1024` | 右欄 `x=5.1 w=4.5` |
| `background` | **全版底圖**，文字疊加其上 | 最高 | `1536x1024` | 全版 `0,0,13.333,7.5`|
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

**visuals 欄位格式（新版，可多個）：**

```yaml
第 N 頁：[頁面標題]
- 頁面角色：問題引入頁
- visuals:
    - id: slide_N_bg
      role: background
      prompt: "一個國中生在黑板前看著數學題目困惑思考的扁平插畫，左側 40% 為純深藍色塊留白（供文字疊加）"
      size: 1536x1024
      quality: low
      # background 自動 full-bleed，不需 insert_at / width_in
      opacity: 1.0        # 可選：0-1，若要半透明讓文字更清楚
    - id: slide_N_accent
      role: accent
      prompt: "一個紅色大問號圖示，扁平向量"
      size: 1024x1024
      quality: low
      x: 8.5              # 自訂位置
      y: 4.5
      w: 2.0
      h: 2.0
```

**向後相容**：舊版 `illustration:` 欄位仍支援，自動轉成 `visuals: [{role: illustration, ...}]`。

> 一頁可以同時有 `geometry` 與 `visuals`（例如左幾何圖右情境圖）、或多個 `visuals`（例如 background + accent）。
> 風格一致性由引擎五的 `image_policy` 統一控管。

### 典型頁面 × 視覺組合（Layout Recipes）

| 頁面角色 | 建議組合 | 範例 |
|---------|---------|------|
| 封面頁 | `background` 或 `hero` + 大標題疊加 | 參考 EP15 plate 封面 |
| 問題引入 | `background` + 大問句文字 | 氛圍為主 |
| 迷思澄清 | 兩個 `accent`（左❌右✅）+ 說明文字 | 視覺對比 |
| 雙欄比較 | 兩個 `illustration` + 雙欄文字 | 左右對照 |
| 流程頁 | `side_panel` + 中央流程圖 | 側邊裝飾不空洞 |
| 數據頁 | `hero` + 大字數據 | 視覺衝擊 |
| 案例頁 | `illustration` + 內文 | 傳統排版 |
| 總結頁 | `background`（半透明）+ 條列 | 氣氛收尾 |
| 行動頁 | `background` + 大字口號 | 同封面 |
| 章節過場 | `section_divider` + 章節標題 | 全版視覺 |

### ▶ 幾何圖形標記規則（數學教學內容專用）

當頁面內容涉及幾何圖形時，在頁面角色表中加入 `geometry` 欄位。這個標記將在引擎六自動觸發圖形渲染並插入投影片。

**何時標記 geometry：**
- 需要示意圖說明幾何概念（三角形、四邊形、圓、立體圖等）
- 案例頁：「如圖所示，△ABC...」
- 流程頁：需要多個步驟圖（每步一圖）
- 比較頁：兩個圖形並排對照（subtype 各異的三角形、不同圓弧關係等）

**geometry 欄位格式（在頁面角色表中標記）：**

```
第 N 頁：[頁面標題]
- 頁面角色：案例頁
- geometry:
    mode: single          # single（單圖）/ side_by_side（並排最多3圖）
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
        width_cm: 10.0      # 插入投影片時的圖片寬度（cm），預設 12
```

> 完整圖形類型與 config 參數：見本 SKILL.md 末尾「幾何圖形參數速查（內嵌）」章節

### 自我檢查

輸出頁面角色表後，自我檢查：
- 是否超過一半的頁面都是同一種角色？→ 頁型過於單調，需要調整
- 是否有頁面的「唯一主重點」其實包含兩個以上概念？→ 該拆成兩頁
- 是否每頁都有明確的理解任務？→ 沒有的話代表這頁可能多餘
- **是否有幾何概念但忘記標記 geometry？** → 補上標記
- **封面頁／問題引入頁／案例頁／行動頁是否缺少主視覺？** → 考慮加 `illustration`

完成後呈現給使用者確認。

---

## 引擎四：SOIL 認知編修師

> 目標：用六個認知詞把每頁修成真正的教學頁

### 六個認知詞

這不是美化用語，而是教學簡報的處理語言：

| 認知詞 | 做什麼 | 怎麼判斷 |
|-------|-------|---------|
| **降雜訊** | 刪掉無助理解的元素 | 拿掉這個元素，學生的理解會變差嗎？不會就刪 |
| **區塊化** | 同類資訊歸在一起 | 學生能不能一眼看出這頁有幾個群組？ |
| **增資訊** | 補上理解的橋梁 | 兩個概念之間的關係標記夠清楚嗎？ |
| **結構化** | 讓主從關係可見 | 學生看得出哪個是主概念、哪個是子概念嗎？ |
| **順脈絡** | 排出合理的閱讀順序 | 學生的視線會自然按照你希望的順序走嗎？ |
| **步驟化** | 讓理解可以一步一步跟 | 如果用動態呈現，該分幾步出現？ |

### 對全流程模式

在引擎三完成頁面角色表之後，逐頁用六個認知詞預先規劃每頁的內容呈現方式，作為引擎六生成簡報時的指引。

### 對診斷修改模式

使用者上傳現有 .pptx 時：

1. 先用 `python -m markitdown` 提取文字內容
2. 用 pptx 技能的 `thumbnail.py` 或轉成圖片來看視覺佈局
3. 逐頁用六個認知詞診斷問題
4. 輸出「認知編修報告」

### 認知編修報告格式

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

---

## 引擎五：SOIL 風格建構師

> 目標：把風格固定成規則，讓整份簡報一致

風格不該太早處理。只有在教學骨架（引擎 1-4）都確定之後，才進入風格層。

### 如果使用者有參考簡報或圖片

進行風格逆向工程，分析：
- 整體風格氣質（正式/活潑/極簡/溫暖）
- 標題位置與層級規則
- 配色系統（主色、輔色、強調色）
- 空白配置
- 強調方式（色塊、底色、粗體、放大）
- 頁型偏好
- 圖像風格

### 如果使用者沒有偏好

根據教學對象和內容主題自動配置：

| 教學場景 | 建議配色 | 風格氣質 |
|---------|---------|---------|
| 國中/國小 | Teal Trust 或 Coral Energy | 活潑、對比強 |
| 高中 | Forest & Moss 或 Ocean Gradient | 清晰、穩重 |
| 大學/研究所 | Midnight Executive 或 Charcoal Minimal | 正式、知性 |
| 教師研習 | Sage Calm 或 Warm Terracotta | 溫暖、專業 |
| 通識/跨領域 | Berry & Cream 或 Cherry Bold | 有個性、吸引注意 |

### 風格規則（所有教學簡報通用）

- 標題位置一致（全部靠左或全部置中，不混用）
- 章節色一致（同一段用同一個色調）
- 同類頁型結構一致（所有比較頁長一樣、所有流程頁長一樣）
- 優先支援比較頁、流程頁、總結頁
- 風格服務核心概念理解，不追求商業感或炫技
- 每頁都要有視覺元素（色塊、形狀、圖示），不做純文字頁
- 不在標題下方加裝飾底線

### 輸出

產出一份風格設定摘要，在引擎六生成簡報時直接套用。包含：

- **視覺基礎**：配色（主色、輔色、強調色 HEX）、字型搭配、標題字級、內文字級、佈局偏好
- **image_policy**（若引擎三有任何頁面標記 `illustration`，必填）：
  - `style_tokens`：統一的圖像風格描述詞（如「扁平插畫、深藍背景、亮青藍線條、教室情境、16:9」）
  - `negative`：應避免的元素（如「不要逼真照片、不要英文字、不要雜亂背景」）
  - `default_size`：預設尺寸（`1024x1024` / `1536x1024` / `1024x1536`）
  - `default_quality`：預設品質（一般 `low`；封面或關鍵頁可升 `medium`）
  - `palette_hint`：圖像配色提示（與簡報主色調一致）

範例：

```yaml
image_policy:
  style_tokens: "扁平向量插畫、深夜藍#0D1B2A背景、亮青藍#00C6FF線條、金黃#FFD700點綴、教室或數位科技情境"
  negative: "不要逼真照片、不要文字、不要雜亂背景"
  default_size: 1536x1024
  default_quality: low
  palette_hint: "主色深藍、強調亮青藍、重點金黃"
```

`image_policy` 將在引擎六的 **I-1 批次生圖子流程**被套用，確保所有 AI 插畫風格統一。

---

## 引擎六：SOIL 簡報總導演

> 目標：整合前五顆引擎的結果，生成 .pptx

### 生成流程（三輪）

#### 第一輪：生骨架

整合以下材料：
- 概念定位稿（引擎一）
- 脈絡定位稿（引擎二）
- 頁面角色表（引擎三）
- 認知編修指引（引擎四）
- 風格設定（引擎五）

> ⚠️ **若頁面角色表中有任何 `geometry` 欄位，必須先完整跑完下方「▶ 幾何圖形整合子流程（G-1 至 G-4）」，確認所有幾何圖的 base64 資料已備妥，再來撰寫 PptxGenJS 腳本。**
>
> ⚠️ **若頁面角色表中有任何 `illustration` 欄位，必須先完整跑完下方「▶ AI 插畫整合子流程（I-1 至 I-3）」，確認所有 AI 插畫 PNG 已生成並轉 base64，再來撰寫 PptxGenJS 腳本。**
>
> 兩個子流程彼此獨立，可以並行執行。最終 PptxGenJS 腳本會同時載入 `geo_b64.json` 與 `illus_b64.json`。

用 PptxGenJS 生成完整 .pptx。

**技術執行：讀取 pptx 技能的技術文件**

```bash
# 讀取 PptxGenJS 完整 API 指南
cat /sessions/focused-exciting-heisenberg/mnt/.claude/skills/pptx/pptxgenjs.md
```

遵循 pptx 技能中的技術規範，並套用林長揚 #1 文字比例（55/34/21/13），升級到海報級字重：

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
| 標題／副標／徽章／強調 | `GenSekiGothic2 TW H`（源石黑體 Heavy，海報感）|
| 內文／註解 | `Microsoft JhengHei`（微軟正黑體，保可讀性）|

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
| 分類頁 | 2x2 或 2x3 網格 |
| 案例頁 | 圖片/情境 + 說明 |
| 數據頁 | 大數字 60-72pt + 小標籤 |
| 總結頁 | 條列收攏 + 帶走一句話 |
| 行動頁 | 深色背景 + 行動指引 |
| 過渡頁 | 全版色塊 + 一句話 |

---

### ▶ 幾何圖形整合子流程（**在撰寫 PptxGenJS 腳本之前**執行）

> 若引擎三的頁面角色表中有任何頁面標記了 `geometry` 欄位，必須在動手寫 PptxGenJS 腳本之前，先把所有幾何圖形全部生成好，再以 base64 嵌入 JS 腳本。
>
> **順序：幾何圖生成 → 轉 base64 → 寫 PptxGenJS（含 addImage）→ 執行生成 .pptx**
>
> 不要先生成骨架再後處理插圖。base64 嵌入的方式讓位置控制更精準，且不需要 python-pptx 後處理。

#### G-1：安裝依賴與確認腳本位置

```bash
pip install cairosvg Pillow --break-system-packages -q

GEOM_RENDERER="/mnt/skills/user/jh-math-geometry/scripts/geometry_renderer.py"
echo "幾何渲染器：$GEOM_RENDERER"
```

#### G-2：生成標準幾何圖形（使用 geometry_renderer.py）

針對引擎三標記的每個 `geometry` 欄位，建立對應的圖形規格 JSON，然後批次渲染：

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

> **視覺確認**：用 `view` 工具逐一查看生成的 `.png`，確認圖形標籤、角弧、等邊記號均正確。如有問題，調整 spec 重新生成，**不要繼續到下一步**。

#### G-3：生成自訂幾何圖形（geometry_renderer.py 不支援的圖形）

當需要「兩直線相交」、「帶延長線的外角圖」、「多角標色」等 renderer 不直接支援的圖形時，用 Python 直接呼叫 `SVGCanvas` 手繪：

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
    print(f"✅ {name}")

# 範例：兩直線相交（對頂角）
def make_vertical_angles():
    c = SVGCanvas(360, 280, 'white')
    W, H = 360, 280
    cx, cy = W/2, H/2
    angle1 = math.radians(35)
    angle2 = math.radians(110)
    r = 130
    # 直線 L
    c.line(cx + r*math.cos(angle1), cy - r*math.sin(angle1),
           cx - r*math.cos(angle1), cy + r*math.sin(angle1))
    # 直線 M
    c.line(cx + r*math.cos(angle2), cy - r*math.sin(angle2),
           cx - r*math.cos(angle2), cy + r*math.sin(angle2))
    c.dot(cx, cy, r=3.5)
    c.text(cx+8, cy+14, 'O', size=12, bold=True)
    # 角標籤與弧（可依需求調整位置）
    c.text(cx+28, cy-32, '∠1', size=13, color='#028090')
    c.text(cx-52, cy-28, '∠2', size=13, color='#028090')
    c.text(cx-52, cy+18, '∠3', size=13, color='#E36414')
    c.text(cx+22, cy+18, '∠4', size=13, color='#E36414')
    save(c, 'vertical_angles')

make_vertical_angles()
```

```bash
python3 /home/claude/geo_custom.py
```

**常用自訂圖形模板（直接複製修改）：**

| 圖形情境 | 自訂重點 |
|---------|---------|
| 兩直線相交（對頂角） | 用 `c.line()` 畫兩直線，手動算角弧位置 |
| 三角形外角和（帶延長虛線） | `c.polygon()` 畫三角形，`c.line(..., dash='5,4')` 畫延長線 |
| 三角形外角定理（∠CBD） | 延長一邊，用 `c.arc_path()` 標外角弧 |
| 平行線截角（多個角標色） | renderer 已支援 `parallel_lines` 型別，一般用 renderer 即可 |

#### G-4：轉換為 base64，供 PptxGenJS 使用

```python
# /home/claude/geo_to_b64.py
import base64, json
from pathlib import Path

geo_dir = Path("/home/claude/geo_out")
# 列出所有需要嵌入的圖形 id（對應引擎三 geometry 標記的 id）
figure_ids = [
    "slide_N_figX",       # 替換為實際的 figure id
    "vertical_angles",    # 自訂圖形
]

result = {}
for fid in figure_ids:
    png = geo_dir / f"{fid}.png"
    if png.exists():
        result[fid] = "image/png;base64," + base64.b64encode(png.read_bytes()).decode()
        print(f"✅ {fid} → {len(result[fid])} chars")
    else:
        print(f"⚠️  找不到 {png}")

with open('/home/claude/geo_b64.json', 'w') as f:
    json.dump(result, f)
print("完成：/home/claude/geo_b64.json")
```

```bash
python3 /home/claude/geo_to_b64.py
```

#### G-5：在 PptxGenJS 腳本中嵌入幾何圖

撰寫 PptxGenJS 腳本時，在最前面讀取 base64 資料，然後在對應頁面用 `addImage` 嵌入：

```javascript
const pptxgen = require("pptxgenjs");
const fs = require("fs");

// ── 讀取所有幾何圖形 ─────────────────────────────────────
const geo = JSON.parse(fs.readFileSync('/home/claude/geo_b64.json', 'utf8'));

// ...（其他設定）

// ── 在對應投影片嵌入幾何圖 ──────────────────────────────
// 位置單位為英吋；sizing.type = "contain" 保持比例
slide.addImage({
  data: geo["slide_N_figX"],   // 對應 figure id
  x: 0.4,   // 距左邊距（英吋）
  y: 1.5,   // 距頂部（英吋）
  w: 4.2,   // 圖片顯示寬度（英吋）
  h: 3.2,   // 圖片顯示高度（英吋）
  sizing: { type: "contain", w: 4.2, h: 3.2 }
});
```

**位置對照參考（LAYOUT_16x9，10" × 5.625"）：**

| 圖形位置 | x | w | 說明 |
|---------|---|---|------|
| 左欄（雙欄佈局） | 0.3 | 4.2 | 左右各約 4.5" |
| 右欄（雙欄佈局） | 5.1 | 4.5 | |
| 置中（全版圖） | 1.5 | 7.0 | |
| 右側小圖（文字為主） | 6.5 | 3.0 | |

---

### ▶ AI 視覺素材整合子流程（**在撰寫 PptxGenJS 腳本之前**執行）

> 若引擎三有任何頁面標記了 `visuals` 或舊版 `illustration` 欄位，必須在動手寫 PptxGenJS 腳本之前，先批次生成所有視覺素材，再嵌入腳本。
>
> **順序：批次生圖 → 視覺確認 → 嵌入 pptx**
>
> 本子流程使用使用者已安裝的 `draw` skill（gpt-image-2），腳本路徑：`C:/Users/mathr/.claude/skills/draw/draw.py`

### role 對應的生圖與嵌入規則

| role | draw.py 參數 | pptx 嵌入 |
|------|------------|-----------|
| `illustration` | size=`1024x1024`, quality=`low` | x=5.1, y=1.5, w=4.5, h=4.0 |
| `background` | size=`1536x1024`, quality=`low` 或 `medium` | 全版 `(0,0,13.333,7.5)` |
| `hero` | size=`1536x1024`, quality=`low` | x=6.7, y=0, w=6.7, h=7.5（右半版）|
| `side_panel` | size=`1024x1536`（直）, quality=`low` | x=0, y=0, w=3.0, h=7.5（左細條）|
| `section_divider` | size=`1536x1024`, quality=`medium` | 全版 |
| `accent` | size=`1024x1024`, quality=`low` | 依 block 的 x/y/w/h 自訂 |

**background / section_divider 的提示詞要求**：必須強制 negative「不要任何文字」，並指定留白區（例如「左側 40% 為純深色色塊供文字疊加」），否則會造成文字疊在插畫主體上可讀性差。

#### I-1：批次生成 AI 視覺素材（使用 draw.py）

針對引擎三標記的每個 `visuals` 條目（或舊版 `illustration`），**合併 `image_policy.style_tokens` 與該 visual 的 `prompt`**，依 role 對應表決定 size/quality，逐張呼叫 `draw.py`。

合併規則：

```
最終 prompt = "{page_prompt}，{style_tokens}，{negative}"
```

範例批次指令（Windows bash / Git Bash）：

```bash
mkdir -p slides/images

# 以引擎五的 image_policy 為基底
STYLE="扁平向量插畫、深夜藍#0D1B2A背景、亮青藍#00C6FF線條、金黃#FFD700點綴、教室或數位科技情境"
NEG="不要逼真照片、不要雜亂背景"
DRAW="python C:/Users/mathr/.claude/skills/draw/draw.py"

# 逐張生成（每張取一個對應 illustration id 的檔名前綴）
$DRAW "國中生在黑板前看著數學題目困惑思考，${STYLE}，${NEG}" \
  --size 1024x1024 --quality low --name slide_3_illus1 --outdir slides/images/

$DRAW "一張發光的火箭向上飛，象徵學習突破，${STYLE}，${NEG}" \
  --size 1536x1024 --quality low --name slide_10_illus1 --outdir slides/images/

ls slides/images/*.png
```

> **成本估算**：low 品質一張約 NT$0.3；一份 10 頁簡報若 4 頁有插畫，約 NT$1.2。
> **並行加速**：若張數多（>5），可把多個 `$DRAW ... &` 用 `&` 背景啟動後 `wait`，能省一半時間。

#### I-2：視覺確認（必做）

用 `view` 工具或直接開檔案逐一檢視生成的 PNG。檢查：

- 風格是否與 `image_policy.style_tokens` 一致？
- 是否符合頁面的教學用途？
- 是否有不該出現的文字／亂碼？
- 配色是否與簡報主色協調？

**若某張不合格**：調整 prompt 或升級 quality 為 `medium`，重新跑 I-1 的該張。**不要帶著不合格的圖進入 I-3**。

#### I-3：轉換為 base64，供 PptxGenJS 使用

```python
# illus_to_b64.py
import base64, json
from pathlib import Path
import glob

img_dir = Path("slides/images")
result = {}

# 對每個 illustration id（對應引擎三標記），找最新生成的 PNG
# draw.py 輸出檔名格式：<name>_<YYYYMMDD_HHMMSS>.png
illus_ids = [
    "slide_3_illus1",
    "slide_10_illus1",
    # ... 依引擎三標記補齊
]

for iid in illus_ids:
    candidates = sorted(glob.glob(str(img_dir / f"{iid}_*.png")))
    if not candidates:
        print(f"⚠️  找不到 {iid}")
        continue
    latest = Path(candidates[-1])  # 取時間戳最新的
    result[iid] = "image/png;base64," + base64.b64encode(latest.read_bytes()).decode()
    print(f"✅ {iid} → {latest.name}")

with open('illus_b64.json', 'w', encoding='utf-8') as f:
    json.dump(result, f)
print("完成：illus_b64.json")
```

```bash
python illus_to_b64.py
```

#### I-4：在 PptxGenJS 腳本中嵌入 AI 視覺素材

依 role 對應表取位置：

```javascript
const pptxgen = require("pptxgenjs");
const fs = require("fs");

// ── 讀取幾何圖與 AI 插畫 ───────────────────────────────
const geo = fs.existsSync('geo_b64.json')
  ? JSON.parse(fs.readFileSync('geo_b64.json', 'utf8')) : {};
const illus = fs.existsSync('illus_b64.json')
  ? JSON.parse(fs.readFileSync('illus_b64.json', 'utf8')) : {};

// ── 在對應投影片嵌入 AI 插畫 ──────────────────────────
// 位置單位為英吋；可依 illustration.insert_at / width_in 調整
slide.addImage({
  data: illus["slide_3_illus1"],
  x: 5.1,   // 右欄起始
  y: 1.5,
  w: 4.5,
  h: 3.0,
  sizing: { type: "contain", w: 4.5, h: 3.0 }
});
```

**background / section_divider（全版底圖）**：

```javascript
slide.addImage({
  data: illus["slide_1_bg"],
  x: 0, y: 0, w: 13.333, h: 7.5,
  sizing: { type: "cover", w: 13.333, h: 7.5 }
});
// 若需要暗化讓文字更清楚，疊半透明深色矩形
slide.addShape(pptx.shapes.RECTANGLE, {
  x: 0, y: 0, w: 6.5, h: 7.5,  // 左半版暗化
  fill: { type: "solid", color: "0D1B2A", transparency: 30 },
  line: { color: "0D1B2A", transparency: 100 }
});
// 再放標題文字（用亮色字在暗化區上）
```

**hero（半版主視覺）**：

```javascript
slide.addImage({
  data: illus["slide_1_hero"],
  x: 6.7, y: 0, w: 6.63, h: 7.5,
  sizing: { type: "cover", w: 6.63, h: 7.5 }
});
// 左側 6.7" 放文字
```

**side_panel（側邊細條）**：

```javascript
slide.addImage({
  data: illus["slide_3_panel"],
  x: 0, y: 0, w: 3.0, h: 7.5,
  sizing: { type: "cover", w: 3.0, h: 7.5 }
});
// 右側 10.3" 放主內容
```

**accent（小裝飾，依 block 指定 x/y/w/h）**：

```javascript
slide.addImage({
  data: illus["slide_2_q"],
  x: 8.5, y: 4.5, w: 2.0, h: 2.0,
  sizing: { type: "contain", w: 2.0, h: 2.0 }
});
```

---

#### 第二輪：修頁面

生成完成後，執行視覺 QA：

```bash
# 文字內容檢查
python -m markitdown output.pptx

# 轉成圖片逐頁檢查
python /sessions/focused-exciting-heisenberg/mnt/.claude/skills/pptx/scripts/office/soffice.py --headless --convert-to pdf output.pptx
rm -f slide-*.jpg
pdftoppm -jpeg -r 150 output.pdf slide
ls -1 "$PWD"/slide-*.jpg
```

用子代理（subagent）以新鮮眼光檢查每張投影片：
- 元素是否重疊
- 文字是否溢出
- 間距是否一致
- 對比是否足夠
- 頁面角色是否清楚（看得出這頁在做什麼嗎？）
- **幾何圖形是否正確對齊、比例是否合適**
- **AI 插畫是否風格一致（整份看起來像同一套素材）、不與文字重疊、主視覺清楚**

修正問題後重新生成。

#### 第三輪：最終檢查

用以下清單逐項確認：

- [ ] 每頁只有一個主重點
- [ ] 教學脈絡三段式完整（動機→注意→行動）
- [ ] 頁面角色多元（不是全部都是條列摘要頁）
- [ ] 關鍵投影片有被突顯
- [ ] 帶走一句話有出現在總結頁
- [ ] 常見誤解有被處理
- [ ] 風格一致（配色、字型、標題位置）
- [ ] 無純文字頁（每頁都有視覺元素）
- [ ] 內容完整、沒有遺漏
- [ ] **有 geometry 標記的頁面，幾何圖形均已用 view 工具預覽過 PNG、確認正確後才嵌入**
- [ ] **幾何圖在投影片內對齊正確、比例合適、不與文字重疊**
- [ ] **有 illustration 標記的頁面，AI 插畫均已通過 I-2 視覺確認**
- [ ] **所有 AI 插畫風格一致（配色、畫風、筆觸一致），符合 image_policy**
- [ ] **封面、問題引入、案例、行動頁等情境頁面有主視覺，不是純文字**

### 輸出

將最終 .pptx 存到使用者的工作資料夾，提供下載連結。
簡要說明投影片架構（幾頁、三段式各幾頁、有哪些關鍵頁）。

---

## 診斷修改模式（使用者帶現有 .pptx 進來）

當使用者帶著現有簡報進來時，不走全流程，而是：

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

向使用者呈現診斷結果，標示修改優先級（高/中/低）。

### Step 5：確認後執行修改

使用者確認要修改哪些之後，才進行實際修改。修改後再次 QA 驗證。

---

## 風格定義模式（使用者要產出 YAML）

當使用者只想定義風格規則時：

1. 請使用者提供參考簡報或圖片
2. 執行引擎五的風格逆向工程
3. 產出風格設定摘要，存為獨立檔案
4. 說明這份風格設定可以在未來製作教學簡報時直接套用

---

## 林長揚 30 條簡報原則整合

本技能整合林長揚「AI 還不會的 30 個簡報秘訣」作為引擎五與引擎六的品質檢查規則。
完整條目見 [知識庫/AI工作流/簡報設計 30 原則 — AI 做不到的人類判斷]。

### 硬規則（引擎五風格建構師自動套用）

| # | 原則 | 實作方式 |
|---|------|---------|
| 1 | 文字比例 55/34/21/13 | 標題 36–44pt、副標 24–28pt、內文 14–16pt、註解 10–12pt（依 pptx 投影片比例調整）|
| 5 | 行距 50–75% | python-pptx 設 `paragraph.line_spacing=1.2` |
| 7 | 黑體粗體 | 標題用重磅字（如 GenSekiGothic2 TW H）、副標 Bold |
| 14 | 元素對齊 | 固定格點 x：左 0.5/0.7、雙欄 5.1/7.2、三欄 0.6/4.85/9.1 |
| 17 | 表格框線越少越好 | 預設表格無外框、僅用空白分隔 |
| 21, 25 | 品牌色固定、強調色 1–2 種 | 引擎五風格設定僅 primary + accent |
| 24 | 淡灰 + 強調色聚焦 | 次要資訊用 muted 灰、重點用強調色 |
| 27 | 滿版圖片用於封面/結尾 | 封面頁、行動頁建議全版深色背景 |

### 軟規則（引擎三頁面架構自我檢查）

- **#3 標題 ≤ 10 字**：每頁標題字數檢查（超過要拆）
- **#4 一張一重點**：引擎三檢查「唯一主重點」是否只包含一個概念
- **#6 內容層級**：每頁至少含主標 + 內文兩層
- **#13 Z 字排版**：頁面角色內的 layout 指引視線從左上到右下
- **#18 多圖對齊**：多張圖片 x/y/w/h 統一
- **#23 進度條減壓**：長簡報（>15 頁）底部加進度條

### 純人類判斷（引擎一／二策略）

- **#2 先講觀眾在意的事** → 引擎二「引起動機」段落重點
- **#19 三方案** → 引擎三「比較頁」或「分類頁」
- **#20 用問句促進思考** → 引擎三「問題引入頁」
- **#22 先痛苦後好處** → 引擎二三段節奏安排
- **#28 用比較幫判斷** → 「比較頁」當主力頁型
- **#29 真實經驗帶來獨特** → 引擎一「最小事實包」可加教師個人案例
- **#30 推動下一步行動** → 引擎二「喚起行動」段出口

### 最終檢查清單擴充

除原有檢查項外，另加林長揚重點項：
- [ ] #1 標題／副標／內文字級階層分明
- [ ] #3 每頁標題 ≤ 10 字
- [ ] #14 同類元素 x 座標一致
- [ ] #25 強調色不超過 2 種
- [ ] #2 動機段有先講觀眾在意的事
- [ ] #30 行動頁有清楚下一步

---

## 核心原則（貫穿所有模式）

這些原則來自 SOIL 教學心法，是所有判斷的底層邏輯：

1. **教學簡報 ≠ 商業簡報**：重點在降低認知負荷、促進理解，不在說服或推銷
2. **教師視角 vs 學生視角**：教師設計順序是「核心概念→關鍵佈局→單頁佈局」，但學生的理解順序是反過來的。從學生的接收順序出發來設計
3. **一頁一重點**：每張投影片只承載一個主要概念
4. **頁面是教學單位**：每頁都有角色和任務，不只是內容容器
5. **風格服務理解**：所有視覺決定都要能回答「這樣做，學生是不是更容易懂？」
6. **先教學判斷，後工具操作**：概念→脈絡→頁面→認知→風格→生成，順序不能反

---

## 依賴

本技能在生成 .pptx 時，需要讀取 pptx 技能的技術文件：

- `pptx/pptxgenjs.md` — PptxGenJS 完整 API（建立新簡報）
- `pptx/editing.md` — 編輯現有 .pptx 的流程
- `pptx/scripts/` — 轉換與檢查工具

本技能在生成幾何圖形時，需要的腳本（已內建，無需呼叫外部技能）：
- `/mnt/skills/user/jh-math-geometry/scripts/geometry_renderer.py` — SVG 渲染引擎
- `/mnt/skills/user/jh-math-geometry/scripts/insert_to_pptx.py` — 插入 PPTX 工具
- 圖形參數速查 → 見下方「幾何圖形參數速查（內嵌）」章節，無需讀取外部檔案

本技能在生成 AI 插畫時，依賴使用者的 **draw skill**：
- 腳本：`C:/Users/mathr/.claude/skills/draw/draw.py`
- 模型：OpenAI **gpt-image-2**
- 前置：`OPENAI_API_KEY` 已設在 shell、`.env`、或 `~/.openai.env`；OpenAI 組織已完成 Individual 驗證
- 成本：low 約 NT$0.3/張、medium 約 NT$1.3/張、high 約 NT$5.5/張（預設用 low）

```bash
# 需要的套件
pip install "markitdown[pptx]" --break-system-packages
pip install Pillow cairosvg python-pptx openai --break-system-packages
npm install -g pptxgenjs
```

---

## 幾何圖形參數速查（內嵌）

> 本章節完整收錄所有支援的圖形類型與參數，撰寫引擎三的 `geometry` 標記時直接查閱，無需讀取外部檔案。

### 通用結構

```json
{
  "id": "fig1",
  "type": "<圖形類型>",
  "config": { ... },
  "canvas": { "width": 360, "height": 280 }
}
```

批次規格（提供給 `geometry_renderer.py`）：

```json
{
  "figures": [ {...}, {...} ],
  "options": { "format": "png", "dpi": 150 }
}
```

> 簡報用圖建議 canvas：`360×280`；並排比較圖各用 `240×200`

---

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

**常用範例**：

直角三角形（直角在 C）：
```json
{"type":"triangle","config":{"subtype":"right","vertex_labels":["A","B","C"],"right_angle_at":"C","side_labels":{"AB":"5","BC":"3","CA":"4"}}}
```

等腰三角形（標等邊 + 底角）：
```json
{"type":"triangle","config":{"subtype":"isosceles","equal_marks":{"AB":1,"AC":1},"angle_arcs":{"B":1,"C":1}}}
```

---

### 2. quadrilateral（四邊形）

| 參數 | 說明 |
|------|------|
| `subtype` | `parallelogram` / `rectangle` / `rhombus` / `square` / `trapezoid` / `right_trapezoid` / `general` |
| `vertex_labels` | 頂點標籤陣列，預設 `["A","B","C","D"]` |
| `side_labels` | 各邊文字標籤 |
| `equal_marks` | 等邊刻度 |
| `right_angles` | 標直角的頂點陣列 |
| `diagonals` | 是否畫對角線，`true/false` |
| `diagonal_labels` | 對角線標籤 `{"AC":"m","BD":"n"}` |

**常用範例**：

平行四邊形（含對角線）：
```json
{"type":"quadrilateral","config":{"subtype":"parallelogram","vertex_labels":["A","B","C","D"],"diagonals":true,"equal_marks":{"AB":1,"CD":1,"BC":2,"AD":2}}}
```

等腰梯形：
```json
{"type":"quadrilateral","config":{"subtype":"trapezoid","vertex_labels":["A","B","C","D"],"equal_marks":{"AB":1,"CD":1}}}
```

---

### 3. circle（圓）

| 參數 | 說明 |
|------|------|
| `center_label` | 圓心標籤，預設 `"O"` |
| `show_center` | 是否顯示圓心點 |
| `points` | 圓周上各點：`{"A": 60, "B": 160}`（角度，0=右，90=上，逆時針）|
| `radius_lines` | 畫半徑線的點陣列 |
| `radius_label` | 半徑標籤 |
| `chords` | 弦：`[["A","B"],["C","D"]]` |
| `diameter` | 直徑端點 `["A","C"]` |
| `tangent_at` | 切線點 |
| `central_angle` | 填色扇形（圓心角）兩端點 |
| `inscribed_angle` | 圓周角：`{"vertex":"C","arc":["A","B"]}` |

**常用範例**：

圓心角與圓周角：
```json
{"type":"circle","config":{"center_label":"O","points":{"A":30,"B":150,"C":270},"radius_lines":["A","B"],"central_angle":["A","B"],"inscribed_angle":{"vertex":"C","arc":["A","B"]}}}
```

---

### 4. coordinate_plane（坐標平面）

| 參數 | 說明 |
|------|------|
| `x_range` | x 軸範圍，如 `[-5, 5]` |
| `y_range` | y 軸範圍 |
| `show_grid` | 是否顯示格線 |
| `tick_interval` | 刻度間隔 |
| `points` | 點陣列：`[{"x":1,"y":2,"label":"A","color":"#cc0000"}]` |
| `lines` | 直線：`[{"slope":2,"intercept":-1,"label":"y=2x-1"}]` |
| `parabolas` | 拋物線：`[{"a":1,"b":0,"c":-2,"label":"y=x²-2"}]` |
| `segments` | 線段：`[{"x1":0,"y1":0,"x2":3,"y2":4}]` |

**常用範例**：

一次函數 y=2x-1：
```json
{"type":"coordinate_plane","config":{"x_range":[-3,5],"y_range":[-4,8],"lines":[{"slope":2,"intercept":-1,"label":"y=2x-1"}],"points":[{"x":0,"y":-1,"label":"(0,-1)"}]}}
```

拋物線 y=x²-2x-3：
```json
{"type":"coordinate_plane","config":{"x_range":[-2,5],"y_range":[-5,6],"parabolas":[{"a":1,"b":-2,"c":-3,"label":"y=x²-2x-3"}]}}
```

---

### 5. solid_3d（立體圖形）

| subtype | 說明 | 頂點順序 |
|---------|------|---------|
| `rectangular_prism` | 四角柱（長方體）| ABCD（上）EFGH（下）|
| `cylinder` | 圓柱 | labels: radius, height |
| `cone` | 圓錐 | labels: apex, base, radius, slant, height |
| `triangular_prism` | 三角柱 | ABC（後）DEF（前）|
| `square_pyramid` | 四角錐 | ABCD（底）P（頂）|
| `triangular_pyramid` | 三角錐 | ABCD |

共用參數：`show_hidden`（虛線稜）、`vertex_labels`、`labels`（標示半徑/高/斜高）

四角柱（標頂點 + 虛線）：
```json
{"type":"solid_3d","config":{"subtype":"rectangular_prism","vertex_labels":["A","B","C","D","E","F","G","H"],"show_hidden":true}}
```

---

### 6. parallel_lines（平行線截角）

| 參數 | 說明 |
|------|------|
| `n_parallel` | 平行線條數（通常 2） |
| `line_labels` | 平行線標籤 `["l","m"]` |
| `transversal_angle` | 截線角度（度）|
| `transversal_labels` | 截線標籤 `["t"]` |
| `angle_marks` | 角度標記：`[{"line":0,"position":"upper_left","label":"A"}]`；position 為 `upper_left/upper_right/lower_left/lower_right` |

兩平行線被截，標同位角：
```json
{"type":"parallel_lines","config":{"n_parallel":2,"line_labels":["l","m"],"transversal_angle":55,"angle_marks":[{"line":0,"position":"upper_left","label":"A"},{"line":1,"position":"upper_left","label":"E"}]}}
```

---

### 7. triangle_center（三角形的心）

| `center_type` | 說明 | 預設標籤 |
|--------------|------|---------|
| `centroid` | 重心（三條中線）| G |
| `circumcenter` | 外心（外接圓）| O |
| `incenter` | 內心（內切圓）| I |

```json
{"type":"triangle_center","config":{"center_type":"centroid","center_label":"G","triangle":{"subtype":"general","vertex_labels":["A","B","C"]}}}
```

---

### 8. similar_triangles（相似三角形）

兩個三角形各自設定，並排呈現，相同角弧表示相等角：

```json
{"type":"similar_triangles","config":{"triangle1":{"vertex_labels":["A","B","C"],"angle_arcs":{"A":1,"B":2},"side_labels":{"AB":"3","BC":"4","CA":"5"}},"triangle2":{"vertex_labels":["D","E","F"],"angle_arcs":{"D":1,"E":2},"side_labels":{"DE":"6","EF":"8","FD":"10"}}}}
```

---

### 快速複製區（簡報最常用）

| 頁面情境 | 直接複製的 spec |
|---------|---------------|
| 畢氏定理示意 | `{"type":"triangle","config":{"subtype":"right","vertex_labels":["A","B","C"],"right_angle_at":"C","side_labels":{"AB":"c","BC":"a","CA":"b"}}}` |
| 全等三角形 | `{"type":"triangle","config":{"subtype":"general","vertex_labels":["A","B","C"],"equal_marks":{"AB":1,"BC":2,"CA":3}}}` |
| 圓心角＋圓周角 | `{"type":"circle","config":{"center_label":"O","points":{"A":30,"B":150,"C":270},"radius_lines":["A","B"],"central_angle":["A","B"],"inscribed_angle":{"vertex":"C","arc":["A","B"]}}}` |
| 平行四邊形對角線 | `{"type":"quadrilateral","config":{"subtype":"parallelogram","vertex_labels":["A","B","C","D"],"diagonals":true,"equal_marks":{"AB":1,"CD":1,"BC":2,"AD":2}}}` |
| 等腰梯形 | `{"type":"quadrilateral","config":{"subtype":"trapezoid","vertex_labels":["A","B","C","D"],"equal_marks":{"AB":1,"CD":1}}}` |
| 四角柱 | `{"type":"solid_3d","config":{"subtype":"rectangular_prism","vertex_labels":["A","B","C","D","E","F","G","H"],"show_hidden":true}}` |
| 重心示意 | `{"type":"triangle_center","config":{"center_type":"centroid","center_label":"G","triangle":{"subtype":"general","vertex_labels":["A","B","C"]}}}` |
| 相似三角形 | `{"type":"similar_triangles","config":{"triangle1":{"vertex_labels":["A","B","C"],"angle_arcs":{"A":1,"B":2}},"triangle2":{"vertex_labels":["D","E","F"],"angle_arcs":{"D":1,"E":2}}}}` |
| 一次函數 | `{"type":"coordinate_plane","config":{"x_range":[-3,5],"y_range":[-4,8],"lines":[{"slope":2,"intercept":-1,"label":"y=2x-1"}]}}` |
| 拋物線 | `{"type":"coordinate_plane","config":{"x_range":[-2,5],"y_range":[-5,6],"parabolas":[{"a":1,"b":-2,"c":-3,"label":"y=x²-2x-3"}]}}` |

---

## 安裝踩坑紀錄

### 2026-05-09 | YAML frontmatter 解析失敗

**症狀：** 安裝過程出現 `Skill.md must start with YAML front matter` 警示，雖然檔案開頭明明就是 `---`。

**根因：** frontmatter 中 `description` 欄位用了 folded block scalar（`description: >`）寫法。雖然語法上合法，Claude Code 的 skill loader 對此欄解析較嚴格，遇到折疊型多行字串會誤判為「沒有 frontmatter」。

**修正：** 把 `description: >` 改成 `description: |`（literal block scalar），保留換行、loader 可正常解析。

**附帶問題：** 原 frontmatter 後 `> 完整理論參考：讀取 [references/soil-theory.md]`，但 zip 內並未附 references 子目錄；連結是 dead link，已改成中性註記，避免執行時 Read 失敗。

**教訓：** 寫 Skill 時 frontmatter 統一用 `|`（literal）而非 `>`（folded）；引用外部檔案前先確認檔案存在或至少在 SKILL.md 同層。

**前置依賴：** 本 skill 可呼叫 `draw` skill（gpt-image-2）插圖；ChatGPT/Codex 訂閱者免另設 API key 即可使用 gpt-image-2（OpenAI 2026-04-21 公告）。


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