# 專案收尾 — 踩過的坑與可重用做法

**專案：** JEV Engineering — 把 agent loop 裡「不需要生成文字的決策」從前沿模型搬到便宜的校準決策層（System One / TypeSafe Jev），並用信心值控制升級；產出一份可攜的 agent skill 加可執行的 Python 套件
**日期：** 2026-09-29（兩個工作階段：v1.0 建置、v1.1 擴充跨平台路由）
**成果：** `jev-engineering/` skill + plugin：163 行 SKILL.md、18 份 reference playbook（2,100 行）、3,449 行純標準庫 Python（9 個模組）、5 個可執行範例、108 項行為測試、2 個 Claude Code hook
**環境：** Windows 11、Git Bash + PowerShell 5.1、Python 3.9.12（Anaconda）、Claude Code

參考來源：Li et al. (2026) *JEV-as-a-Judge* (CMU) 加四篇 X 長文（@N01ennn、@0xCodila、@polydao、@0xwhrrari）。本文只寫**這次實作時真正踩到的坑**，不重述論文結論。

> **驗證聲明：** 本專案**從未呼叫過真實 API**。全部 108 項測試跑在 stub provider 上。
> 所有成本數字都來自論文的凍結價格表、廠商公告、或明確標記 `SYNTHETIC` 的合成價格。
> `models.json` 裡 9 個模型有 7 個沒有價格、6 個沒有 `api_id`——這是刻意的，不是待辦遺漏。詳見 `jev-engineering/UNKNOWNS.md`。

---

## 零、一句話總結

| # | 教訓 | 適用範圍 |
|---|---|---|
| 1 | **「便宜模型省錢」的直覺會漏掉 KV cache 重讀這一項，而那一項常常最大。** 5/25 對 3/15 的價差下，借用便宜模型跑一步再切回來，成本是原地不動的 **1.49 倍** | 任何 model routing / 分層架構 |
| 2 | **router 要打敗的不是「全部用最強的」，是「先用便宜的、失敗才往上爬」。** 後者不需要 router、不需要 registry、不需要任何決策呼叫；能力梯度平緩時它在**任何** router 準確率下都勝出 | 任何要導入分層路由前的評估 |
| 3 | **把重試當成獨立擲硬幣，會讓最弱的層在紙上變成最便宜的選項。** 修正前「全部用 low」是成本最低的政策——它只完成 62 % 的任務 | 任何含重試的成本模型 |

三句的共同點：**便宜的那一項不會自己把代價報給你，要自己把代價那一項寫進公式。**

---

## 一、KV cache 重讀是 routing 最大的隱形成本（這節最貴）

### 1. 分層路由失敗兩年的原因不在價目表上

**症狀：** 直覺上「簡單段落丟給便宜模型、難的留給貴模型」一定省錢。實測反而變貴。

**實測：** 大模型 5/25、小模型 3/15（美元 / 百萬 token）。令 `X` = context、`Y` = 產出、`Z` = 產出過程中被觸發讀入的 token：

```
原地不動  = 25Y + 5Z
切下去再切回 = 3X + 20Y + 8Z
```

代入 `X=0.65, Y=0.12, Z=0.23`（Mtok）：$4.15 對 $6.19，**切換貴 49 %**，而且 $2.04 的差額裡有 **$1.75 純粹是大模型重新讀一遍小模型的產出**。

**原因：** 控制權交回大模型時，它必須重讀小模型產生的全部內容，KV cache 要重建。這一項不出現在任何定價頁面上。

**要點：** 決策層之所以成立，不是因為它便宜，是因為它**從不進入對話**——不載入歷史、不產生 token、不留下需要重建的 cache。這是「決策層」和「便宜模型」的架構性差別。

### 2. 我把這條規則寫成了絕對規則，然後被自己的 demo 反駁

**症狀：** 第一版 `16-self-switching.md` 寫「借用什麼都不要借，要嘛整段交出去、要嘛原地不動」。`route_models.py` 跑出來卻顯示「切換」。

**原因：** 我在文件裡用 5/25 vs 3/15，在 demo 裡用 10/50 vs 3/15。後者的 output 價差是 12 倍，省下的產出費用蓋過了重讀費用。

**修正後的條件式：**

```
來回切換划算  ⟺  Y × (A_out − B_out − A_in)  >  B_in × (X + Z)
                      └──────  margin  ──────┘
```

`A_in` 以**減項**出現，因為那就是重讀的單價，而它扣的是同一個 `Y`。

| high tier | medium tier | margin | 結論（X=0.65, Y=0.12, Z=0.23） |
|---|---|---|---|
| 5 / 25 | 3 / 15 | 5 | 原地不動 |
| 2 / 10 | 1 / 5 | 3 | 原地不動 |
| 3 / 15 | 0.8 / 4 | 8 | 切換 |
| 10 / 50 | 3 / 15 | 25 | 切換 |
| 10 / 50 | 0.8 / 4 | 36 | 切換 |

**要點：** 相鄰兩層的 output 價差窄（1.7 倍）→ 重讀費用主導，不要借；價差寬（12 倍）→ 借得起。**不要背任何 rule of thumb，把真實價格填進 registry 然後呼叫 `worth_switching()`。** 現在這條不等式寫在文件裡，而且 `test_smoke.py` 用五組價格檢查實作與公式一致——**沒有程式在執行的公式，只是一段註解。**

### 3. 單向移交（one-way handoff）幾乎總是比來回切換划算

把「借一步再還」換成「剩下的都交給你」，重讀那一項直接消失。同樣價格下 one-way 在 context < 0.553 Mtok 時划算。

**要點：** 真要切換，就在**自然邊界**切（一個階段完成、測試轉紅），把剩下的整段交出去。**絕對不要在寫到一半的改動中間切換**——接手的模型只能從半成品的 diff 去猜意圖。

---

## 二、成本模型自己會騙人

### 4. 重試不是獨立事件，把它當獨立事件會讓最弱的層勝出

**症狀：** 第一版 `compare_policies()` 跑出「全部用 low」是每完成任務成本最低的政策。直覺上不對。

**原因：** 我用幾何級數算重試：成功率 0.55、重試 3 次，完成率 = 1 − 0.45³ = 0.909。但**能力不足的層重試不會變得有能力**——多數失敗是能力問題，不是運氣問題。

**修正：** `TierProfile.retry_recovery`（預設 0.25）讓每次重試的成功率衰減到前一次的四分之一。0.55 + 3 次重試的真實完成率降到 **62.5 %**。

**要點：** 這個單一數字會左右整張政策比較表。把它設成接近 1.0，就是製造一份會替弱模型背書的試算表。

### 5. 完成率必須和成本擺在同一張表，不能藏進分母

**修正後的輸出：**

```
always low            $0.09408/task  1.84 calls   0.0% escalated   62.5% completed
escalate from low     $0.12630/task  1.55 calls  45.0% escalated   99.6% completed
always medium         $0.19245/task  1.36 calls   0.0% escalated   84.8% completed
routed (90% accurate) $0.19565/task  1.40 calls  31.8% escalated   98.9% completed
always high           $0.46233/task  1.11 calls   0.0% escalated   95.7% completed
```

「全部用 low」仍然是每完成任務最便宜的——**而它只完成 62 % 的任務**。

**要點：** 任何只報「每任務多少錢」而把完成率折進分母的比較，每一次都會讓最弱的層看起來最好。兩欄一起讀，不然不要讀。

### 6. router 要打敗的是那個「什麼都不用建」的政策

**症狀：** 我原本拿 routing 去比「全部用 high」，它輕鬆勝出，看起來很成功。

**實測：** 拿去比「先用 low、失敗往上爬」（不需要 router、不需要 registry、連一次決策呼叫都不用）：

```
beats 'always high' at any router accuracy
never beats 'escalate from low': $0.13894/task even at 100% accuracy vs $0.12630/task
```

**要點：** 打敗「全部用最強的」幾乎不證明任何事。**能力梯度平緩時（便宜的層本來就能完成大部分任務），誠實的結論是不要做 router，直接往上爬。** routing 值得做的條件是：梯度陡 **且** 一次白費的便宜嘗試很貴（長任務、有副作用、失敗會花掉人的注意力而不是四美分）。

**這個比較要在建 router 之前跑，不是之後。**

### 7. 一個回傳 `None` 表示兩種相反結論的函式

**症狀：** `router_breakeven_accuracy()` 在「任何準確率都勝出」和「連 100 % 都打不贏」兩種情況都回傳 `None`。呼叫端無法區分，而它回報了一個掃描結果明確否定的「勝出」。

**修正：** 改回傳 `BreakEven` dataclass，`status` 明確三態：`always` / `never` / `threshold`。

**要點：** 這是我這次犯的最危險的一種 bug——**它不會壞掉，它會說謊**。任何「找不到答案」和「答案是邊界值」共用同一個回傳值的函式，都要拆開。

---

## 三、Claude Code hook 的坑

### 8. 寫入 `.claude/settings.json` 會立刻生效，包含當前這個 session

**症狀：** 我把 `hooks` 區塊寫進 `.claude/settings.json`，下一個 Bash 呼叫就被 hook 攔下並失敗：

```
PreToolUse:Bash hook error: can't open file
'D:\2026 JEV Engineering\skills\jev-engineering\assets\.claude\hooks\jev_gate.py'
```

**兩個獨立的原因：**

1. **hook command 的相對路徑是對「session 當下的工作目錄」解析，不是對專案根目錄。** agent 一 `cd` 進子目錄，`python .claude/hooks/x.py` 就找不到了。→ 必須用 `$CLAUDE_PROJECT_DIR`。
2. **沒有 API key 時，gate 會（正確地）fallback 到 `ask`**——也就是**每一個** Bash 呼叫都跳權限確認。那不是一個安全的安裝，那是一個壞掉的安裝。

**解法：** hook 接線放在 `.claude/settings.json.example`，預設**不啟用**，並把原因寫進 `CLAUDE.md`。`settings.json` 只留一段 `$comment` 說明為什麼是空的。

**要點：** 會改變 harness 行為的檔案，寫下去就是立即生效的部署動作，不是編輯文字。**先寫成 `.example`，讓啟用成為一個明確的人為決定。**

### 9. hook 裡的子程序繼承的 PATH 常常沒有正在執行它的那個 Python

**症狀：** `checks.sh` 手動跑正常，從 Stop hook 呼叫時每一項 Python 檢查都失敗：`python: command not found`。

**解法：** hook 把自己的解譯器傳下去，腳本優先採用：

```python
env = {**os.environ, "PYTHON": sys.executable}
subprocess.run(["bash", CHECKS.relative_to(PROJECT).as_posix()], cwd=str(PROJECT), env=env)
```

```bash
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for candidate in python3 python py; do
    if command -v "$candidate" >/dev/null 2>&1; then PY="$candidate"; break; fi
  done
fi
```

### 10. 傳 Windows 絕對路徑給 Git Bash，會得到一個看起來像「測試失敗」的錯誤

**症狀：** Stop hook 回報「checks.sh 失敗，去修測試」。實際上 `bash` 根本沒能執行那個腳本。

**原因：** `str(CHECKS)` 在 Windows 是 `D:\...\checks.sh`（反斜線），Git Bash 無法解析，`exit 127`。而 hook 原本只判斷 `returncode != 0`，於是把「執行不了」誤報成「測試沒過」——agent 會被送去修一批從來沒跑過的測試。

**兩處修正：** 傳**相對於 cwd** 的 posix 路徑；並把 `126/127` 單獨判為「無法執行」，回報沒有結論而不是回報失敗。

**要點：** 「無法取得結論」和「結論是失敗」是兩件事。任何把 exit code 當布林值的 gate 都會把前者變成後者。

### 11. gate 的失敗方向要選，而且要寫下來

`allow` on error 比沒有 gate 更糟；`deny` on error 會讓 agent 在網路抖動時完全不能用。**選 `ask`，然後監控 error 率**——一直在 ask 的 gate 已經不是 gate，是一個提示。

---

## 四、決策層本身的坑

### 12. 廣為流傳的範例程式碼有錯，官方文件才是對的

**實測：** 四篇 X 長文裡有兩篇使用 `result.choices[...]`、`result.nouls[...]`、`result.scores[...]`。**官方文件的回應格式只有 `answers[...]`**，所有 primitive 共用。而**同一批來源**在別處又正確地寫 `res.answers["risk"]`——它自己就前後矛盾。照抄那些片段會在 runtime 拿到 `AttributeError`。

其他兩處：`Score(labels=[...])` 應為 `criteria=`；`$0.042/Mtok` 這個價格**無法用直接抓取確認**（文件頁 render 成 `$42,000`，顯然是渲染問題），而所有成本數字都繼承這一個未確認的數字。

**要點：** 二手教學文的程式碼片段要當成**假設**，不是事實。先對官方文件核對再寫進 library。這次的做法是：所有不一致都記進 `UNKNOWNS.md`，並在文件裡明寫「哪一個來源錯了」——因為下一個 session 一定會先去翻那些長文。

### 13. Noul 沒有 `confidence` 欄位，硬湊一個出來要標記清楚

**實測：** `Choice` 和 `Score` 回傳 `confidence`；`Noul` 只回傳 `noul` 一個機率，文件明言「沒有另外的 confidence」。

**做法：** 需要統一介面時自己導出 `certainty = abs(noul − 0.5) × 2`，但**在 docstring 裡寫明這是自己的統計量、和 Choice 的原生 confidence 不同尺度、門檻必須分開調**。

**要點：** 把自製指標偷偷塞進和原生指標同一個欄位，是一種很安靜的 mis-set。

### 14. 「一直沒有升級」是一個沒有症狀的失敗模式

如果升級路徑從來沒觸發過，`tau` 太鬆，而你已經無聲地建了一套無人監督的系統。所有 gate 都內建 health 回報：ask 率 0 % 和 ask 率接近 100 % 都是警告。

---

## 五、工具鏈的坑

### 15. Bash heredoc 寫 markdown 在這個環境會斷

**症狀：** `cat > file.md <<'EOF' ... EOF` 回 `unexpected EOF while looking for matching`。行尾 CRLF 讓 terminator 變成 `EOF\r`，永遠對不上。

**解法：** 大量 markdown 一律用 Write tool。需要程式化改檔時，用 Python 讀寫並**明確指定** `encoding="utf-8", newline="\n"`。

### 16. 用字串替換改自己剛寫的檔案，會安靜地漏掉

**症狀：** 一個 patch 腳本裡四個 `.replace()`，三個成功一個沒中，`print("patched")` 照樣印出來。結果是函式簽章改了、呼叫端沒改，`TypeError`。

**解法：** 小範圍改動用 Edit tool（不中就報錯）。真的要用腳本，就**每個替換都斷言恰好命中一次**：

```python
n = text.count(old)
if n != 1:
    sys.exit("edit matched %d times (need exactly 1)" % n)
```

**要點：** 和 `2026-09-04` 那份記的同一條教訓，這次是在自己的 patch 腳本上再踩一次。`n != 1` 就中止，價值全部在這裡。

### 17. Python 3.9 沒有 runtime 的 `X | Y`

`from __future__ import annotations` 只讓**註解**變字串。模組層級的 `Question = Choice | Score | Noul` 是 runtime 運算式，3.9 會直接 `TypeError`。→ 用 `Union[...]`。

**要點：** 這種東西要在真實目標解譯器上跑一次才會知道。這次把「Python 3.9 相容」寫成 `CLAUDE.md` 裡的 invariant。

---

## 六、可重用產出

### 用 stub provider 把整個決策面測起來

最有價值的工程決策：`decide()` 走一層 provider，測試註冊一個 stub 回傳 wire 格式。於是**不用 API key、不連網、不花錢**就能鎖住整個決策矩陣：

```python
@register_provider("stub")
def stub(state, questions, model, timeout):
    return {"model": "stub", "answers": {...}, "usage": {"input_tokens": 400}}
```

`eval/test_smoke.py` 的 108 項檢查鎖的是**決策矩陣本身**：哪個 capability 在哪個 confidence 產生哪個 verdict、哪個訊號會升級路由、切換在什麼價格下划算。這讓「改一個門檻」變成安全動作。

**可直接搬用：** 任何把 LLM / 外部 API 判斷放進控制流的系統，都應該有一層可替換的 provider 加一份鎖住決策矩陣的測試。不然每次調門檻都是盲改。

### 把 registry 當資料，而且讓程式拒絕猜

`models.json` 是**資料不是程式**——價格和 model id 每週在變，埋在模組裡的常數沒人會回去核對。三條硬規則：

1. **沒有價格的模型永遠不被當成免費。** `select()` 只對有價格的候選做成本排序，並警告它只排了子集；全部沒價格就退回平台偏好順序。
2. **display name 永遠不會被當成 identifier 送出去。** `Model.callable_id` 沒填 `api_id` 就 raise。「Claude Opus 5.5」是名字，`claude-opus-5` 是 id，混用等於凌晨三點的 404。
3. **`Registry.audit()` 明列還缺什麼。** 缺價格、缺 id、未驗證的 id、空的 tier。

還有一個模型上的更正：**tier 不是 model，是 `(model, effort)` 配對。** 同一組權重在不同 reasoning effort 下買到不同能力、不同價格——所以 Gemini 3.6 Flash 同時出現在 medium（`-high` effort）和 low（`-medium` effort）。忽略 effort 的路由會路由到「Flash」，然後拿到供應商的預設 effort。

### 政策優先於分類器

`secrets` 這個 data class 不是一個路由結果，是一個**停止**。`route_task()` 直接 `raise PolicyStop`，而不是挑一個模型——因為要防的失敗模式是 agent 好心地把 data-class 過濾條件拿掉再試一次。

同樣的形狀在 tool gate：8 個 capability class 裡有 4 個（`network_egress`、`credential_access`、`spend`、`other`）門檻設成 **1.01**，一個永遠達不到的數字。「一律問人」因此和可調門檻**寫在同一張表裡**，不是散在程式別處的特例。

### 「政策」和「分類」的分界線

可重用的判準：**不可逆、花錢、對外可見 → 不論信心多高都給人。** 其他的才用不確定性升級。這句話是被問「為什麼一個很有信心的分類器還要問我」時該拿出來的答案。

---

## 七、下次要先問的問題

1. **這個切換的重讀費用是多少？** 在寫任何 routing 之前，把 `A_out − B_out − A_in` 算出來。margin 是負的或很小，就不要做分層。
2. **我要打敗的那個政策，真的是「全部用最強的」嗎？** 先跑「先便宜、失敗往上爬」。打不贏它，就不要建 router。
3. **這張成本表有沒有報完成率？** 沒有的話，最弱的那一層一定在表上看起來最好。
4. **重試在我的模型裡會不會憑空變出能力？** 把 `retry_recovery` 寫出來，不要讓幾何級數替能力不足的層背書。
5. **這個檔案寫下去會不會立刻改變 harness 行為？** 會的話先寫成 `.example`。
6. **這個回傳值有沒有一個值代表兩種相反結論？** 有的話現在就拆開。
7. **這些數字裡有幾個是我真的量過的？** 這次的誠實答案是：零個成功率、零個門檻、零次真實 API 呼叫。全部寫進 `UNKNOWNS.md` 的第四象限，並按「關掉一個要花多久」排序。

---

## 附：檔案位置

- Skill / plugin：`jev-engineering/`（`claude plugin marketplace add <path>/jev-engineering`）
- 入口：`jev-engineering/skills/jev-engineering/SKILL.md`
- 18 份 playbook：`.../references/00-17`
- 可執行套件：`.../assets/jev/`（純標準庫，Python 3.9+）
- 未知清單（四象限）：`jev-engineering/UNKNOWNS.md`
- 工作階段紀錄：`jev-engineering/HANDOFFS.md`
- 全部驗證：`cd jev-engineering && bash .claude/checks.sh`
