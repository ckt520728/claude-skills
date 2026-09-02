# Harness OS 建置回顧：踩過的坑

一個 session 內從 14 篇論文 + 一份 Gemini 原型，做出可用的 Harness OS plugin。
記錄過程中真正踩到的坑——原型的、環境的、以及**我自己犯的**。

原則：只記真的發生過的事。沒發生的預想不寫。

---

## 一、最重要的一課：綠燈的測試套件擋不住沒被測到的那一層

**發生了什麼**
kernel 寫完，24 項 selftest 全綠。接著我用 CLI 跑一次真實流程，`fork` 指令
**完全沒作用**——沒有建 sandbox、沒有輸出、`exit 0`。

**根因**
argparse 的 subparser 用了 `dest="cmd"`，而 `fork` 子指令自己定義了 `--cmd`。
argparse 把指令字串寫進 `a.cmd`，**覆蓋掉子指令名稱**，dispatch 掉出所有分支，
函式回傳 `None`，shell 看到 exit 0。

```python
sub = p.add_subparsers(dest="cmd")     # 撞名
s.add_argument("--cmd", required=True) # 覆蓋
```

**為什麼 24 項測試沒抓到**
selftest 全部呼叫 Python API（`h.fork(...)`），沒有一項走 CLI。而 skill 教使用者
用的是 CLI。**我測了不是使用者會走的那條路。**

**修法**
1. `dest="subcommand"`，並在該行留下說明為何不能叫 `cmd`。
2. selftest 加入 CLI 層（24 → 31 項），其中一項是通用的：
   **「任何已宣告的子指令都不得靜默無輸出」**——這會擋掉整類同型錯誤，而不只這一個。

**教訓**
這正是整個專案要防的失敗型態：**綠色的摘要蓋在紅色的現實上**。
API 層測試 + 未測的介面層 = 假完成。
它是被「跑一次」抓到的，不是被「讀一次」抓到的。

---

## 二、我把「我沒找到」當成「不存在」

**發生了什麼**
Gemini 筆記說整個框架出自 Lilian Weng 的《Harness Engineering for Self-Improvement》。
我查核後標為「未經證實，不予沿用」，理由是：`Reference/` 裡沒有這篇、14 篇 PDF 也沒引用它。

使用者指出：那篇文章是真的，**這 14 篇就是它的參考文獻**。

**根因**
我的兩個理由在結構上不可能成立：
- 那篇文章是這份閱讀清單的**來源**，本就不會出現在自己的參考書目裡。
- 早於它發表的論文，不可能引用它。

我用了一個**在設計上不可能包含查核對象**的證據來源，去做查核。

**修法**
抓取原文確認（Lilian Weng，2026-07-04），修正五個檔案，並把「harness 即 OS」的
類比正確歸屬回原文——那句話本來就是 kernel／skill 分工的設計綱領。

**教訓**
> 「在我蒐集到的證據中不存在」≠「無根據」。
> 宣告某事未經證實之前，先問：**我的證據來源有沒有可能包含它？**

比第一課更難防。第一課靠跑測試就會現形；這一課只有靠問一個關於方法本身的問題才會現形。

---

## 三、原型的七個阻斷性缺陷

Gemini 原型架構是對的（檔案系統即記憶體、進程隔離、斷言後才發布、弱點挖掘）。
但實作有七處會在第一個真實任務就撞死。最嚴重的三個：

### 3.1 「並行子代理派發」根本不存在

```python
result = subprocess.run(cmd_list, ..., timeout=300)   # 原型
```

`subprocess.run` 會**阻塞到子行程結束**。整個架構賴以成立的核心功能是假的。

改為 `Popen` + 分離 process group + `poll`（非阻塞、順便回收與強殺逾時）／`wait` 分離。

**教訓**：架構圖上的方塊不等於程式碼裡的行為。畫得出來不代表跑得起來。

### 3.2 `/workspace` 硬編碼

`def __init__(self, workspace_root: str = "/workspace")` — 在 Windows 上必死，
而這正是使用者的環境。搭配的 `harness_run.sh` 也假設 bash 與 `python3`。

改為 `HARNESS_WORKSPACE` → `--workspace` → cwd，全程 `pathlib`，
Windows 用 `tasklist`／`taskkill`，POSIX 用 process group。

### 3.3 斷言器可以被垃圾檔通過

原型只檢查 `exists`、`not_empty`、`valid_json`、以及「檔案裡有沒有 `#` 字元」。
**一個只有一個 `#` 的一位元組檔案可以通過所有檢查。**
而最常見的真實失敗——看起來像樣、實際塞滿 `TODO` 又中途截斷的草稿——全數通過。

擴充到 12 種檢查，其中 `no_placeholder`（TODO / FIXME / lorem / 「…以下略」）
與 `sections:A|B|C`（指名的標題必須存在）是抓真實假完成的主力。

其餘四個（hot-patch 只寫三個沒人讀的字串常數、迴圈偵測只比對 action 名稱、
失敗分群沒有機制維度、驗證器與被驗證物同在可寫目錄）記在
`harness-os/references/prototype-delta.md`。

**共同教訓**：原型自己的分析文件**正確指認了獎勵欺騙是核心風險**，然後沒有實作
任何對策。**指認風險不等於處理風險。**

---

## 四、環境層的坑（Windows + Claude Code）

| 坑 | 現象 | 解法 |
|---|---|---|
| 長 heredoc 失敗 | `ENAMETOOLONG: uv_spawn`；多檔 heredoc 直接讓 shell 語法錯誤，且**檔案一個都沒建立** | 超過幾百行用 Write 工具，不要用 `cat > f <<'EOF'` |
| 路徑含空格 | `K="python D:/2026 Claude .../k.py"` 再用裸 `$K` → 在空格處斷開，Python 說找不到 `D:\2026` | `KP="路徑"` + `python "$KP"` |
| 非 ASCII 檔名 | `pdftotext` 開不了含 `Ö` 的 DGM 論文，**其他 13 篇全部成功**——差點沉默漏掉一篇 | 用 `pypdf` 等函式庫，不要用命令列工具 |
| Python 八進位跳脫 | 非 raw 字串裡的 `\2026` 被當成 `\202` + `6`，寫進 Obsidian 的路徑變成 `D:\x826 Claude...` | Windows 路徑一律用 raw string 或 `chr(92)` 組合 |
| cp950 主控台 | 印出中文路徑時 `UnicodeEncodeError`，但**檔案本身是好的 UTF-8** | 驗證時印 ASCII-safe 的摘要，不要印原字串 |

第三項值得特別記：**它是「沉默漏一篇」型的失敗**。13 篇成功、1 篇失敗、沒有錯誤
彙總，如果不是後來清點數量就會漏掉。這正是後來 `check_coverage.py` 存在的理由——
那個驗證器是從這個坑長出來的。

---

## 五、測試自己也會有盲點

寫驗證器測試時，`check_coverage.py` 的「必要欄位為空」案例過不了：測試預期失敗，
實際回傳 PASS。

追下去發現不是測試寫錯，是**驗證器有真實漏洞**：兩個 vault entry 用了同一個 `id`，
後讀到的會**靜默覆蓋**前一個。一篇論文的摘要就這樣消失，而 coverage 仍然顯示「完整」。

這正是 `check_coverage.py` 存在的目的——結果它自己有這個洞。

**修法**：加上重複 id 偵測（hard fail），測試改用不衝突的 id，另外補一個專測重複 id 的案例。64/64 通過。

**教訓**：測試失敗時，先問「是測試錯了，還是被測物錯了」。這次是後者。
如果我當時改測試去遷就程式，就會把洞留下來。

---

## 六、有效的做法

不只記坑。這些是真的有用的：

1. **先問兩個問題再動工。** packaging 與語言這兩個決定會影響整份產出，事後改是重寫。花一次提問，省一次重做。

2. **`selftest` 當成一級交付物。** kernel 自帶 31 項自測、驗證器自帶 64 項。
   每次改動前後各跑一次。沒有這個，前面那個 `fork` 的 bug 會一路活到使用者手上。

3. **每條規則都要有出處。** `evidence-ledger.md` 把每個機制對應到論文的哪一節。
   沒有出處也沒有理由的規則就是裝飾，而且每次載入 skill 都在付 token。

4. **誠實聲明限制，而不是含糊帶過。** `guard` 是絆線不是沙盒、evolve loop 會鑽驗證器的洞——
   這兩點寫在程式碼註解、skill、README 三個地方。
   **高估自己安全性的 harness 比沒有安全機制更糟，因為它會讓人不再檢查。**

5. **從真實失敗長出驗證器。** 八個驗證器裡至少兩個（coverage、citations resolve）
   直接來自這次 session 踩到的坑。設計驗證器最好的來源是剛發生的事故。

---

## 七、可遷移的三條原則

1. **測使用者會走的那條路，不是你方便測的那條。**（第一課）
2. **宣告「未經證實」之前，先確認你的證據來源有可能包含它。**（第二課）
3. **指認風險不等於處理風險。**（原型的獎勵欺騙）

---

## 附：最終狀態

| 項目 | 狀態 |
|---|---|
| kernel selftest | 31/31 PASS |
| verifier tests | 64/64 PASS |
| skills | 6 個（orchestrator + boot/fork/assert/mine/evolve），已裝到 `~/.claude/skills/` |
| profiles | 6 個領域 |
| verifiers | 8 個 `cmd:` 驗證器 |
| 文件 | README、USER_MANUAL、evidence-ledger、prototype-delta、verifiers/README |

**尚未做的事**：全部只經過 selftest，**沒有跑過一次真實任務**。
設計都有證據支撐，但設計與實作的落差只會在真實執行時暴露——
就像第一課裡的 `fork` bug 一樣。下一步應該是拿 `research-proposal` 或
`literature-corpus` profile 對真實材料端到端跑一次。
