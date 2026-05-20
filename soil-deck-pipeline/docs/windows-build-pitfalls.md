---
title: Windows 建置簡報的踩坑全集（HTML + PowerPoint）
date: 2026-05-20
type: pitfalls-reference
applies_to:
  - soil-deck-pipeline
  - soil-html-deck
  - soil-teaching-deck
  - soil-image-deck
---

# Windows 建置簡報踩坑全集

> 這份文件記錄在 Windows + Anaconda + PowerShell 5.1 環境，用 Claude Code 產 HTML 與
> PowerPoint 簡報時，**真實踩過並解決**的坑。動到對應環節前先讀。

---

## 坑 1：Anaconda 的 PIL（Pillow）DLL 載入失敗

**症狀：**
```
ImportError: DLL load failed while importing _imaging: 找不到指定的模組。
```
連帶 `import pptx` 也會炸（python-pptx 在 import 時就會 `from PIL import Image`）。

**根因：** Anaconda base 環境的 Pillow native DLL 壞掉；且該機 `pip` 的 SSL module 不可用、`conda` 不在 PATH，無法即時重裝。

**解法（二選一）：**
- **影像壓縮** → 不要靠 Pillow，改用 **PowerShell + .NET System.Drawing**（見 [`scripts/compress_images.ps1`](../scripts/compress_images.ps1)）。
- **產 PPTX** → 在 `import pptx` **之前**注入一個最小 PIL stub（見 [`scripts/pptx_pil_stub.py`](../scripts/pptx_pil_stub.py)），用 `struct` 自己讀 PNG/JPEG header 拿尺寸，繞過壞掉的 DLL。

---

## 坑 2：PowerShell 5.1 把 UTF-8（無 BOM）腳本當 ANSI 讀

**症狀：** `.ps1` 內的中文變成亂碼，且常以**詭異的 parser error** 出現（例如 `Unexpected token`、`The string is missing the terminator`），讓人誤以為是語法錯。

**根因：** Claude Code 的 `Write` 工具預設寫 UTF-8 無 BOM；但 Windows PowerShell 5.1 預設用系統 ANSI codepage 解讀 `.ps1`，中文位元組被打散。

**解法：**
- `.ps1` 本體**全 ASCII**（註解、字串都不要放中文）。
- 需要中文的地方（例如 git commit message）→ 抽到獨立的 **UTF-8 sidecar 檔**，腳本用 `[System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)` 明確以 UTF-8 讀進來。
- 要寫中文檔案內容時，用 `New-Object System.Text.UTF8Encoding($false)` + `[System.IO.File]::WriteAllText()`（無 BOM）。

---

## 坑 3：含中文的檔案路徑，PowerShell `Test-Path` / `Join-Path` 找不到

**症狀：** 路徑明明存在（如 `G:\我的雲端硬碟\...`），`Test-Path` 卻回 false、`Get-ChildItem -Filter` 回空。

**根因：** 同坑 2——`.ps1` 以 ANSI 讀，腳本內寫死的中文路徑字串已被破壞。

**解法：**
- 先用 **Bash 工具**（對 UTF-8 友善）把需要的檔案 `cp` 到**純 ASCII 路徑**（如 `images/foo.png`），再讓 PowerShell 處理 ASCII 路徑。
- PowerShell 端一律用 `-LiteralPath`，且路徑變數從 ASCII 來源或 UTF-8 sidecar 取得，不要寫死在 ANSI 腳本裡。

---

## 坑 4：python-pptx 需要 PIL，但 PIL 壞掉

**症狀：** `from pptx import Presentation` 直接 `ImportError`（鏈到 `PIL._imaging` / `PIL.ImageFont`）。

**解法：** 在 `import pptx` 前注入 stub，需涵蓋 **`PIL.Image`、`PIL.ImageFont`、`PIL.ImageDraw`** 三個子模組（python-pptx 的 text/chart 模組都會 import）。`Image` stub 要提供：
- `open()` 回傳含 `.size`、`.format`、`.mode`、`.info`（空 dict）的物件
- 用 `struct` 解 PNG（IHDR）與 JPEG（SOFn marker）header 拿真實尺寸（嵌圖時 python-pptx 需要）

完整可用版本見 [`scripts/pptx_pil_stub.py`](../scripts/pptx_pil_stub.py)。

---

## 坑 5：PowerPoint COM 自動化不穩

踩到的具體錯誤與解法：

| 錯誤 | 根因 | 解法 |
|---|---|---|
| `Cannot convert "True" to MsoTriState` | COM 列舉不吃 `$true/$false` | 用 `-1`（msoTrue）/ `0`（msoFalse） |
| `RPC_E_CALL_REJECTED (0x80010001)` | GUI 還在初始化就被狂呼叫 | `Start-Sleep` 等初始化 + 每張 slide 包 try/retry |
| `Presentations.Add()` 回 null | 同上，太早呼叫 | 加長初始 sleep；或改用 python-pptx |
| 中文標題在腳本內又亂碼 | 同坑 2 | 內容從 UTF-8 JSON 讀，腳本本體 ASCII |

**結論：** COM 路線脆弱。**首選 python-pptx + PIL stub**（坑 4 的解法），比 COM 穩得多、可重跑、跨機器一致。

---

## 坑 6：PPTX 檔案被鎖（`~$` owner file）

**症狀：** 重新產 PPTX 時 `PermissionError: [Errno 13]`，且看到 `~$xxx.pptx` 小檔（165 bytes）。

**根因：** PowerPoint（含預覽 handler / 殘留 handle）仍佔著檔案，即使 `Get-Process POWERPNT` 已查不到。

**解法：**
- 產出前先 `Stop-Process POWERPNT -Force` 並移除 `~$` lock。
- 程式內加 **fallback 檔名**：`try: prs.save(out) except PermissionError: prs.save(out_new)`，避免整個流程卡死。

---

## 坑 7：HTML 簡報排版 — 圖被裁切

**症狀：** slide 內的圖底部被切掉一截。

**根因：** 對 slide 容器設了固定 `height: calc(100vh - Npx)`，又在外層 `.inner` 設 `overflow:hidden`，內容超出就被裁。

**解法：**
- 圖容器用 `aspect-ratio` + `max-height:NNvh` + `object-fit:contain` 讓它**等比例自然縮放**，不要硬設高度。
- 該頁的 `.inner` override 掉 `max-height/overflow`（`max-height:none;overflow:visible`）。
- **不要**用固定 1920×1080 + transform scale 的舞台（小預覽面板會縮成超小）。

---

## 坑 8：HTML 圖用相對路徑會壞

**症狀：** 預覽面板看不到圖、檔案搬移後圖破。

**解法：** 一律 **base64 內嵌**（`data:image/jpeg;base64,...`）。先用 System.Drawing 壓成 JPEG（width≤1280, quality≈78）再轉 base64，5 張圖內嵌後 HTML 約 1.3–1.6 MB，可攜。HTML deck 的點擊翻頁 JS 記得把 `a` 標籤排除，內嵌連結才點得動。

---

## 坑 9：從 PowerShell 跑 git push 誤觸 `$ErrorActionPreference=Stop`

**症狀：** git 把進度寫到 stderr，在 `Stop` 模式下被當成 terminating error。

**解法：** 跑原生 git 前把 `$ErrorActionPreference` 暫存後設成 `Continue`，用 `& git push origin main 2>&1 | Write-Host`，再以 `$LASTEXITCODE` 明確判斷成敗，最後還原。

---

## 坑 10：把橫式 infographic 切成區塊呈現

**情境：** 一張很高（如 862×1825）的長 infographic 直接塞進 16:9 slide 會變很小。

**解法：** 用 System.Drawing 依 y 座標把原圖**裁成多個邏輯區塊**（`tokenization_b1..b4.png`），在 slide 用 2×2 grid 排版，每塊配中文小標導覽。或請使用者重生一張**橫式**版本取代。

---

## 一句話總結

> Windows + Anaconda + PowerShell 5.1 做簡報，最大的兩個敵人是
> **「壞掉的 PIL」**（→ System.Drawing 壓圖 + python-pptx stub 繞過）和
> **「PS 5.1 把 UTF-8 當 ANSI」**（→ 腳本全 ASCII + 中文走 UTF-8 sidecar）。
> 其餘都是這兩個根因的衍生症狀。
