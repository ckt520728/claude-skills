# Typeless 參考檢查

指定來源：`D:\Downloads\Typeless-2.8.2-x64-Setup.exe`。未執行安裝程式。

7-Zip 靜態檢查顯示這是 NSIS Unicode 安裝包，內含 `$PLUGINSDIR/app-64.7z`；選擇性解包後取得 `resources/app.asar`。ASAR 為 306,999,609 bytes，SHA-256 為 `dc26918ff1e86816913f709767408d60ecf8b54c19d9acf63ad82632540ecd9f`。完整輸入指紋見 `typeless-artifacts.json`。

使用指定 REA fork，HEAD 為 `e762e32afbba3fd32532fd42a3f4fdcd05252ad3`，並閱讀其 `skill-src/reverse-engineer-anything/SKILL.md`。以 npm `rea-agents@6.0.0` CLI 分析原始 ASAR，沒有變更 Codex MCP 設定。

REA 統計包含 10,037 個 relevant files、5,546 個 parsed JavaScript files、6 個 parse failures；graph coverage 標示 incomplete。工具建立 application graph 與 Electron boundary reconstruction，產生 Evidence ID：

`ev_562aabc74749f85073d80f8fcefa522c9b53ecf113099eeefa694adbd62877d9`

已讀取的 Evidence header 確認 subject digest 與上述 ASAR 相同，provider 為 `rea-javascript-application`。**這是靜態分析，不證明功能執行、遠端模型、效能或安全性。** Ghidra 在 REA doctor 中可被找到；本次 ASAR 檢查不需要 native 反編譯，沒有宣稱已使用 Ghidra 追蹤原生 DLL。

完整圖包含大量第三方依賴，JSON 輸出非常大。CLI session `22682` 已正常結束；`scripts/summarize_rea.py` 已逐項解析完整 JSON，確認沒有截斷。摘要見 `typeless-rea-summary.json`，實際統計及限制見 `typeless-rea-findings.json`。輸出完整不代表分析 coverage 完整。原始 `typeless-rea.json` 已加入 `.gitignore`，未包含於 App 產物。

實作採本專案新寫的 Python／SwiftUI 程式碼、本機 Whisper 模型與自訂介面。沒有將 Typeless 的程式碼、圖示或服務放入 App。
