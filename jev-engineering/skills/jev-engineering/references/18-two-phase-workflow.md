# 18 — 兩階段規劃與執行

v1.2 預設採 **high 規劃、medium/low 產出**。這是使用者要求的新執行政策；原有 Jev 的 Choice、Score、Noul 與八類工具能力全部保留。不是把 Jev 改成生成模型。

## 角色與邊界

| 階段 | 執行者 | 可以做 | 交接 |
|---|---|---|---|
| Phase 1 | high planner + Jev 決策層 | 讀取必要來源、拆任務、決定策略、分配算力 | 結構化任務規格 |
| Phase 2 | medium/low executor + Jev gate | 寫作、程式修改、工具操作、測試 | 成品參照、檢查證據、實際用量 |
| 驗收 | 宿主驗證程式或 medium/low reviewer | 檢查規格與成品是否相符 | completed 或 replan |

第一階段可以回傳任務規格這類控制資料，但不能產生文章草稿、程式碼、patch 或預先寫好的答案。`objective` 是工作要求，`acceptance` 是可驗證條件，不能用來藏成品。planner 的唯讀工具限制由宿主設定；Python callback 不是 sandbox，不能阻止惡意 callback 自行寫檔。

Jev 判定 high 或不確定時，回到 planner 拆分／釐清；沒有 high executor。無法拆分時回報限制，不能降低品質標準或直接把 high 標成 medium。第一階段也不得直接執行 worker。

## 交接規格

每個 TaskSpec 含下列欄位。Python 使用 tuple；JSON 交接使用 array，由 adapter 明確轉成 tuple。

| 欄位 | 內容 |
|---|---|
| `task_id` | 唯一非空 ID |
| `objective` | 單一任務目的，含必要決策結果；不含預寫成品 |
| `inputs` | 必要檔案、段落或來源參照，可為空 |
| `outputs` | 成品參照，至少一個；文字回覆可用宿主 artifact ID |
| `acceptance` | 獨立檢查條件，至少一個 |
| `capabilities` | 原有八類能力之一或多個 |
| `depends_on` | 只引用更早的 task ID；無依賴則為空 |
| `max_output_tokens` | 該 executor 的最大輸出額度 |

同一份 plan 的 outputs 不重複。若多項操作改同一檔案，合併成同一任務；不要用不同路徑拼寫逃過衝突檢查。宿主 sandbox 仍須限制實際檔案路徑。

`Allocation` 另外保存實際 `Model`（含 effort）、資料類型與 Jev 信心。`ExecutionPlan.status` 為 `ready`、`replan` 或 `ask`。只有 ready 才能交給 executor。

## Python 執行流程

套件使用 Python 3.9+ stdlib，模型連線由宿主 adapter 提供，避免綁定單一 agent SDK。

```python
from jev import plan_phase, execute_phase

plan = plan_phase(
    request, planner_adapter,
    registry=registry, data_class="internal", provider="jev",
)
report = execute_phase(
    plan, executor_adapter,
    registry=registry, provider="jev",
    tool_runner=host_tool_runner,
    verifier=verify_artifacts,
    approve=host_human_approval,
    cwd=project_directory,
)
```

這段是宿主接線範式，名稱由你的應用提供。完整可直接執行的離線範例：

```powershell
python -X utf8 skills/jev-engineering/assets/examples/two_phase.py
```

範例在 temporary directory 寫入／讀回成品後清理，使用明確標示的 SYNTHETIC stub 模型，沒有真實 API 費用或省費測量。

宿主需要實作四個介面：

1. `planner_adapter(PlannerRequest) -> PlannerResult`：用 `request.model.callable_id` 與 `model.effort` 呼叫 high，套用 `instructions` 與 `max_output_tokens`，停用執行工具；解析 JSON 為 TaskSpec。只回報 API 的實際 model key 與 token 用量。
2. `executor_adapter(WorkerRequest, ExecutionContext) -> WorkerResult`：用指定 medium/low 模型與 `task.max_output_tokens`。每個工具呼叫都經 `context.call(tool, arguments)`，不可直接呼叫 `tool_runner`。不能繼承 planner 的完整 context，也不能自動 fallback 到 high。
3. `tool_runner(tool, arguments)`：在宿主 sandbox 內執行通過 gate 的具體工具。它必須限制檔案／命令範圍；Jev 分類不等於作業系統隔離。
4. `verifier(request, result) -> bool`：由主控注入獨立驗收，檢查實際成品／測試結果。不可直接回傳 executor 自報的成功欄位。文字 artifact 也須從宿主儲存區讀回驗證。

可選的 `approve(task_id, tool, arguments, verdict) -> bool` 只能代表人工對該實際動作的授權（包括已取得且仍適用的授權）。沒有授權時回傳 false；不可設成自動 true 來消除 ask。deny 不可被覆寫。

Jev 一次分類各任務的 tier 與資料類型；已知的 internal/customer_data 不會被 Jev 降成 public。候選同時受平台可用性、資料政策及已驗證 API ID 限制。無可用模型回 ask，不放寬篩選。未定價時沿用平台偏好，不能宣稱成本最小。

Phase 2 執行前重新檢查所有模型配置。每個 worker 只收到自己的 TaskSpec 與直接依賴的 artifact 參照。一次只嘗試一次；失敗停止後續任務，不自動重新規劃／重試。宿主可將 `report.completed` 保留，再提供錯誤摘要啟動新 plan，避免重做已完成動作。

## 預算與信心

`workflow.Limits` 的預設值是可調整的政策，不是實證最佳值：最多 16 個任務、planner 輸出 4096 tokens、每個 worker 上限 4096、總輸出上限 32768、每份 task 12000 字元、每個 worker 最多 12 次工具呼叫。TaskSpec 預設輸出額度為 2048。

這些上限在模型呼叫前檢查，並驗證回傳的實際用量。API 的生成上限須由 adapter 設定；事後偵測超額不能撤銷已產生的費用／寫入。total output cap 不等於所有輸入加輸出的費用上限，字元數也不等於 tokenizer token 數。

`ROUTE_CONFIDENCE = 0.85` 是未經本地流量校準的起始門檻；等於門檻才通過。低於門檻、high 或 other 都 replan。資料類型不確定、含憑證、無模型或服務失敗回 ask。保留 `toolgate.DEFAULT_THRESHOLDS`，不讓路由信心取代實際工具 gate。

八類能力：`read`、`local_write`、`destructive`、`network_egress`、`process_spawn`、`credential_access`、`spend`、`other`。第一階段只盤點未來能力；第二階段對實際參數逐次 gate。workflow 停用跨參數的工具 verdict cache，保留 hard blocks 優先與外部行為人工決定。

## Claude Code plugin

根目錄 `agents/` 提供三個角色：

| 名稱 | 模型 alias | 工具 |
|---|---|---|
| `jev-planner` | `opus` | Read、Glob、Grep |
| `jev-executor-medium` | `sonnet` | Read、Glob、Grep、Write、Edit、Bash |
| `jev-executor-low` | `haiku` | Read、Glob、Grep、Write、Edit、Bash |

使用方式：要求主控「用 jev-engineering 處理此任務，先用 jev-planner 只規劃，再把交接任務分派給 medium／low executor」。skill 的主控負責連接 Jev、預算、交接與驗收；角色檔本身不會自動執行 Python。讀取副本／安裝後須啟動新 session，使宿主載入新角色。

alias 是 Claude Code 的宿主設定，不是 Python registry 的 API ID。宿主可能覆寫模型，執行前必須確認實際模型；不能靜默接受 high executor。模型設定與 plugin agents 格式參考 [Claude Code subagents](https://code.claude.com/docs/en/sub-agents) 與 [plugin manifest](https://code.claude.com/docs/en/plugins-reference)，查核日期 2026-10-02。

現有 `.claude/settings.json` hooks 保持停用，plugin 不會自行修改全域權限。**角色提示詞與原生權限不能當作已安裝 Jev middleware 的證據。** 要強制逐次 Jev gate，宿主須接上 `ExecutionContext.call()`，或另行設定等價 middleware。原有 Bash hook 是舊的四風險分類，不能宣稱它已覆蓋完整八類 workflow。先用離線範例驗證契約，再以實際宿主資料驗證路由。

Codex／其他 host 可使用同一份 skill 與 adapter；若 host 沒有 model selection API，回報待交接，不由當前 high agent 代做。

## 用量與證據邊界

執行報告包含完成率、已回報的 input/output tokens 與 `usage_complete`。若 callback 在回報用量前失敗，或呼叫尚未提供 usage 的舊 ToolGate，`usage_complete=false`；這時用量只是下限。驗收器若使用模型，也由宿主把用量補入總帳。

節省昂貴模型 tokens 不保證總 tokens 減少。比較真實工作負載時須加總 planner、Jev、executor、gate、驗收、重試及重新規劃；同表列完成率與每個完成任務成本。沒有定價或用量時寫未量測，不顯示虛構節省百分比。

本次行為驗證涵蓋階段隔離、實際寫入與獨立讀回、八類 gate、信心邊界、資料政策、缺模型、依賴、預算、模型漂移及失敗停止。stub 測試不證明真實模型會遵守語意規格，也不證明實際價格、模型品質或節省率。

## v1.3 寬度執行：雙大腦 Swarm 扇出

來源：一份 NotebookLM 筆記，整理 X 上的「雙大腦／兩階段」代理架構貼文（推理層 Astra／Claude 決定**建什麼**，Kimi K3 集群決定**如何大規模建造**，兩者之間的 **Handoff Wire** 是系統最關鍵的單一連線）。這與 v1.2 的兩階段政策同構；v1.3 補上的是**寬度**：同一份計畫一次扇出許多 worker。筆記中的供應商數字（300 個並行 agent、1M context、2.8T 參數、100 家 EV 公司單次爆發完成）來自貼文本身，**未經驗證**，不得當成配額或效能承諾。

### 何時用 swarm，何時用依序執行

| 情況 | 用 |
|---|---|
| 任務多半互相獨立、數量大（同模板 × N） | `execute_swarm()` |
| 任務是一條依賴鏈，或少於約 4 份 | `execute_phase()`（v1.2，依序） |
| 宿主無法同時派發多個 worker | `execute_phase()`；不要模擬並行後宣稱省時 |

兩者每份任務都走同一個 `run_task()`：指定模型、逐次工具 gate、一次嘗試、獨立驗收。差別只在排程。

### 1. Handoff Wire：task manifest

Phase 1 不把自然語言交給集群，而是寫出一份清單：

```python
from jev import write_manifest, load_manifest, SwarmPolicy

digest = write_manifest(plan, "task_manifest.json", "EV_Market_Analysis",
                        SwarmPolicy(concurrency=8, requests_per_minute=60))
plan2, policy = load_manifest("task_manifest.json", registry)   # 執行端
```

清單（schema `jev.task_manifest/1`）含 `project`、`planner_model`、`policy`、`limits`、planner 用量，以及每份任務的 TaskSpec 欄位加上 `model`、`tier`、`data_class`、`confidence`；最後是對其餘內容的 `sha256`。

`load_manifest()` 會：驗雜湊（Phase 1 之後被改過就停）、把 array 明確轉回 tuple、確認每個 `model` 在**執行端自己的** registry 中存在且 tier 相符、重新跑任務驗證（ID、依賴、成品不重複、能力、預算、憑證樣式）。任何欄位不符都是 `WorkflowStop`，不會漏成 `KeyError`。

雜湊是**竄改偵測**，不是簽章：能改清單的人也能重算雜湊。它防的是交接途中被人或工具「順手修一下」，而不是惡意攻擊者。

筆記中的範例欄位 `action`／`target`／`required_tools`／`output_format` 對應到這裡的 `objective`／`inputs`／`capabilities`／`acceptance`；`concurrency_limit` 對應 `SwarmPolicy.concurrency`。

### 2. 扇出前審查：先擋住會被放大的歧義

筆記點出的主要風險是**扇出錯誤放大**：Phase 1 規格若有歧義，N 個 worker 會同步複製同一個錯誤。`preflight()` 先把任務依**模板**分組（能力與驗收條件完全相同者），對每個多於一份的組問 Jev 一題 `Noul`：

> 每一份規格單獨交給一個不知道其他任務的 worker，就足以不需追問地產出格式一致、能依驗收條件逐條判定的成品。

所有組在同一次 `decide()` 內問完；單一任務的組不問。機率低於 `SPEC_CLEAR_THRESHOLD = 0.85` 的組 → `replan`，**一份 worker 都不派**。這個門檻是 `Noul` 機率，和 `ROUTE_CONFIDENCE` 是不同量尺，未經本地流量校準。服務失敗或用量回報異常 → `ask`。

### 3. Canary 先行

`SwarmPolicy.canary_min_group`（預設 3）以上的模板組，第一份任務是 canary。同組其餘任務要等 canary **通過獨立驗收**才放行。canary 失敗 → 同組全部保留（`held`），依賴它的任務列為 `blocked`，回 `replan`。代價：大組多一段等待；換到的是「規格錯了只燒一份 worker，不是 N 份」。

`preflight()` 問的是規格**看起來**清不清楚；canary 量的是實際執行後**有沒有**做對。兩者都要。

### 4. 有界並行、失敗隔離與斷路器

- 依賴滿足即派發，最多 `concurrency` 個同時執行（程式硬上限 `MAX_CONCURRENCY = 512`）。實際值由供應商配額決定，不是由貼文的數字決定。
- 所有 worker 共用一個速率限制器（`requests_per_minute`，沿用 `bulk.py` 的 `_RateLimiter`）。
- 一份任務失敗只阻擋**依賴它的**任務；其他獨立任務照常完成。已完成成品保留在報告中，重新規劃時不要重做。
- 失敗數 ≥ `breaker_min_failures` 且失敗比例 ≥ `breaker_failure_ratio`（預設 2 份、25%）→ 斷路：不再派新任務，等執行中的結束，回 `replan`。高失敗率最可能的原因是規格，不是運氣。
- 任一任務因工具 gate 回 `ask`（需要人）→ 立即停止派發新任務，整份回 `ask`。
- 不重試、不 fallback 到 high，與 v1.2 相同。

`SwarmReport` 回報 `completed`、`failed`（task → 精簡原因）、`blocked`、`held`、`canaries`、`waves`（依賴分層）、`peak_concurrency`、`breaker_tripped`，以及含 planner、扇出前審查與所有 worker 的用量；`completion_rate` 與用量一起報告。

**Thread safety。** `executor`、`verifier`、`approve` 會在 worker thread 中被呼叫。宿主須確保它們可並行呼叫；尤其 `approve` 若彈出人工確認，要能處理多個同時到達的請求，或將並行數設為 1。

### 5. 宿主接線

**Claude Code。** 主控讀清單後，對同一層（`waves()`）中已放行的任務，**在同一則訊息中**並行呼叫多個 `jev-executor-low`／`jev-executor-medium` subagent，每個只帶自己的 TaskSpec 與直接依賴的成品參照。canary 規則與斷路器由主控照本節執行；角色檔不會自動做這些事。

**外部集群（例如 Kimi K3）。** 筆記提出兩種橋接：

| 模式 | 做法 | 在本 skill 的位置 |
|---|---|---|
| MCP | 將集群包成一個 MCP 工具（如 `kimi_swarm_dispatch`），Claude 規劃完成後呼叫 | 該工具呼叫屬於 `network_egress` + `spend`，一律經工具 gate 與人工核准 |
| Subprocess／CLI | Claude 寫出 `task_manifest.json`，本地腳本讀取後呼叫供應商 API | 腳本以 `load_manifest()` 讀清單，並以 `execute_swarm()` 的 executor adapter 呼叫 API |

無論哪一種，外部集群的回傳仍須由**本地**驗收器讀回成品驗證；不能接受集群自報「100 份完成」。

**Kimi K3 的設定。** `models.json` 已登錄 `kimi-k3`（平台 `moonshot`，tier medium），但 `api_id` 為 `null`、`api_id_verified=false`，因此永遠不會被派發。啟用前：

1. 從 Moonshot 官方文件確認實際 model ID 與 base URL。筆記中的 `moonshot-v1-300-swarm`、`kimi-k3` 與已被移除的連結都未經確認，不要照抄。
2. 需要 Moonshot 自己的 API key。Open Code Go／OpenClaw 類工具的訂閱只涵蓋該工具本身，不含 Moonshot 的 API 用量（此點依筆記，與一般網關計費方式一致，仍請以官方說明為準）。key 放環境變數 `MOONSHOT_API_KEY`；不要寫進會被提交的 `openclaw.json`／`config.json`。
3. 填入 `api_id`、設 `api_id_verified=true`，若要比較成本再填價格與 `price_source`。
4. 檢視 Moonshot 的資料使用條款後，再決定是否把 `moonshot.data_classes_allowed` 從 `["public"]` 放寬。
5. 用真實流量量測：完成率、每完成任務成本、wall-clock，與 v1.2 依序執行並列。

### 證據邊界

`eval/test_swarm.py` 以 stub 驗證：清單往返與竄改偵測、模板分組與依賴分層、審查門檻邊界、canary 先行與失敗保留、並行上限、失敗隔離、斷路、工具 gate 停止派發、用量計入預算。關鍵規則經 mutation testing 確認：故意破壞後測試會失敗。stub 不證明任何供應商真的支援上述並行數，也不證明 swarm 比依序執行便宜：並行縮短 wall-clock，但 token 用量不會因此減少，canary 與審查還會增加少量用量。
