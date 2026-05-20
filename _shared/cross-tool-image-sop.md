---
title: SOIL 跨工具協作 SOP（Claude 規劃 × Codex/ChatGPT 生圖 × Claude 打包）
date: 2026-05-09
type: sop
applies_to:
  - soil-image-deck
  - soil-teaching-deck
  - soil-html-deck
---

# SOIL 跨工具協作 SOP

> **核心原則：** 用 Claude 強的地方（規劃、文字、打包），用 Codex/ChatGPT 強的地方（gpt-image-2 生圖），中間用檔案傳遞。
> **適用 Skill：** `soil-image-deck`、`soil-teaching-deck`、`soil-html-deck`

---

## 一、角色分工

| 工具 | 負責 | 為什麼 |
|---|---|---|
| **Claude Code（你目前用的）** | 引擎 1–5：概念定位 → 脈絡定位 → 頁面架構 → 認知編修 → 風格建構；最後階段：圖片 QA + `pack_pptx.py` 打包 / 寫 HTML / 寫 PptxGenJS | Claude 規劃、推理、寫程式強，但不能直接呼叫 OpenAI 生圖 |
| **Codex CLI 或 ChatGPT 網頁版（你訂閱了）** | 引擎 6 的 I-1 階段：批次呼叫 `gpt-image-2` 生圖 | 你的 ChatGPT/Codex 訂閱直接含 gpt-image-2 取用權，免另設 API key |
| **你** | 中介傳遞檔案、品質把關 | 兩個工具不會自動互通，需要你扮演 conductor |

---

## 二、固定專案結構（**所有 deck 共用**）

開新專案時 Claude 會自動建立：

```
<專案資料夾>/
├── specs/
│   ├── plan.md                  ← 引擎 1–5 的所有規劃輸出（一份完整劇本）
│   ├── page_layout.yaml         ← 引擎 3 產出的每頁規格（YAML，機器可讀）
│   ├── image_policy.yaml        ← 引擎 5 產出的風格規格
│   └── image_briefs.md          ← ★給圖像工具用的整批 prompt（複製貼上即可）
├── images/                      ← ★你把生好的 PNG 放這裡
│   ├── page_01_cover.png
│   ├── page_02_hook.png
│   └── ...
└── output/                      ← Claude 最終產出
    ├── 簡報.pptx                 (image-deck / teaching-deck)
    └── 簡報.html                 (html-deck)
```

**檔名約定（重要！）：** `images/` 內的 PNG **必須**命名為 `page_NN_<role>.png`（NN 補零），`pack_pptx.py` 與 HTML/PPTX 組裝會依此排序。命名錯就順序錯。

---

## 三、工作流（三階段）

### Phase A — Claude 規劃階段（引擎 1–5）

**你對 Claude 說**（擇一觸發語）：
- 「幫我用 SOIL 做一份 [主題] 的純圖片簡報，10 頁」 → 跑 `soil-image-deck`
- 「幫我做一份 [主題] 的教學簡報，文字可編輯」 → 跑 `soil-teaching-deck`
- 「幫我做一份 [主題] 的 HTML 簡報」 → 跑 `soil-html-deck`

並補一句：**「圖像我會自己用 Codex/ChatGPT 生，請走跨工具協作 SOP」**

**Claude 會做：**
1. 問 3–5 個補充問題（教學對象、頁數、預算上限、視覺風格、色系）
2. 跑引擎 1–2，產出概念地圖與三段式脈絡，**呈現給你確認**
3. 跑引擎 3，產出 `specs/page_layout.yaml`（每頁 role / core_point / on_image_text / image_brief / layout_hint）
4. 跑引擎 4 自我檢查（六字訣）
5. 跑引擎 5，產出 `specs/image_policy.yaml`（style_tokens / size / quality / palette / upgrade_rules）
6. **最重要：產出 `specs/image_briefs.md`**（見下節格式）
7. 把整份規劃寫入 `specs/plan.md` 給你日後追溯

**`specs/image_briefs.md` 的格式（Claude 必須照這個格式）：**

```markdown
# 圖像生成 Briefs — [主題]

> **共用設定（每張都要套）：**
> - 模型：gpt-image-2
> - 尺寸：1536x1024（除非個別 prompt 另外指定）
> - 品質：low（封面與行動頁升 medium）
> - 風格：扁平向量插畫、深夜藍 #0D1B2A 背景、亮青藍 #00C6FF 主色、金黃 #FFD700 點綴
> - 避免：不要逼真照片、不要雜亂背景、不要英文字、不要亂碼

---

## page_01_cover  (medium quality)

**Prompt:**
左文右圖。圖像內容：Q版機器人老師站在發光黑板前手持畫筆，黑板上有數學公式與電路圖案。圖上文字：標題「把 ChatGPT 生圖偷進 Claude Code」、副標「gpt-image-2 × 教學工作流」、標籤「EP15」。風格：扁平向量插畫、16:9 橫版、深夜藍 #0D1B2A 背景、亮青藍 #00C6FF 主色、金黃 #FFD700 點綴。避免：不要逼真照片、不要亂碼。

**存檔名：** `images/page_01_cover.png`

---

## page_02_hook

**Prompt:**
全版插畫 + 大問句浮於上方。圖像內容：一個卡通老師站在兩條岔路前，左路 ChatGPT 訂閱方塊，右路 Claude Code 齒輪。圖上文字：標題「能偷進來嗎？」。風格：（同共用）。

**存檔名：** `images/page_02_hook.png`

---

…（依此類推到 page_NN）
```

每張的 prompt **必須是獨立完整的**——使用者複製單一段就能丟到 ChatGPT/Codex 跑，不需翻前面找風格設定。

---

### Phase B — 生圖（你動手）

**你選一條路：**

#### 路線 B1：ChatGPT 網頁版（最簡單，逐張）

1. 打開 [chatgpt.com](https://chatgpt.com)，新對話
2. 把 `specs/image_briefs.md` 用附件方式上傳，告訴 ChatGPT：
   > 這是要生成的圖像清單。請依檔案中每一個 `## page_NN_xxx` 的 Prompt，逐張用 gpt-image-2 生成圖片，尺寸照 prompt 指定（預設 1536×1024）。每張生完後，告訴我檔名我會直接右鍵下載。
3. 對每張圖：右鍵 → 另存圖片 → 用對應檔名（`page_01_cover.png`）存到專案的 `images/`

> ⚠️ ChatGPT 網頁版一次只能輸出一張圖（除非升級到 Pro 的 multi-image batching 模式）。所以是逐張對話，10 頁約需 10–15 分鐘。
> ⚠️ 中文 prompt 中的「on-image text」（要顯示在圖上的標題）大致會被遵循，但偶爾會有錯字——逐張檢查時要看圖上文字是不是對的。

#### 路線 B2：Codex CLI（批次，較快）

1. 開 terminal，啟動 Codex：
   ```bash
   codex
   ```
2. 把 `specs/image_briefs.md` 內容餵進去，下指令：
   > 請依這份 briefs 平行呼叫 gpt-image-2，每張依 prompt 指定的 size/quality 生成，存到 `images/page_NN_xxx.png`。完成後給我清單。
3. Codex 會用內建的圖像生成能力批次跑（10 張 low quality 通常 1–2 分鐘）

> ✅ 推薦走 B2 如果你已熟悉 Codex CLI——平行批次最有效率。
> ⚠️ Codex 內的 gpt-image-2 計費直接用你的 ChatGPT 訂閱額度，不額外計費 API 費用。

---

### Phase C — 回到 Claude 打包

**檔案放好後，你對 Claude 說：**
> 圖都生好放在 `images/` 了，幫我打包

**Claude 會做：**

1. **QA 階段**：用 Read/view 工具逐張開圖，檢查
   - 圖上文字是否正確（無錯字、無亂碼）
   - 風格與 `image_policy.yaml` 是否一致
   - 佈局是否符合 `layout_hint`
   - 不合格的圖會列出，請你重生那張（回到 Phase B 的單張流程）

2. **打包階段**（依 deck 類型）：

   | Deck | 打包指令 |
   |---|---|
   | `soil-image-deck` | `python pack_pptx.py --images-dir images --output output/簡報.pptx --title "標題"` |
   | `soil-teaching-deck` | Claude 寫 PptxGenJS / python-pptx 程式，把 PNG 當插畫嵌入，文字另起 textbox |
   | `soil-html-deck` | Claude 寫 HTML，把每張 PNG 用 Pillow 壓縮 + base64 內嵌 |

3. **驗收**：Claude 報告
   - 輸出檔案路徑
   - 總頁數、總成本（每張 NT$0.3 low / NT$1.3 medium）
   - 鍵盤快捷鍵（html-deck）或編輯指引（teaching-deck）

---

## 四、給 Claude 的執行守則（Skill 內部讀取用）

當使用者要求走「跨工具協作模式」時，Claude **不要**：
- ❌ 試著直接呼叫 `draw` skill（本機可能沒有）
- ❌ 試著直接呼叫 OpenAI API（本機可能沒設 OPENAI_API_KEY）
- ❌ 假裝圖已經生好

Claude **必須**：
- ✅ 跑完引擎 1–5 後，**停下來**產出 `specs/image_briefs.md` 並請使用者去生圖
- ✅ 等使用者回來說「圖好了」後，**先做 QA**（逐張檢查）才打包
- ✅ 對 image-deck，使用 `pack_pptx.py`（已經在 skill 內附）
- ✅ 嚴守檔名約定 `page_NN_<role>.png`，QA 時若檔名錯要請使用者改

---

## 五、預算與成本（gpt-image-2，2026-05-09 公告價）

| 品質 | 每張價（NT$ 約值） | 適用 |
|---|---|---|
| low | 0.3 | 99% 場景：內容頁、過場頁、非主視覺頁 |
| medium | 1.3 | 封面、結語、行動頁（單 deck 通常 1–3 張） |
| high | 3.5 | 印刷級、高解析度需求（罕見） |

**典型成本：**
- 10 頁簡報：9 low + 1 medium ≈ **NT$4**
- 15 頁簡報：13 low + 2 medium ≈ **NT$6.5**
- 20 頁簡報：17 low + 3 medium ≈ **NT$9**

> 注：透過 ChatGPT/Codex 訂閱使用 gpt-image-2 不額外計費 API 用量，但有每天的 image generation 額度上限。Plus 約每 3 小時 50 張。10 頁簡報安全。

---

## 六、常見坑與解法

| 坑 | 解法 |
|---|---|
| ChatGPT 生出來的圖**中文標題寫錯字** | 重生一次；或把 prompt 中文字加引號並重複一次強調 |
| 生圖**風格漂移**（10 張畫風不一致） | 每張 prompt 都把 style_tokens 完整寫一次（不要只寫第一張），Claude 已自動處理這點 |
| ChatGPT 拒絕生圖（policy） | 改 prompt 中的人物描述（避免名人、品牌、特定政治符號） |
| Codex CLI 批次中**部分圖失敗** | Codex 會回報哪張失敗，重跑那張即可 |
| 圖傳回 Claude 後**檔名不對** | Claude QA 時會檢查並請你改名；或你也可以用 `ls images/` 看一下 |
| `pack_pptx.py` 打包後**順序錯亂** | 檢查檔名是不是 `page_NN_*.png`（NN 補零，不能寫 `page_1`） |
| 生出來的圖**比例不對**（變正方形） | prompt 末尾加「16:9 橫版」並指定 size 1536x1024 |

---

## 七、最小範例：實際對話腳本

### 第一段（你 → Claude）

> 「幫我用 SOIL 做一份『糖尿病腎病變早期診斷』的教學簡報，10 頁，對象是內科住院醫師。文字要可編輯（teaching-deck）。圖像我會自己用 ChatGPT 網頁版生，請走跨工具協作 SOP。」

### 第二段（Claude 跑完引擎 1–5）

Claude 會回覆：
> 規劃完成，請看 `specs/plan.md` 與 `specs/page_layout.yaml`。
>
> 我已產出 `specs/image_briefs.md`，內含 10 張圖的獨立 prompt（含 1 張封面 medium、9 張內容 low）。
>
> 請：
> 1. 把 `specs/image_briefs.md` 上傳到 ChatGPT 網頁版
> 2. 依檔案中每張 prompt 逐張生成
> 3. 用對應檔名（page_01_cover.png … page_10_action.png）存到 `images/`
> 4. 完成後跟我說「圖好了」

### 第三段（你生完圖 → Claude）

> 「圖都生好放在 `images/` 了，幫我打包」

### 第四段（Claude QA + 打包）

Claude 會：
1. 逐張開圖確認文字、風格、佈局
2. 寫 PptxGenJS / python-pptx 程式組裝（teaching-deck 會把圖當插畫嵌入）
3. 輸出 `output/糖尿病腎病變早期診斷.pptx`
4. 報告：總頁數、檔案大小、編輯指引

---

## 八、版本與變更紀錄

| 日期 | 變更 |
|---|---|
| 2026-05-09 | 初版。基於 SOIL 三件套的跨工具協作流程，預設 ChatGPT/Codex 訂閱者使用 gpt-image-2 |

---

## 九、相關連結

- Claude Skill：[`soil-image-deck`](../soil-image-deck/SKILL.md) / [`soil-teaching-deck`](../soil-teaching-deck/SKILL.md) / [`soil-html-deck`](../soil-html-deck/SKILL.md)
- 打包腳本：[`pack_pptx.py`](../soil-image-deck/pack_pptx.py)
- 安裝踩坑紀錄：[`docs/2026-05-09-install-pitfalls.md`](https://github.com/ckt520728/claude-skills/blob/master/docs/2026-05-09-install-pitfalls.md)
- gpt-image-2 公告：[OpenAI Developer Community](https://community.openai.com/t/introducing-gpt-image-2-available-today-in-the-api-and-codex/1379479)
