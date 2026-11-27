# 專案收尾：用 Claude 建知識圖譜引擎（身體活動 × 神經認知老化）踩過的坑

**專案：** 2026 Knowledge graph with Claude
**日期：** 2026-11-27（單一工作階段）
**環境：** Windows 11、Git Bash + PowerShell 5.1、Python 3.11（uv，venv 放在 Drive 之外）、SQLite（放在 Google Drive G:）、Claude Code 2.1（headless `claude -p`）、Ollama（備用）
**研究主題：** The role of physical activity in mitigating neurocognitive aging: insights from electrophysiological biomarkers and neuroimaging studies
**產出：**
- 專案 `G:\我的雲端硬碟\2026 Knowledge graph with Claude`：`kgengine` 套件、CLAUDE.md、CONTEXT.md、ADR 0001–0003、handoffs.md
- 新技能 `knowledge-graph-engine/`，位於 `ckt520728/claude-skills`
- MCP 伺服器 `kg`（10 個工具），已登錄在專案 `.mcp.json`

> 本文只記錄方法與教訓。沒有金鑰；圖譜內容來自使用者本機文獻，不隨本文發布。

---

## 一句話總結

**知識圖譜的難處不在抽取，而在「數到底有幾篇證據」。** Claude Haiku 的三元組品質一開始就夠好（有方向、附 p 值引文）。真正花時間的是：重複 PDF 灌水的權重、縮寫相撞造成的錯誤合併，以及只抽前三塊時漏掉的結果段落。

## 做了什麼

| 區塊 | 內容 | 證據 |
|---|---|---|
| 攝取 | PDF／DOCX／MD／URL／貼上文字；段落式切塊（6k 字元）；切掉參考文獻；重複文件偵測 | 1,010 份文件、11,533 塊；168 份被標為重複 |
| 抽取（NER＋RE） | Pydantic 結構化輸出；本體閘門（9 種實體、18 種謂詞，皆為 `Literal` 列舉）；引文與信心值；LLM 快取 | 先導 286 塊加 r8 草稿 8 塊，0 失敗，US$1.61 |
| 實體消歧（ER） | 多數決定型別 → 正規化與縮寫 → rapidfuzz 分塊內交給 LLM 叢集 | 2,668 個名稱 → 1,957 個實體 |
| 查詢 | search／entity／neighbors／paths／類 Cypher `match`／證據矩陣／矛盾／Louvain 社群／Graph-RAG `ask` | 3,853 條主張、30 組矛盾、7 條「介入 → 生物標記 → 認知」鏈（每步 ≥ 2 篇） |
| 整合 | CLI、FastAPI（`/docs`）、MCP（stdio）、vis-network HTML、GraphML／JSON／Cypher | MCP 以真實 stdio client 測過 `list_tools` 與 `call_tool` |
| 模型 | `claude-cli`（預設，用登入帳號，免 API 金鑰）、`anthropic`、`ollama`、`openai` 相容 | `--provider` 一個參數切換 |
| 測試 | 6 項離線測試（FakeProvider） | `pytest -q` |

使用者決策：
- 自己的綜論草稿只收最新的 r8；
- 暫不跑全庫（約 US$45）；
- 加入重複文件偵測。

### 初步發現（先導圖譜，n_docs 為去重後的支持文件數）

- 有氧運動 →（增加）→ BDNF（9）；有氧訓練 →（增加）→ 海馬迴體積（6）
- 力竭運動 →（增加）→ iAPF（4）；穩態運動 → iAPF 無效果（2）
- 矛盾：PA/PE → 認知「改善」19 篇 vs「無效果」2 篇；有氧運動 → 海馬迴體積「增加」3 篇 vs「無效果」1 篇
- Graph-RAG 問「哪些 EEG 指標隨有氧運動或體能改變，且能預測認知？」，回答信心為 **low**，並明確列出缺口：圖中沒有任何一條邊把 VO2max 連到 EEG 指標。原因是只抽前三塊，P300 等結果段落沒被抽到（坑 #23）。

---

## 踩過的坑與解法

### 模型後端

1. **沒有 API 金鑰，但 Claude Code 已登入。** 改用 headless `claude -p --json-schema '<schema>' --output-format json --tools "" --strict-mcp-config --no-session-persistence`，結果在 `structured_output` 欄位。`--tools ""` 防止模型去讀檔，`--strict-mcp-config` 省下載入 MCP 的時間，`--no-session-persistence` 避免幾百個 session 塞滿 `/resume`。
2. **吞吐量比單次延遲看起來差。** 單次約 12 秒，但 6 個 worker 實際只有每分鐘約 2.5 塊；286 塊花了約 100 分鐘。大量抽取請改用 API。
3. **Pydantic 的 `$defs`／`$ref` 不是每個後端都吃。** 送出前先把 ref 展開（`inline_schema`）。
4. **本體要寫成 schema 的 `Literal` 列舉，而不是寫在提示詞裡。** 這樣 Haiku 從未產生清單外的謂詞。

### 攝取

5. **PyMuPDF 把警告印到 stdout，** CLI 的 JSON 輸出因此壞掉。加上 `fitz.TOOLS.mupdf_display_errors(False)`。
6. **先切掉參考文獻再切塊，** 否則每個被引用的篇名都會變成實體，成本也翻倍。
7. **Drive 上的 `.gdoc` 只是捷徑，沒有內容。** 要用 Google Docs 連接器讀取，再用 `kg_add_text` 匯入。
8. **同一篇論文在文獻庫裡有多個副本：** 1,010 份中有 168 份是重複。例如 `Gutmann_2015_…` 和 `Gutmann 等 - 2015 - …` 是同一篇，沒去重時會被算成「2 篇支持」。解法：首塊 8 字詞 shingle、倒排索引、Jaccard ≥ 0.5；保留「已抽取最多、最長」的那份。
9. **去重的假陽性：** 兩本 Elsevier 書的版權頁互相比對成功。解法：再要求第二塊也要相似（≥ 0.3），只有一塊的文件則要求 ≥ 0.85。
10. **自己的草稿 r1 … r8 彼此近乎重複。** 只收最新版，並明確和使用者確認這個決定。

### 實體消歧

11. **縮寫相撞造成錯誤合併：** 「Exhaustive exercise (EE)」把「Enriched environment (EE)」吞了。解法：相同縮寫不能把兩個不同的全名併在一起；單獨的縮寫（如 IAPF）只有在同型別中對應唯一全名時才併。已補回歸測試。
12. **LLM 會把同層概念併在一起：** physical activity、physical exercise、exercise 被併成一個 324 度的樞紐。這是領域定義的問題，不是 bug，已列入 CONTEXT.md 待決問題，交由使用者決定。
13. **語料一大，就不能每種型別一個提示詞**（2,668 個名稱）。先模糊分塊，每批 ≤ 120 個名稱；模型漏列的名稱保留為單獨實體。消歧呼叫要加快取。
14. **消歧前先用多數決定型別，** 否則同一名稱會因型別不同而變成兩個節點。
15. **分批 LLM 消歧結果不一致：** 「PA/PE」與「Physical Exercise (PE)」分落在不同候選塊，所以沒被併。需要第二輪、針對樞紐節點的消歧。

### Windows／Google Drive 工程

16. **venv 不要放在 Google Drive 上**（改放 `~/.venvs/kgengine`）。SQLite 放在 Drive 上，單一寫入者沒問題。
17. **cp950 主控台遇到「ä」「等」會拋 `UnicodeEncodeError`。** 設定 `PYTHONIOENCODING=utf-8`，CLI 內再 `sys.stdout.reconfigure`。Git Bash 沒有 `iconv`。
18. **mcp 2.x 把 `FastMCP` 改名為 `MCPServer`。** 鎖版本 `mcp[cli]>=1.9,<2`，並用真實的 stdio client 測試，不要只測 import。
19. **CLI 篩選的捷徑寫錯：** `doc_ids=ids or [-1]` 讓「沒有篩選」變成「什麼都不選」。要區分 `None`（不篩）與 `[]`（篩不到）。
20. **系統預設是 Python 3.9（Anaconda），** 程式用了 `X | None` 等語法。用 `uv venv --python 3.11` 建 venv。

### 評估與流程

21. **批次前先對單篇做煙霧測試，** 讀 20 條三元組；有方向、有 p 值引文才算合格。
22. **每次消歧後檢查別名最多的群集，** 錯誤合併就藏在那裡（坑 #11 一分鐘內就被抓到）。
23. **`--max-chunks 3` 會漏掉結果段落。** 下一步只對先導論文補抽其餘的塊（約 600 塊、約 US$3），或改成偵測「Results」標題的那一塊。
24. **Graph-RAG 的脈絡被樞紐邊佔滿：** 2-hop 擴到 1,002 個節點，以 n_docs 排序取前 250 條邊，具體的 EEG 邊被擠掉了。應改依種子距離與型別相關性排序。
25. **約 10% 的邊落到 RELATED_TO**（377／3,853）。比例高時補一個謂詞（例如 `MODULATES`），不要接受模糊的邊。
26. **「低信心＋明確缺口」才是對的輸出。** 在私人語料上，誠實說「圖中沒有這條邊」比聽起來很有信心更有用。

---

## 可重用的部分

- **技能：** `knowledge-graph-engine/`。SKILL.md 寫架構與建置順序，`scripts/` 放完整套件與測試，`references/pitfalls.md` 收 27 個坑，另有 ADR 與 glossary 範本。
- **換領域：** 只要改 `ontology.py`（實體型別、謂詞、同義詞、`KG_TOPIC`），並把 `PROMPT_VERSION` 加一。
- **給其他 AI 用：** MCP（Claude Code／Desktop）、REST（`/docs`），或匯出成 Cypher 給 Neo4j。

## 下一步

1. 補抽先導論文的結果段落，然後重新消歧。
2. 讓 Graph-RAG 的脈絡排序考慮種子距離與型別。
3. 用 grilling 釐清 PA／運動／體能是否要分成不同節點；決定後跑第二輪樞紐消歧。
