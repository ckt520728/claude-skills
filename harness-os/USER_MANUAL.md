# Harness OS — User Manual

使用手冊。安裝、啟動、六種任務的實戰用法，以及什麼時候**不要**用它。

---

## 1. 這個東西解決什麼問題

不是「讓 AI 更聰明」。是讓長時間、跨 session 的工作**不要在物理層崩掉**：

| 你遇過的狀況 | 實際發生了什麼 | Harness OS 的對策 |
|---|---|---|
| 「它忘記前面講好的東西」 | 狀態只活在 context window | playbook + trace 落盤 |
| 「它一直重跑同一個失敗指令」 | 沒有前三步的記憶 | `loopcheck` 迴圈斷路器 |
| 「讀到第 20 篇 PDF 就開始胡說」 | 原始材料留在 prompt 裡 | 每篇 fork 一個 job，只留摘要 |
| 「它說做完了，檔案是空的」 | 口頭宣稱完成，沒有驗證 | contract + `assert` + `publish` 閘門 |
| 「修好 A 卻弄壞 B」 | 沒有回歸測試 | held-in / held-out `gate` |
| 「一直在修錯的東西」 | 修症狀不修機制 | 失敗簽名 + `mine` |
| 「跑到一半忘了某條硬規則」 | 約束被上下文壓縮掉了 | 不變約束 `constraint` |
| 「為了過關把答案寫死」 | 驗證器是靜態的，被鑽了 | `challenge:` 動態挑戰 |

**核心規則一句話**：交付物必須通過事先寫好的契約，才准進 `out/`。

---

## 2. 安裝

```bash
git clone https://github.com/ckt520728/claude-skills.git
cd claude-skills/harness-os

# 兩個 gate，都必須 PASS
python scripts/harness_kernel.py selftest          # 42 checks
python scripts/verifiers/test_verifiers.py         # 72 checks
```

安裝 skills（擇一）：

```bash
# macOS / Linux
cp -r skills/* ~/.claude/skills/

# Windows PowerShell
Copy-Item -Recurse skills\* "$env:USERPROFILE\.claude\skills\"
```

需求：Python 3.8+。**沒有任何第三方套件**。Windows / macOS / Linux 都可跑。

驗證安裝：在 Claude Code 裡輸入 `/harness-os`。看到 orchestrator skill 載入就成功了。

---

## 3. 啟動

### 三種啟動方式

**A. 直接叫 skill**（最常用）

```
/harness-os 幫我用 research-proposal profile 起草國科會計畫書
```

**B. 讓它自己觸發**
描述裡的觸發詞會讓 Claude 自動載入：「長任務」「跑 harness」「它說做完但沒有」
「this keeps losing track」。

**C. 只用 kernel，不用 skill**
你也可以純粹在終端機用它當驗證工具，不牽涉 skill：

```bash
export HARNESS_WORKSPACE="/path/to/project"
KP="/path/to/harness-os/scripts/harness_kernel.py"
python "$KP" boot
python "$KP" contract --name report --target out/report.md \
  --checks "exists,min_words:2000,no_placeholder"
python "$KP" publish --contract report
```

> **路徑有空格的注意**：用 `KP="路徑"` 然後 `python "$KP"`。
> 不要寫成 `K="python 路徑"` 再用裸的 `$K` — 會在空格處斷開。
> 本文以下用 `$K` 代表 `python "$KP"`。

### 最小可用流程（80% 的情況只需要這樣）

```bash
$K boot --profile academic-writing
$K goal --text "投稿用 draft" --done "draft 通過所有 contract"

$K contract --name draft --target draft/paper.md --split held_in \
  --checks "exists,min_words:3000,sections:Abstract|Methods|Results,no_placeholder"
$K guard init

# ... 工作 ...

$K assertall --round 1
$K publish --contract draft
```

**先只用這五個指令。** fork / mine / evolve 等真的需要再加。

---

## 4. 契約怎麼寫（最重要的一節）

契約就是「完成」的定義，**必須在動工前寫好**。事後補的契約會被寫成剛好符合已產出的東西，那就失去意義了。

### 可用的檢查

| 檢查 | 用途 | 例 |
|---|---|---|
| `exists` | 檔案在不在 | `exists` |
| `not_empty` / `min_bytes:N` | 不是空檔 | `min_bytes:2000` |
| `min_words:N` | 篇幅 | `min_words:4000` |
| `valid_json` | JSON 語法 | `valid_json` |
| `json_keys:a;b;c` | 必要欄位 | `json_keys:total;equipment` |
| `sections:A\|B\|C` | 必要章節（標題內含即可） | `sections:研究方法\|經費預算` |
| `regex_present:PAT` | 必須出現 | `regex_present:performance\.now` |
| `regex_absent:PAT` | 不准出現 | `regex_absent:\[citation needed\]` |
| `no_placeholder` | TODO / FIXME / lorem / 截斷 | `no_placeholder` |
| `python_compiles` | Python 語法 | `python_compiles` |
| `cmd:<指令>` | **任何外部驗證器**，exit 0 才算過 | `cmd:pytest -q` |
| `challenge:<指令>` | **抗作弊驗證**：每次跑注入一個新的隨機 nonce（`$HARNESS_CHALLENGE`），驗證器要 exit 0 **且** 回吐這個 nonce 才算過 | `challenge:python $V/check_challenge_response.py -- python solver.py` |

小語法：`--checks` 用逗號分隔；**某個檢查的參數裡需要逗號時改用 `;`**，kernel 會轉回來。

### 三條鐵則

1. **`no_placeholder` 每個文字或程式交付物都要加。** 假完成最常見的型態就是佔位符和截斷。
2. **至少一個 `--split held_out`。** 那是修復迴圈看不到的檢查。沒有它，`gate` 無法偵測過擬合，而且每輪都會警告你。
3. **有真實測試就用 `cmd:`；能重算的確定性性質就用 `challenge:`。** 結構檢查只能確認形狀；`cmd:pytest`、`cmd:tsc --noEmit` 確認的是行為。`challenge:` 再多一層：每輪換一個新 nonce，寫死或背下來的答案會因為對不上沒見過的挑戰而失敗——這是修復迴圈最便宜的作弊路徑，用它堵住。它的限制：只證明驗證器對一個不可重複的輸入即時跑過，不證明整體正確；而且只會回吐 `$HARNESS_CHALLENGE`、沒把 nonce 餵進交付物的驗證器等於在對自己作弊——要把 nonce 穿過交付物本身。

### 兩個 v2.1.0 新工具

**不變約束 `constraint`**——長任務失敗多半不是能力不夠，而是**跑到一半忘了約束**，而上下文壓縮最先侵蝕的就是這種細節（ACE context collapse / Codex 不變前綴層）。開工前把硬規則寫下來：唯讀路徑、經費上限、預先登錄的閾值、「絕對不要做 X」。它會被 `status` **原樣**顯示在最上方，永不壓縮、永不修剪。它不是 playbook——playbook 是學來的、可修剪的；constraint 是給定的、不可變的。

```bash
$K constraint add "budget.json 是經費的唯一真相來源，不要在內文改數字"
$K constraint list
```

**能力階梯 `ladder`**——當單一二元契約還無法回報進度時，用階梯給一個密集的進度訊號（ExploitBench 16 階梯度）。它回報**連續通過的最高階**，是進度計，**不是**閘門；升級照樣走 held-in/held-out 的 `gate`。

```bash
$K ladder set --name draft --target draft/paper.md \
  --tiers "exists,min_words:1000,sections:Abstract|Methods,no_placeholder,min_words:4000"
$K ladder assert --name draft     # -> tier_reached / tiers_total，也會顯示在 status
```

### 內建的九個驗證器

`scripts/verifiers/` 裡有九個現成的 `cmd:` / `challenge:` 驗證器，全部經過測試：

```bash
V="<plugin>/scripts/verifiers"
python $V/check_budget_alignment.py --doc draft/proposal.md --budget draft/budget.json
python $V/check_coherence.py --doc draft/paper.md
python $V/check_citations_resolve.py --doc draft/review.md --vault vault/
python $V/check_coverage.py --sources refs/ --vault vault/
python $V/check_glossary.py --doc draft/paper.md --glossary draft/glossary.json
python $V/check_reproducible.py --results results/dev_metrics.json
python $V/check_no_null_rt.py --csv results/sim_run.csv --expected-trials 96
python $V/check_timing_distribution.py --csv results/sim_run.csv --condition-col condition
python $V/check_challenge_response.py -- python solver.py   # 由 challenge: 帶起，需 $HARNESS_CHALLENGE
```

每個都有 `--help`。細節見 `scripts/verifiers/README.md`。

---

## 5. 六種任務的實戰用法

每種任務先讀對應的 `profiles/<name>.md`——裡面有該領域真正會出的錯。

### 5.1 設計網站（醫院藥品管理、醫師打卡系統）

**profile**：`web-system`

**關鍵**：這個領域**有真實驗證器**，所以幾乎不需要結構檢查的代理指標。

```bash
$K boot --profile web-system
$K contract --name api --target services/api/app.py --split held_in \
  --checks "exists,python_compiles,no_placeholder,cmd:pytest -q services/api/tests"
$K contract --name e2e --target tests/e2e/report.json --split held_out \
  --checks "exists,valid_json,cmd:npx playwright test --reporter=json"
```

**拆解順序**：`db_schema` → `api_auth` → `api_domain` → `ui_pages` → `e2e`。
schema 先做，後面每個 job 都讀它；等 API 寫完才改 schema 要重寫三次。

**踩坑**：
- 打卡系統的 session 在併發下遺失 → 修的是 **middleware**（共享 session store），不是重試。
- 時區。存 UTC、顯示 Asia/Taipei，寫一個 helper，不要每處各自處理。
- **真實病人與員工資料絕對不要進 sandbox、job log、trace 或 prompt。** 用合成資料，並用 `regex_absent` 契約擋身分證字號格式。
- 管制藥品需要 append-only 稽核軌跡 → 寫成 `cmd:` 契約，不是寫成註解。

### 5.2 專案規劃（國科會計畫）

**profile**：`research-proposal`

**關鍵**：預算與方法對不上，是審查最常挑出、也最機械可查的缺陷。

```bash
$K boot --profile research-proposal
$K contract --name consistency --target draft/proposal.md --split held_in \
  --checks "cmd:python $V/check_budget_alignment.py --doc draft/proposal.md --budget draft/budget.json --methods 研究方法"
```

`check_budget_alignment.py` 會抓：小計加總錯、總計對不上、**編了預算但方法完全沒提到的設備**。

**拆解**：一章一個 job，外加 `refs_align`、`budget_reconcile` 兩個獨立 job。

**踩坑**：
- 平行寫的章節術語會漂移 → 建 glossary.json，用 `check_glossary.py` 檢查。
- 篇幅要**在 fork 時就分配**給各章，不然各章寫滿、總長爆掉。
- **引用捏造是最嚴重的風險。** `regex_present:\[[0-9]+\]` 只確認引用標記存在，不確認論文存在。用 `check_citations_resolve.py --bib` 或 `--vault`，且發出前一定要對真實資料庫核對。

### 5.3 訊號分析方法（EEG / HRV）

**profile**：`signal-analysis`

**關鍵**：切分要**在任何分析之前、依受試者切**，而且開發期間絕不看 holdout。

```bash
$K boot --profile signal-analysis
$K contract --name repro --target results/dev_metrics.json --split held_in \
  --checks "cmd:python $V/check_reproducible.py --results results/dev_metrics.json"
$K contract --name results_holdout --target results/holdout_metrics.json --split held_out \
  --checks "exists,valid_json,json_keys:n_subjects;metric"
```

`check_reproducible.py` 會抓：缺 seed / dataset 版本 / code 版本、**dev 與 holdout 受試者重疊**、同一 seed 跑出不同數字、事後才改門檻。

**公開資料**：PhysioNet（MIT-BIH、Fantasia、CHB-MIT）、OpenNeuro、Temple EEG Corpus。
把**確切的資料集版本記進 playbook**——這件事極容易忘，忘了就不可重現。

**踩坑**：
- 結果隨 window 長度大幅擺動，**不一定是 bug**。有些是訊號本身的性質。`mine` 會把這類標成 `addressable: false`——一個把所有不穩定結果都當 bug 修的迴圈，會把真實現象調掉。
- HRV 指標（SDNN、RMSSD、LF/HF）對記錄長度、呼吸速率、artifact 處理極敏感。跨研究比較前先確認這些條件一致。
- LF/HF 作為「交感／副交感平衡」指標在文獻上有爭議。若分析依賴這個詮釋，要明講。

### 5.4 文獻閱讀與整理

**profile**：`literature-corpus`

**關鍵模式**——這是 harness 價值最明顯的場景：

```
每篇 PDF fork 一個 job
  → job 寫出 vault/<id>.json（結構化摘要）
  → 主執行緒只讀摘要
  → playbook 加一行
  → 徹底忘掉這篇 PDF
```

原始 PDF 內文**從不進主 context**。這一條就是 8 篇與 80 篇的差別。

```bash
$K boot --profile literature-corpus
$K contract --name coverage --target vault/index.json --split held_in \
  --checks "exists,valid_json,cmd:python $V/check_coverage.py --sources refs/ --vault vault/"
$K contract --name citations --target draft/review.md --split held_out \
  --checks "cmd:python $V/check_citations_resolve.py --doc draft/review.md --vault vault/"
```

`check_coverage.py` 抓的是**沉默跳過**：報告涵蓋 40 篇中的 34 篇，看起來跟涵蓋 40 篇一模一樣，沒有任何東西會告訴你。這是這個領域最常見也最不可見的失敗。

**先定好 vault schema**，這樣 40 篇摘要才可比較。schema 見 profile。

**踩坑**：
- 掃描檔沒有文字層 → 偵測擷取結果 < 200 字就轉 OCR，並記錄這次 fallback。
- **檔名含非 ASCII 字元會讓命令列 PDF 工具靜默失敗**（本專案就遇到：`Ö` 讓 `pdftotext` 開不了檔）。用函式庫（pypdf）而非 shell 指令，並靠 coverage 檢查兜底。
- 摘要是**有方向性的失真**：最先被丟掉的是細微差別、保留語氣和作者自陳的侷限——而那正是批判性綜述最需要的。vault 裡保留逐字引文＋頁碼，報告倚重的論點用引文而非改寫。
- 單篇要深挖時用 `academic-paper-deep-analysis`（七層精讀）；廣度用 vault schema。

### 5.5 撰寫學術論文或部落格

**profile**：`academic-writing`

```bash
$K boot --profile academic-writing
$K contract --name coherence --target draft/paper.md --split held_in \
  --checks "cmd:python $V/check_coherence.py --doc draft/paper.md"
```

`check_coherence.py` 是純腳本、不呼叫模型，抓的是平行寫作必然會壞的四件事：
段落近乎重複、縮寫未定義就使用、有標題沒內容的空章節、標題層級跳號。

**拆解**：`outline` → 各章平行 → `terminology_align` → `coherence` → `citation_align`。
**大綱本身就是一個契約**。論證結構要在動筆前定案；寫完四章才重構，等於重寫四章。

**邊界條件（重要）**：
結構、一致性、引用衛生、重複——可檢查，這個迴圈做得很好。
**論證品質、新穎性、文氣——不可檢查。** 用 `/verify-with-rubric` 配一個
**獨立、非 `fork`** 的 sub-agent，rubric 在動筆前寫好，結果當**建議**看。
**絕不**讓自動迴圈對 LLM judge 做無監督最佳化——它會先找到 judge 的盲點，而不是先寫出好文章。

### 5.6 可攜式認知測驗 App

**profile**：`cognitive-app`

**關鍵認知**：這個 App 產出的是**研究或臨床資料**。看起來完美但靜默丟掉 8% 反應時間的 App，比會 crash 的更糟——crash 看得見，資料遺失看不見。

```bash
$K boot --profile cognitive-app
$K contract --name data_integrity --target results/sim_run.csv --split held_in \
  --checks "cmd:python $V/check_no_null_rt.py --csv results/sim_run.csv --expected-trials 96"
$K contract --name timing --target results/sim_run.csv --split held_in \
  --checks "cmd:python $V/check_timing_distribution.py --csv results/sim_run.csv --condition-col condition"
```

模擬一整個 session——包含快速作答、不作答、連點——然後驗證每個 trial 都有一列、沒有 null / 0 / 負值的反應時間。**每輪都跑。**

`check_timing_distribution.py` 會抓一個沒別的東西會發現的問題：**時鐘量化**。
如果幾乎所有 RT 都是 15ms 的倍數，代表用了 `Date.now()` 或 timer tick 而非
`performance.now()`——資料看起來完整，但毫秒級的認知測量在這個解析度下沒有意義。

**踩坑**：
- 快速點擊時 CSV 出現 null → 正解**不是**「寫入失敗就重試」，而是**停止逐次寫入**：記憶體累積、測驗結束一次落盤，另加定期 checkpoint 防瀏覽器關閉。這是機制層修改，不是補丁。
- 不作答要記成 `null` + `timed_out` 旗標，**絕不能記成 0**。混為一談會污染所有下游統計。
- 第一個 trial 常含資產載入延遲 → 預載、並標記或丟棄 trial 1。
- 門診環境：必須離線可跑、中斷後不丟已完成 trial、指導語逐字固定（變動就是混淆變項）。
- **效度警告**：螢幕版重製的量表**不等於**原始已驗證的量表。時序、刺激大小、觀看距離、輸入裝置都會改變常模。紙筆版的切分點不能直接沿用——要在交付物裡寫明。

---

## 6. 什麼時候不要用

Harness OS 有真實的 overhead。它在下列情況划算：任務長（超過一小時或跨 session）、可平行、重做代價高、或**曾經被謊報完成過**。

**不要**用在：改一個檔案、回答一個問題、寫一支短腳本。
十分鐘的任務套完整 harness，是穿著制服的摩擦力。

**部分採用完全合理，而且通常是對的**：只用 contract + `assert` + `publish` 就能消除大部分假完成，成本幾乎為零。真的需要再加 fork / mine / evolve。

---

## 7. 出問題時

| 症狀 | 處理 |
|---|---|
| `harness not booted` | `$K boot`，或設 `HARNESS_WORKSPACE` |
| `fork` 之後 job 狀態 `unknown` | sandbox 沒建起來；檢查 `--cmd` 引號。含引號的指令加 `--shell` |
| job 卡在 `running` 不會逾時 | **逾時是在 `poll` 時強制執行的。** 沒人 poll 的 job 沒人殺它 |
| `gate` 說沒有 held-out contract | 加一個 `--split held_out` 的契約，否則偵測不到過擬合 |
| `guard check` 回 `TAMPERED` | 契約或驗證器被改過。**上次乾淨檢查之後的所有結果作廢。** 停下來告訴使用者，不要「修一修繼續」 |
| 同一個 contract 連三輪失敗 | 停止修補，走 `mine` — 你在修症狀 |
| `loopcheck` 回 `{"loop": true}` | 停。換機制、換工具、或問使用者。不要重試得更用力 |
| 路徑含空格導致指令壞掉 | `KP="路徑"` + `python "$KP"`，不要 `K="python 路徑"` + 裸 `$K` |

---

## 8. 誠實的限制

三件必須知道、而且刻意寫在程式碼與 skill 裡的事：

1. **這個迴圈的上限等於驗證器的忠實度。** 驗證器是真測試時，它很強；驗證器是代理指標（LLM judge、結構檢查代替品質）時，它會找到代理與目標之間的縫隙——因為那比把事情做好便宜。**主觀目標上絕不無監督執行。**

2. **`guard` 是絆線，不是沙盒。** 它讓竄改在紀錄上可見，但擋不住。真正的隔離需要 OS 權限或容器。

3. **背景 job 不回傳 exit code。** `poll` 回報完成狀態與 stderr 尾巴。需要 exit code 時，讓 job 寫一個結果檔，再用 `cmd:` 契約檢查它。

---

## 9. 延伸閱讀

- `README.md` — 指令與版面速查
- `profiles/<name>.md` — 各領域的交付清單、契約、已知失敗機制
- `scripts/verifiers/README.md` — 八個驗證器的能力與限制
- `references/evidence-ledger.md` — 每個設計決策對應到哪篇論文的哪個發現
- `references/prototype-delta.md` — 相對於原型改了什麼、為什麼
- 理論來源：Lilian Weng, [Harness Engineering for Self-Improvement](https://lilianweng.github.io/posts/2026-07-04-harness/)（2026-07-04）
