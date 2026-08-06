# Publish Lab Blog：實戰踩坑清單

這份清單來自 2026-08-06 發布〈藏在腦波底下的第二個節奏〉的實際工作階段。它補充 `SKILL.md` 的正常流程，專門處理「看似完成、其實尚未完成」的情況。

## P1：上一個工作階段的 repo 藏在暫存目錄

局部成果不一定在使用者目錄下的固定 checkout；本次位於 Claude scratchpad 的 `tmp/repo`。如果直接重 clone，可能遺失尚未提交的文章與三個註冊點。

**處理：**先用已知的 slug、標題或獨特數值搜尋 `.html`，找到候選 repo 後檢查 `git status --short --branch`、remote 與 diff。建立穩定工作目錄是後續改善方向。

## P2：PowerShell 預設編碼造成假性亂碼

Windows PowerShell 5 的 `Get-Content` 預設編碼可能把 UTF-8 繁中顯示成 mojibake。這不代表檔案真的損壞。

**處理：**對 HTML／Markdown 明確使用 `-Encoding UTF8`；用瀏覽器或 UTF-8-aware parser 判斷內容，而不是根據 console 顯示下結論。

## P3：`node --check` 不能直接檢查 `.html`

`node --check post.html` 會因副檔名而失敗，並非 JavaScript 語法錯誤。

**處理：**擷取所有 inline `<script>` 區塊，以 `new Function(scriptText)` 或暫存 `.js` 檔編譯。要確認檢查器本身成功執行，並輸出 script 數量。

## P4：PowerShell pipeline 可能掩蓋前段失敗

第一次 JS 檢查的 Node regex 因 quoting 出錯，但同一 command 後面的 HTTP 檢查成功，使整體 shell exit code 仍為 0。

**處理：**重要驗證分開執行，或在每一段後檢查 `$LASTEXITCODE` 並立即 `exit`。不要只看最後一個 command 的結果。

## P5：規格要求「數張 SVG」，現稿只有一張

文章已有三個 canvas，肉眼容易覺得圖像充足，但 skill 明確要求至少兩張彩色 SVG。

**處理：**發布前機械式計數 `<svg>`、`<canvas>`、`type="range"`，並確認開閉標籤成對。本次補上快／慢雙迴路控制器架構圖。

## P6：公開引用的年份與完整度漂移

Hsu 等人的 Human Brain Mapping 文章在 2022 線上先行、正式卷期為 2023；原稿沿用了 2022。另有兩筆已發表研究缺作者、卷期或 DOI。

**處理：**逐筆對照出版社或 PubMed 等主要來源，不以搜尋摘要或記憶中的 online-first 年份代替正式書目。這次修正為 `2023;44(3):914–926`，並補齊 Tsai 與 Liang 文獻。

## P7：沒有可連線瀏覽器，不能假裝做過視覺測試

browser runtime 回報空清單；既有 Chrome skill 的上一階段狀態不能保證新工作階段仍有連線。

**處理：**遵守 browser skill，不偷換其他控制介面。改做 inline JS 編譯、HTML 結構、DPR、reduced-motion、除零 guard、本機 HTTP 與正式 URL 驗證；交付時明示缺少最終視覺點擊測試。

## P8：`$HOME` 是 PowerShell 保留變數

用 `$home` 儲存首頁 URL 時，PowerShell 因變數不分大小寫而撞到唯讀 `$HOME`，後續 `Invoke-WebRequest` 甚至把本機 home path 當 URL。

**處理：**一律使用 `$siteIndexUrl`、`$publicPostUrl` 等任務專屬名稱，不覆用 HOME、PATH、PROFILE 等環境／系統變數。

## P9：push 成功不等於 GitHub Pages 已上線

commit 已推到 `main`，Vercel 也已成功，但 legacy GitHub Pages 長時間停在 `building`，新頁面仍回 404。當時 GitHub Status 回報 minor service outage，build 的 error 欄位為空且 commit 正確。

**處理：**分別驗證：repo contents、Vercel post、Vercel homepage card、Pages build API、GitHub Pages post。只有 URL 200 且首頁 slug count = 1 才算該部署面完成；外部 outage 應明確報告。

## P10：Drive 可讀不代表可寫

目標資料夾可以列出，但 raw HTML upload 回覆 403。

**處理：**保留 SHA-256 相符的本機快照，報告 connector 缺少寫入 scope；不要為了「看起來成功」而把檔案改傳到 Drive root。Drive snapshot 不是 source of truth。

## P11：`git diff --stat` 看不到 untracked 文章

首頁與 sitemap 出現在 diff stat 中，新文章因尚未追蹤而沒有列出，容易低估提交範圍。

**處理：**永遠一起看 `git status --short`，並以明確路徑 staging：文章、`index.html`、`sitemap.xml`。

## P12：提升權限啟動的測試 server 也要提升權限停止

本機 HTTP server 以提升權限啟動，普通 `Stop-Process` 被拒絕；而原 command 仍印出「stopped」，形成假成功訊息。

**處理：**停止後再次查 PID，只有 `Get-Process` 查不到才回報成功；必要時用相同權限層級清理。

## 完成條件

- 文章、首頁卡片、sitemap 三處註冊皆在同一 commit。
- 引用逐筆驗證；HTML UTF-8 正常。
- 至少 2 SVG、1 interactive canvas；本次實際為 2 SVG、3 canvas、6 sliders。
- inline JavaScript 可編譯，標籤配對，DPR/reduced-motion/除零 guard 存在。
- 至少一個正式部署面回傳 200，首頁 slug count = 1；其他部署面的狀態被明確記錄。
- 本機快照 hash 相符；Drive 成功或留下可行動的權限說明。
- working tree clean、commit 已推送、暫存 server 已停止。
