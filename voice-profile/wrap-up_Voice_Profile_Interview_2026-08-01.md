# Voice Profile 100 題訪談：過程回顧與 Pitfalls 筆記
> 日期：2026-08-01
> 適用 vault 路徑：知識庫 / 2026 Claude code
> 標籤：#voice-profile #claude-workflow #pitfalls

---

## 一、這次做了什麼

用 100 題「Taste Interview」完整捕捉 Kwo-Ta 的寫作聲音 DNA，並：
1. 對照現有部落格文章，列出 7 條衝突清單 → 寫成 `部落格寫作指導原則_Kwo-Ta.md`
2. 整合 Q1–Q100 全部 Q&A → 寫成 `Voice_Profile_Kwo-Ta_Complete.md`

訪談跨 3 個 session 完成：
- Session 1（舊）：Q1–Q37
- Session 2（前次）：Q38–Q68
- Session 3（本次）：Q69–Q100

---

## 二、遇到的陷阱（Pitfalls）

### Pitfall 1：Context 跨 session 流失

**問題：** 100 題訪談橫跨多個 session，每次 context 壓縮都可能丟掉細節。特別是答案修正（例如 Q42 #5、Q58 #1）在壓縮後只剩摘要，原始 Q&A 細節需要靠 session summary 重建。

**根本原因：** 單一 session context window 不夠放 100 題 × 完整 Q&A。

**解決方案：**
- 在訪談進行中，主動把重要的「答案修正」立即記入 summary 的關鍵欄位
- 每次 session 開始前先讀上一 session 的 summary，確認修正有沒有被正確帶入
- 最終 Voice Profile 要在同一個 session 內一次寫完（不跨 session 分段寫）

---

### Pitfall 2：問題模板編號 vs 實際問題編號的漂移

**問題：** 訪談模板的 Q75 是關於「論點結構」（論點先行？），但本次 session 的 Q75 被設計成「引用文獻格式」。兩個編號不同步，導致部落格指導原則 MD 引用了錯誤的問題編號（Q75 (A) 論點先行）。

**根本原因：** 訪談模板 Q1-Q68 由 Part 3 template 驅動；Q69-Q100 改由我自己設計問題，編號不再和模板對應。

**教訓：**
- 如果要用模板外的問題，從模板的 Q66-Q100 整個換掉，不要沿用編號
- 或者，寫 Voice Profile 時不要引用「Q75 (X)」這種編號，只引用概念（「論點先行 = 確認」）

---

### Pitfall 3：Q42 #5 初始誤讀

**問題：** 訪談初次解讀「方法放最後 = Outputs over Process 邏輯」，但用戶修正說是「報告流暢性——技術性內容放後面，讓聽眾先看 big picture，再在 discussion 時回頭討論 methods 的應用」。

**根本原因：** 把一個表面上「過程vs結果」的選擇，直接對應到之前建立的 voice signature，沒有先問「為什麼？」

**教訓：** 遇到行為模式，先問「為什麼這樣做」，不要急著把它歸類到已知框架。

---

### Pitfall 4：Q58 #1 預設立場錯誤

**問題：** 初始假設「對學弟用比較口語化的『你』」。用戶修正：**任何書面場合（包括學弟/後輩）一律用「您」**，無例外。

**根本原因：** Claude 帶入了一般的社交禮儀預設（senior-junior 關係可以更隨意）。

**教訓：** 礼貌 register 完全由用戶個人標準決定，不能帶入「一般社會常規」的預設。

---

### Pitfall 5：blog MD 寫完後，訪談繼續更新了 Q72 的答案

**問題：** Blog 指導原則 MD 在 Q1-Q68 完成後就寫了。後來 Q72 的正式答案是 A+B（二元對比也 OK），但 blog MD 裡寫的是「只在多維度比較才用」（太嚴格）。

**根本原因：** 先寫文件、後繼續訪談，文件有過期風險。

**解決方案：**
- 訪談全部完成後再寫 blog 指導原則
- 若必須在中途寫，寫完後要回來更新（本次已修正）

---

### Pitfall 6：Q83 的重要補充差點丟失

**問題：** Q83 用戶補充了兩條非常重要的 Hard NOs（AI 視角 + 英文混雜），但這兩條是在選項 1-6 之後以文字形式補充，格式和其他答案不同，容易在 summary 壓縮時被當作備注而非核心規則。

**教訓：** 任何格式外的補充，立即用「HARD RULE 新增：」標記，確保它在 context 壓縮時被保留。

---

### Pitfall 7：最終合併時 Q36-Q68 的問題原文不完整

**問題：** Q36-Q68 的問題由 template 決定，但 template 在 Google Drive（另一個 MCP 工具）。最終寫 Voice Profile 時，template 的問題文字和答案的對應是靠記憶和 session summary 推斷，沒有完整 verbatim Q&A。

**根本原因：** 訪談問題的原始來源（Google Drive template）和答案的記錄（session 對話）分開存放。

**教訓：**
- 下次做類似訪談，每個問題問完就立即把「問題 + 答案」寫入一個持久文件
- 不要讓問題只活在對話 context 裡

---

## 三、本次訪談的流程設計評分

| 環節 | 結果 | 說明 |
|---|---|---|
| Q1-Q35：概念建立期 | ✅ 很好 | Google Drive 有完整 verbatim Q&A |
| Q36-Q68：美學偏好期 | ⚠️ 部分 | Template 問題 + session answers，但問題原文有空缺 |
| Q69-Q80：結構偏好期 | ✅ 好 | 本 session 完整記錄 |
| Q81-Q100：Hard NOs + Red Flags 期 | ✅ 好 | 本 session 完整記錄 |
| 最終 Voice Profile 合併 | ✅ 完成 | 單一 session 一次寫完，避免了跨 session 的漂移 |

---

## 四、下次做 Voice Profile 訪談的改進清單

- [ ] **設置即時記錄文件**：每個 Q 回答完就 append 到一個持久 MD 文件（不依賴 session context）
- [ ] **問題來源固定**：把 template 問題全部預先貼入記錄文件，不要讓問題只活在對話裡
- [ ] **答案修正即時標記**：修正用「[CORRECTION]」標記，不要讓它在 summary 壓縮時消失
- [ ] **訪談全部完成再寫衍生文件**：blog 指導原則、Quick Reference Card 等，在所有 Q 都回答後再寫
- [ ] **每個行為模式先問「為什麼」**：不急著歸類到已知框架

---

## 五、最終產出文件清單

| 文件 | 路徑 | 說明 |
|---|---|---|
| `Voice_Profile_Kwo-Ta_Complete.md` | `2026 Cowork/` | 完整 Q1-Q100 Voice Profile |
| `部落格寫作指導原則_Kwo-Ta.md` | `2026 Cowork/` | 7 條衝突 + 下篇文章指導原則 |
| 本文件 | `知識庫/2026 Claude code/` | 流程回顧 + Pitfalls 筆記 |

---

## 六、Voice Profile 的三個最重要發現

1. **Q100（最後鐵則）= 整個 Profile 的前提**：所有聲音訊號必須建立在「先介紹說話者身份」這個基礎上。沒有身份錨定，聲音訊號只是無主角的風格模仿。

2. **Real Voice vs C-mix 的界線**：Kwo-Ta 的 Real Voice 不是「文藝散文體」，而是「口語被書面化」。部落格的目標不是文藝，而是把 Real Voice 的骨架 × 20% 密集化修辭。B 區（文藝散文）是永久禁區。

3. **「廠商沒有提供的訊息」是不可取代的 unique value**：AI 能做文獻整理，但只有 Kwo-Ta 能補上「在你的辦公室和病房觀察到的、沒有被主流敘述說到的那一層」。每篇文章沒有這一層，就只是另一篇醫療科普。

---

*文件由 Claude 撰寫於 2026-08-01，根據 Taste Interview 100 題訪談和過程記錄產出。*
