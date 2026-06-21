# 2026-06-22 Session Notes：虛擬大腦 E/I 平衡文獻回顧 Workflow v1.0

> 本次 session 把 PHCSSM v3.0 多代理人「單篇論文批判」管線，改造成「文獻回顧（literature review）」模式，對 `D:\Virtual brain_simulation_Neuronal_E_I_balance` 的三篇 NotebookLM 筆記（背後 11 篇原始文獻）做綜整，產出英文 APA 7th 學術回顧 + 繁中科普 Blog + 本踩坑紀錄。

---

## 一、本次完成事項

| 產出物 | 路徑（D: 專案夾 / 同步至 repo + G drive） | 說明 |
|--------|------|------|
| Workflow v1.0 | `vbm_ei_ad_review_workflow_v1.js` | 文獻回顧版，15 agents、6 schemas、reads 原始筆記做接地 |
| 學術回顧（英文 APA 7th） | `2026-06-22_VBM-EI-AD_academic_review.md` | 8 章節 + 11 篇 APA 參考文獻 + 10 個開放問題 |
| 科普 Blog（繁中） | `2026-06-22_VBM-EI-AD_blog_popular_science.md` | 一般讀者向，含三個教學比喻 |
| Session Notes | 本文件 | 設計決策與踩坑 |

**Workflow 執行統計：** 15 agents、574,443 tokens、22 tool uses、約 1,027 秒（≈17 分鐘）。Self-healing synthesis 第一次就通過（`missed_items: []`、兩個布林值皆 true）。

---

## 二、從「單篇批判」到「文獻回顧」的核心改動

PHCSSM v3.0 原本是拆解**一篇** arXiv 論文。本次目標是綜整**一個語料庫**。沿用了全部 6 個可複用 schema，但重新定義了代理人分工：

| 階段 | PHCSSM v3.0（單篇） | 本次 v1.0（文獻回顧） |
|------|--------------------|----------------------|
| Phase 1 平行分析 | A1×3 數學 + A2 文獻定位 + A3 數據 + A4 應用 + A6 掃描 | A1×3 **NMM 數學**（形式推導／失效邊界／景觀反演）+ A2 **建模與推論方法** + A3 **老化與 AD 實證** + A4 **分子到網路機制** + A6 **缺口與老化 vs AD 對比** |
| Grounding | 對照單篇 PAPER 常數 | **代理人讀內嵌 SOURCES 摘要；接地代理人改讀三份原始筆記檔**，抓摘要漂移 |
| BTL 錦標賽 | 解決代理人矛盾 | 解決**跨來源張力**：Stuart-Landau vs Jansen-Rit、Aβ-only vs dual-hit、均場有效性範圍、AEC vs 相位、老化與 AD 是否分得開 |
| Reflectors | 數學／實證／新穎性 | 方法學嚴謹度／臨床實證效度／**老化-AD 區辨與可複現性** |
| Synthesis | 同儕評審報告 | **直接產出 8 章節英文回顧 paper 草稿** + citations_used 清單 |

**關鍵設計：APA 引用與分析分離。** Workflow 只負責「科學綜整」（grounded in notes）；參考文獻的書目資料（期刊、卷期頁、DOI）由主迴圈用 WebSearch / WebFetch **獨立查證**，避免代理人從內部權重默寫出假 DOI。

---

## 三、踩坑紀錄（Pitfalls）

### 坑洞 1：摘要層的「來源膨脹（provenance inflation）」⭐⭐⭐（最重要）

**發生了什麼：** 為了省 token，分析代理人讀的是內嵌的英文 SOURCES 摘要（從三份中文筆記濃縮）。Synthesis 階段一度把「只有單一來源講過」的內容（NMM2/Clusella 的 Lorentzian ansatz、Cooray 的 Fokker-Planck），寫成「三條軌跡 T1/T2/T3 都同意」的多來源共識。

**為什麼危險：** 這正是 PHCSSM 坑洞 1 的變體——濃縮摘要會製造出原文沒有的「虛假交叉佐證」，讓一個單一來源的說法看起來像是被多方證實。

**怎麼被攔下來：** Grounding 代理人被指示**改讀三份原始筆記檔**（而非只看摘要），抓出漂移並標記；Synthesis 的 instructions 要求「丟棄假的 provenance 標籤，每個主張只歸給原始來源」。最終 paper 的 §6 明確記錄了這次修正。

**未來改進：** 文獻回顧模式下，接地代理人一定要讀原始全文/筆記，不能只看濃縮摘要。摘要可加速分析，但驗證必須回到 ground truth。

### 坑洞 2：零捏造 APA——每一筆參考都得查證

**發生了什麼：** 三篇筆記只給了檔名（`Clusella_2022_...pdf`），沒有期刊、卷期、頁碼、DOI。若直接讓模型「補完」，極易生出假 DOI/頁碼。

**做法：** 11 篇全部用 WebSearch 查證 DOI 與書目；其中 Clusella（Biol. Cybern. 117(1–2):5–19）、Zimmermann（NeuroImage: Clinical 19:240–251）另用 WebFetch 到 PMC 確認卷期頁。**無法確定的 issue 號一律省略，而非猜測**（APA 7th 允許）。

### 坑洞 3：資料夾裡有 2 篇 PDF，筆記其實沒引用

**現象：** D: 夾有 12 篇 PDF，但三篇筆記的「引用來源」只涵蓋 11 篇。`Deco_2015` 與 `Glomb_2017` 是背景資料，**筆記正文未引用**。

**處理：** 學術回顧的 in-text citation 與參考清單**只列實際被綜整的 11 篇**，不為了湊數把未引用的 PDF 塞進 references。

### 坑洞 4：一個被管線挖出來的真實科學爭點——τᵢ 的「絕對 vs 相對抑制」

**內容：** Stefanovski 2019 用「拉長抑制時間常數 τᵢ（14→50 ms）」代表 Aβ 去抑制。但拉長 τᵢ 會**增加抑制性 PSC 的曲線下面積**，等於**總抑制量上升**，與「去抑制／過度興奮」的敘事方向相反。要正確讀出 hyperexcitability，需要一個從未被明確定義的「相對局部興奮度」指標。

**意義：** 這不是流程 bug，而是 Reflector 對抗性批評挖出的**實質方法學陷阱**，已寫入 paper §5 與 §6。示範了多代理人 adversarial critique 的價值。

### 坑洞 5：G drive 路徑與存取（沿用並更新舊坑）

- 舊踩坑「G: 槽無法從 Claude Code 存取」**已過時**：本 session 能直接讀寫 `/g/我的雲端硬碟/...`。
- 但正確路徑含 **`我的雲端硬碟`**（Google Drive 根），不是最初寫的 `G:\Second Brain\...`。目標夾實為 `G:\我的雲端硬碟\Second Brain\知識庫\2026 Claude code`。

### 坑洞 6：背景 Workflow 的等待方式

**現象：** Workflow 在背景跑約 17 分鐘。`TaskOutput(block=true)` 單次上限 600 秒（10 分鐘），需分 2 段 blocking-wait 才等到完成。完成時會收到 `<task-notification>`。

**心得：** 長 workflow 不必輪詢；可一邊等一邊做不相依的工作（本次趁等待時用 WebSearch 把 11 筆 APA 參考查完）。

### 坑洞 7：數學符號以純文字呈現

Synthesis 輸出用 `tau_i`、`lambda`、`Abeta`、`chi-squared` 等純文字符號（避免編碼問題）。學術版已加註：投稿前需轉成 τᵢ、λ、Aβ 等正式符號。

---

## 四、本次回顧最重要的三個原創綜整判斷

1. **「收斂 ≠ 互證」**：Stuart-Landau 的 a、Jansen-Rit 的 τᵢ、Wong-Wang 的耦合，其實是**同一個「E/I 軸驅動 FC」先驗的不同參數化**。它們彼此吻合是「共同假設下的一致」，不是獨立驗證。BTL 與 Reflector 一致認定這點被過度宣稱為 corroboration。

2. **「尺最不準的地方剛好是病灶」**：均場模型只在臨界帶（λ≈0.70–0.85）可信，而 AD 的前側超同步／後側低同步正好落在帶外——這是整個 enterprise 最重要的認識論安全閥（Deschle 2021），卻沒有任何 AD 反演研究驗證病灶節點是否仍在帶內。

3. **「沒有正常老化基準線」**：所有研究的 HC 組只是統計對照，沒有人招募「澱粉樣蛋白陰性的健康老人」去建立老化 E/I 軌跡。因此「AD 特有失衡」可能混入未知的老化變異。Paper 的整體 verdict 因此定調為：**這是收斂的理論框架與研究路線圖，而非已成立的生物標記科學。**

---

## 五、可複用資產

- `vbm_ei_ad_review_workflow_v1.js`——文獻回顧版 6-phase 管線；改 `SOURCES` / `SOURCE_MAP` / 各 agent prompt 即可套用到其他語料庫。
- 6 個 schema 沿用 PHCSSM v3.0（`ANALYSIS_SCHEMA`、`A1_CONSENSUS_SCHEMA`、`GROUNDING_SCHEMA`、`BTL_SCHEMA`、`CRITIQUE_SCHEMA`、`REFLECTOR_CONSENSUS_SCHEMA`），另新增 `REVIEW_SYNTHESIS_SCHEMA`（title/abstract/sections[]/citations_used + self-healing 欄位）。
- **新慣例**：文獻回顧模式下，grounding agent 讀原始檔；APA 書目由主迴圈 WebSearch 獨立查證。

---

## 六、連結

- 專案夾：`D:\Virtual brain_simulation_Neuronal_E_I_balance`（12 篇 PDF + 3 篇 NotebookLM 筆記）
- 學術版：`2026-06-22_VBM-EI-AD_academic_review.md`
- 科普版：`2026-06-22_VBM-EI-AD_blog_popular_science.md`
- Workflow：`vbm_ei_ad_review_workflow_v1.js`
- 管線母本：PHCSSM v3.0（`phcssm_multi_agent_analysis_workflow_v3.js`）

---

*Session 日期：2026-06-22 | 執行環境：Claude Code (Opus 4.8) on Windows 11 | Workflow：15 agents / 574,443 tokens / ≈17 min*
