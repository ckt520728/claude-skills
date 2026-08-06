# HHSA Python 與 Closed-Loop 研究原型：Wrap-up 與踩坑紀錄

日期：2026-08-06
工作目錄：`C:\Users\YangminRoom1\Documents\Dr Chu's file\2026 HHSA Python Code and closed loop`

## 本次成果

- 盤點並驗證離線 HHSA、closed-loop controller、LSL live path 與 hardware interlock 的現況。
- 建立可重用 skill：`skills/hhsa-closed-loop-prototyping/`。
- Skill 內含：任務分流與安全邊界、架構與驗證矩陣、已知陷阱參考，以及可重跑的專案 audit script。
- 保留原專案的研究原型定位：預設只允許模擬、錄製或 marker output，不把軟體 interlock 誤稱為臨床安全系統。

## 驗證結果

| 驗證 | 結果 | 備註 |
| --- | --- | --- |
| `python -m pytest -q` | 102 passed | 約 44.69 秒；pytest cache 因 sandbox 權限出現 1 個非測試失敗警告 |
| `python validate_ground_truth.py --no-plot` | 5/5 passed | clean/noisy/masked AM、theta-gamma PAC、sawtooth false-PAC guard 全數通過 |
| `python demo_closed_loop.py --quick` | 通過 | 23,040 samples、7.5% blanked、0 safety violations；quick run 會改寫追蹤中的 PNG |

Ground-truth 代表性結果：16 Hz/2 Hz clean AM peak 落在約 `(17.45, 1.83)` Hz；noisy 與 mask-sift 條件仍在 log-bin 容許範圍。Sawtooth 測試的真實 2 Hz AM 對 4–16 Hz 背景比大於一百萬倍。

## 最重要的技術決策

1. HHSA 第二層輸入必須是 `abs(IMF)` extrema 的 cubic-spline envelope，不能偷換為 Hilbert magnitude。
2. `f_am < f_c` 是逐 sample 的物理限制；違規 sample 應丟棄而不是截斷。
3. 離線 HHSA 與線上因果控制是兩條不同 code path；約 32 ms/window 的 HHSA 不可放進 1.95 ms/sample 的 fast path。
4. Phase targeting 使用 AM envelope extrema，但 amplitude gate 使用 carrier RMS，否則在 trough 目標會把所有 trigger 擋掉。
5. Latency 必須拆成 detection lag 與 transport lag；後者需先清空 LSL backlog 再量測。
6. Blanking 後送入慢速 HHSA 的資料應插值，不應 sample-and-hold；後者會把 AM power 向上偏移並造成正回饋。
7. Physical stimulation 之前必須另有獨立硬體 current limit/interlock、watchdog、急停、設備手冊驗證、倫理核准與合格人員監督。

## 本次遇到的 pitfalls

### 1. 文件中的測試數已過期

`CLAUDE.md` 仍寫 74/74，但目前實際 suite 是 102 tests。結論是 wrap-up 應引用當次 command output，不應照抄狀態文件；文件中的固定計數需視為可能漂移。

### 2. pytest cache 權限警告

受限環境可執行全部測試，卻可能無法更新 `.pytest_cache`。這不是產品失敗。Reusable audit script 使用 `-p no:cacheprovider`，避免把無關 cache 權限混進驗證訊號。

### 3. Quick demo 會動到 tracked figure

`demo_closed_loop.py --quick` 不只是讀取驗證，也會寫入 `closed_loop_demo.png`。若直接提交，可能把較短模擬的圖誤當成 canonical artifact。處理方式是提交前重跑完整 demo，並檢查 `git diff/status`。

### 4. Windows console 與 CJK

本機 cp950 console 會讓部分中英混合文字顯示成亂碼。技術文件與產物一律以 UTF-8 寫檔，不把 console rendering 當成內容正確性的判準。

### 5. Scientific code 最危險的是 silent wrong answer

先前錯誤多半不會 crash，而會產生看似合理的 spectrum、phase 或 trigger。單元測試之外，必須保留 synthetic ground truth、phase-effect reversal、stream gap/rate、charge/watchdog 等行為級驗證。

### 6. Skill 與 source project 是兩個發布範圍

Skill 在原 working folder 中開發與驗證，但 GitHub 目標是 `ckt520728/claude-skills`。發布時應明確複製 skill 與 wrap-up、逐一 staging，避免把整個研究資料夾或可能含敏感來源的壓縮檔誤推到公開 repository。

## 後續使用方式

在另一個 HHSA/EEG closed-loop 專案中呼叫 `$hhsa-closed-loop-prototyping`，先做 static/core audit，再依修改範圍跑對應的 ground truth、controller、LSL 或 hardware tests。若任務涉及真實刺激器，skill 應停在 verified manual 與獨立安全條件的邊界，而不是猜測 vendor protocol。
