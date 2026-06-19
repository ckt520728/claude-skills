# 2026-06-19 Session Notes: PHCSSM Multi-Agent Workflow v3.0

> 本次 session 主要工作：以 Robin MAS 架構原則優化 PHCSSM 論文分析 Workflow，從 v2.5 升級至 v3.0，並實際執行產生學術論文分析報告與科普 Blog。

---

## 本次 Session 完成事項

| 產出物 | 路徑 | 說明 |
|--------|------|------|
| Workflow v3.0 | `phcssm_multi_agent_analysis_workflow_v3.js` | Robin MAS 優化版，15 個 agents |
| 學術論文分析 | `phcssm_academic_analysis.md` | 英文同儕評審格式，8 章節 |
| 科普 Blog | `phcssm_blog_popular_science.md` | 繁體中文，一般讀者適合 |
| Session Notes | 本文件 | 坑洞記錄與設計決策 |

**執行統計（Workflow v3.0）：** 15 agents、971 秒、523,804 tokens、120 tool uses

---

## 從 v2.5 → v3.0 的核心改動

源自 Robin MAS（Ghareeb et al., 2026, *Nature*）的五個 Core Concepts：

### [R1] Structured JSON Schemas — 所有 Agent 強制輸出結構化 JSON

**v2.5 問題：** 每個 Agent 輸出純文字，後續 Agent 要自己解析，容易出錯（BixBench 多步驟 15.3% 失敗率的教訓）。

**v3.0 改動：** 為每個 Agent 定義獨立的 JSON Schema（ANALYSIS_SCHEMA、GROUNDING_SCHEMA、BTL_SCHEMA、CRITIQUE_SCHEMA 等），每個 `key_finding` 必須附上 `paper_evidence` 欄位（直接引用論文原文），下游 Agent 收到的是 `JSON.stringify()` 的結構化資料，不是自由格式文字。

---

### [R2] A1 Consensus Trajectories — 數學分析代理人跑 3 條軌跡

**v2.5 問題：** Agent 1（數學分析）只跑一次，數學類型分析幻覺風險最高。

**v3.0 改動：**
- T1（Formal Completeness）：專注推導完整性
- T2（Failure Mode Analysis）：專找可能失效的地方
- T3（Topology & Convergence）：專注收斂性與拓撲

三條軌跡各自獨立，再由 A1 Consensus Merger 取「≥2/3 同意」的 finding 才列入。

**實際效果：** 三條軌跡都獨立發現「STP bilinear term (u·R·S) 不是真正的 affine recurrence」，強化了這個關鍵發現。T3 獨家發現 Jacobi vs Gauss-Seidel 訓練/推斷不一致問題（Section 5 承認但未量化）。

---

### [R3] Grounding Check Gate — 所有 Claim 必須對應論文原文

**v2.5 問題：** 無驗證機制，Agent 可能從模型內部知識（而非論文）生成 claim。

**v3.0 改動：** 新增 Agent G，它拿到 PAPER 完整文字 + 所有前面 Agent 的輸出，逐一檢查：
- 有論文原文佐證 → `grounded_claims`
- 超出論文範圍 → `hallucination_flags`
- 論文有寫但沒有 Agent 提到 → `coverage_gaps`

**實際效果：** 接地驗證代理人發現 PAPER 常數本身有幾個數字是錯的（下方坑洞 1），並輸出到 hallucination_flags，防止這些錯誤進入 BTL 和 Synthesis。

---

### [R4] BTL Tournament Gate — 取代單一 Monitor Agent

**v2.5 問題：** Agent 7（Monitor）做「絕對評分」，有位置偏差，且無法處理代理人之間的矛盾。

**v3.0 改動：** BTL Tournament Agent 列出所有跨 Agent 矛盾，每一個矛盾做兩兩比對，用「哪個 claim 有更直接的論文佐證」作為勝負標準。輸出 `resolved_consensus`（明確的共識立場）和 `synthesis_instructions`（給 Agent 5 的明確指令）。

**實際效果：** 解決了 A2 和 A6 對「novelty claim 是否成立」的分歧，BTL 裁定「incremental but non-obvious，不完全是 vanity conjunction」。

---

### [R5] Consensus Adversarial Critique — 3 條反駁軌跡取共識

**v2.5 問題：** 單一 Reflector (A8) 的盲點沒有校正機制。

**v3.0 改動：**
- R1（Math Rigor lens）：專攻數學嚴謹度
- R2（Empirical Validity lens）：專攻實驗效度
- R3（Novelty & Reproducibility lens）：專攻新穎性與可複現性

再由 Reflector Consensus Merger 取「≥2/3 Reflector 同意」的缺陷列入最終報告（單一 Reflector 的發現標記為「uncertain」）。

**實際效果：** 三個 Reflector 都獨立發現：
1. MTL 的真實複雜度是 O(M log T) 而非 O(log T)（致命缺陷）
2. MTL 無收斂性證明（致命缺陷）
3. 消融實驗自相矛盾（致命缺陷）
4. 測試資料集選擇存在循環驗證問題（致命缺陷）

---

### 額外：Self-Healing Synthesis Loop

**設計理由（Robin 的 ReAct error-feedback 模式）：** Agent 5 Synthesis 可能漏掉 BTL 的某些 synthesis_instructions 或 consensus weaknesses。

**實作：** Synthesis Schema 加入 `all_btl_instructions_addressed`（布林值）和 `all_consensus_weaknesses_addressed`（布林值）兩個欄位，以及 `missed_items` 陣列。如果任一為 false，自動 retry 一次並傳入 missed_items 清單。

**實際效果：** 本次執行中 Agent 5 第一次就通過，`missed_items: []`，不需要 retry。

---

## 坑洞記錄（Pitfalls）

### 坑洞 1：PAPER 常數的數字來自摘要而非論文內文 ⭐⭐⭐（最重要）

**發生了什麼：** Workflow 裡的 `const PAPER` 包含了幾個數字是從論文摘要/簡介版本抄來的，但實際上論文內文的表格數字不同：

| 欄位 | PAPER 常數的值 | 論文實際值 | 問題 |
|------|----------------|-----------|------|
| EigenWorms 準確率 | 83.9% | 85.0% | 83.9% 是 S5 baseline，不是 PHCSSM |
| 參數數量範圍 | 1,748–9,485 | 1,312–4,891 | 摘要與表格兩者矛盾（論文本身的 bug） |
| 訓練時間 | 27–129 s | 18–141 s | 論文版本差異 |
| GPU 記憶體 | 10–48 MB | 論文根本沒寫 | 子虛烏有的數字 |

**影響：** Grounding Check Gate（R3）在接地驗證階段攔截了這些錯誤，標記為 `hallucination_flags`，後續 Agent 使用的是修正後的數字。學術論文和科普 Blog 均使用了正確數字。

**根本原因：** PAPER 常數是從論文 abstract/摘要版本手動整理的，而不是直接從 arXiv PDF 提取全文。

**未來改進：** 理想做法是在 Phase 0 加一個「Paper Ingestion Agent」，直接透過 `agent()` + WebFetch 取得 arXiv PDF，把完整論文文字存入 PAPER 常數，而不是手動摘要。

---

### 坑洞 2：學術職稱確認

**發生了什麼：** 科普 Blog 第一稿把 Po-Han Chiang 稱為「研究生」，後來被使用者更正為「教授」。

**根本原因：** 論文 arXiv 版本的機構欄位寫的是 NYCU（陽明交通大學），但沒有明確的職位資訊，靠推斷容易出錯。

**教訓：** 對人名職稱的 claim，應在 Grounding Check 中設為強制驗證項目，無法從論文文字確認的一律留空或標注「職稱待確認」。

---

### 坑洞 3：Self-Healing Loop 的初始版本用字串比對

**發生了什麼：** 最初設計的 self-healing check 用 `string.includes()` 比對「synthesis 是否提到 BTL 指令中的關鍵詞」，但這很容易有 false positive（提到了某個詞但沒有實際處理）和 false negative（用不同措辭表達同樣概念）。

**最終設計：** 改成讓 Synthesis Agent 自己回報兩個布林值（`all_btl_instructions_addressed` / `all_consensus_weaknesses_addressed`）和一個 `missed_items` 陣列。這把驗證責任交給最了解自己輸出的代理人本身，更可靠。

---

### 坑洞 4：Agent 費用與模型選擇的平衡

**現象：** v3.0 把 A1 分成三條 Opus 軌跡，R1 和 R2 也用 Opus，整體費用比 v2.5 高許多。

**評估：** 數學分析（A1）確實需要 Opus 品質。但 Reflector R3（新穎性角度）和 Consensus Merger 可以降到 Sonnet，效果沒有明顯差異。

**建議的 v3.1 優化：**
- R1（Math）：Opus ✓
- R2（Empirical）：Sonnet（從 Opus 降）
- R3（Novelty）：Sonnet ✓（已是 Sonnet）
- A4（Applications）：Sonnet（從 Opus 降，應用分析比數學分析要求低）

預計可節省 20-30% 費用而不損失關鍵品質。

---

### 坑洞 5：PAPER 常數的長度在大型論文會超出 token 限制

**現象：** 本次 PAPER 常數是手動摘要，約 700 words。若未來要分析較長的論文（如 30 頁的 NeurIPS paper），完整論文文字可能超過 token 窗口。

**建議：** 對長論文，可將 PAPER 常數拆分為幾個部分（Abstract + Methods + Results + Discussion），並讓各 Agent 只接收與其任務相關的部分。或在 Phase 0 加入論文分段索引器。

---

## PHCSSM 分析的三個最重要原創發現

1. **O(M log T) 取代 O(log T)**：多傳輸迴圈（MTL）的真實平行深度是 O(M log T)，M 無上限證明且從未在實驗中報告。這個發現只有在三條數學軌跡都獨立抵達同一結論後，才被列為「高信度致命缺陷」。

2. **消融實驗自相矛盾**：移除 STP 讓 EigenWorms 準確率提升 +2.8%，移除 STDP 讓 EthanolConcentration 提升 +3.1%，但 mean drop 遠低於 seed 標準差（0.23pp vs 4–11pp）。這不只是「某些約束沒有幫助」，更是「效果完全在統計噪音範圍內，無法區分有無貢獻」。

3. **Grounding Gate 抓到 PAPER 常數本身的錯誤**：接地驗證代理人發現「83.9% EigenWorms」實際上是對比 baseline（S5）的數字，PHCSSM 本身是 85.0%。這說明即使是論文作者提供的摘要，也可能有誤——R3 的「接地驗證」機制在這裡發揮了關鍵作用。

---

## 架構設計決策記錄

### 為什麼選 BTL 而不是 LLM Judge 投票？

Robin 系統的實驗顯示，pairwise comparison 在評估多候選方案時比「直接給 1–10 分」更穩定，且位置偏差更少。在 v3.0 的 BTL Tournament，每對矛盾都是一場「誰有更直接的論文佐證」的比賽，裁決依據是可追溯的，而不是 LLM 主觀印象。

### 為什麼 A1 用 3 條而不是 8 條？

Robin 的 Finch 代理人在分析生資數據時用 8 條軌跡，因為數據分析有高度的隨機性（程式碼每次執行結果不同）。數學分析的隨機性主要來自「從哪個角度切入」，3 條 + 明確的不同角度方向（形式完整性 / 失效模式 / 收斂性）可以覆蓋主要盲點，再多軌跡的邊際效益有限。

### 為什麼 Self-Healing 只 Retry 一次？

Robin 系統的 ReAct 迴圈建議設最大迭代次數上限，防止無限循環。一次 Retry 足夠處理「漏掉某個 synthesis_instruction」的情況；如果兩次都失敗，通常是 instructions 本身有矛盾，需要人工判斷。

---

## 可複用的 Schema 設計

下列 Schema 設計可直接用於其他論文分析 Workflow，只需調整 `description` 欄位：

- `ANALYSIS_SCHEMA`：標準論文分析輸出（key_findings with paper_evidence, strengths, weaknesses, unverified_claims）
- `GROUNDING_SCHEMA`：接地驗證輸出（grounded_claims, hallucination_flags, coverage_gaps）
- `BTL_SCHEMA`：BTL 錦標賽輸出（contradictions with winner/rationale, resolved_consensus, synthesis_instructions）
- `CRITIQUE_SCHEMA`：對抗性批評輸出（critical_weaknesses with severity, parameter_comparison_validity, reviewer_rejection_reasons）
- `REFLECTOR_CONSENSUS_SCHEMA`：多軌跡批評共識（consensus_weaknesses with source_reflectors, single_reflector_findings）
- `SYNTHESIS_SCHEMA`：最終報告（含 self-healing 驗證欄位 all_btl_instructions_addressed, all_consensus_weaknesses_addressed, missed_items）

---

## 連結

- **arXiv 論文：** https://arxiv.org/abs/2604.01295
- **Robin MAS 原始論文：** Ghareeb, A. E. et al. (2026). A multi-agent system for automating scientific discovery. *Nature*.
- **Workflow v2.5（原版）：** `phcssm_multi_agent_analysis_workflow.js`
- **Workflow v3.0（本次）：** `phcssm_multi_agent_analysis_workflow_v3.js`
- **Robin 架構解構筆記：** `notebooklm-note-多代理人科學發現系統-robin架構解構-2026-06-18.md`

---

*Session 日期：2026-06-19 | 執行環境：Claude Code (claude-sonnet-4-6) on Windows 11*
