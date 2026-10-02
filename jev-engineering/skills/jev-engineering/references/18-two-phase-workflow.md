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
