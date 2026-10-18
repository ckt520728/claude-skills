# 目前狀態：持續進行

目標維持：可用的 Windows 桌面 App 與 iPhone 原生 App，支援近即時繁體中文／英文轉錄及中翻英，沒有訂閱依賴。

本輪開始時僅有需求及設計文件；本輪已新增程式碼、Windows portable 產物、iPhone 專案與實際推論證據。

| 驗收項目 | 證據與狀態 |
| --- | --- |
| Windows 可執行產物 | `dist/Voice2Txt/Voice2Txt.exe`，附 small 模型與 Python Runtime |
| 真實本機英文推論 | `verification/english-inference.json`；公開 JFK 音訊，base CPU int8 |
| 真實本機中文／翻譯 | `verification/chinese-small-inference.json`；Windows Hanhan 合成音訊 |
| 尾段、字典、資料保存與錯誤狀態 | 4 項核心測試及 `verification/desktop-integration.json`；UI 真實、麥克風及 decoder 模擬 |
| 打包版 UI 與三種模式 | `verification/packaged-zh.json`、`packaged-en.json`、`packaged-translate.json`；需以其中的 `ok`、`stage` 及 `desktop_ui` 欄位確認，不以建置成功代替 |
| 不依賴訂閱／付費 API | 桌面使用 bundled faster-whisper small；iOS 使用 WhisperKit CoreML。未使用付費 API；首次其他模型下載需要網路 |
| Typeless 參考 | 已以 7-Zip 靜態解包指定安裝檔，REA CLI 分析 ASAR；沒有執行安裝檔或使用原程式碼作為實作 |
| iPhone 原生專案 | `ios/Voice2Txt.xcodeproj`、SwiftUI 與 WhisperKit 0.9.4；**尚未編譯、簽署、安裝或實機驗證** |
| iPhone 專案結構 | 獨立 OpenStep parser 解析通過，參照的 Swift 檔案存在；見 `verification/ios-project-structure.json`。這不是 Xcode 編譯證據 |
| 2026-10-18 重建 GPU 版產物 | `verification/packaged-2026-10-18.json`：打包版 `-IncludeGpu`（small/medium/large-v3 + cuBLAS/cuDNN，7.8 GB）6 組 self-test 全部 `ok`。這只證明打包版各後端可執行；中翻英品質見下一列 |
| 中翻英固定語料比較 | `verification/quality-*.json`、`pipeline-small-ollama.json`：Whisper 直接翻譯在 small 1／3、medium 2／3（漏「明天」）、large-v3 2／3（漏「開會」）；small + 本機 Ollama gemma4 3／3。僅 3 句合成語料 |
| Ollama 預設與翻譯備援 | `verification/packaged-fallback-2026-10-18.json`：打包版 7 組 self-test 全部 `ok`。Ollama 正常時由 gemma4 翻譯；Ollama 異常時依序改用雲端備援、Whisper。Gemini／OpenAI 以刻意無效的金鑰測試，回 HTTP 400／401 後正確改用 Whisper。有效金鑰實測見 `verification/cloud-fallback-2026-10-18.json`（18 組，含 Whisper 時間）：OpenAI `gpt-6-luna` 在 low／medium／high 為 3.5–5.6 秒，9／9 由 OpenAI 翻譯。Gemini `gemini-3.8-flash` low 8–11 秒、medium 10–12 秒；high 一句 28 秒，另一句超過 30 秒逾時並正確改用 Whisper。單元測試 20 項通過；全新設定下 UI 自動選 `本機 Ollama` |
| 兩階段設計：Whisper 轉錄 + LLM 整理 | `verification/refine-small-2026-10-18.json`：5 個含贅詞／口誤／否定的組合，僅 Whisper 0／5、Ollama 5／5、OpenAI high 5／5、Gemini low 2／2（另 3 段 HTTP 429 額度不足）。`verification/packaged-chain-2026-10-18.json`：打包版 12 組全部 `ok`，Ollama → OpenAI → Gemini → Whisper 順序正確；Gemini 該輪因帳號額度回 429 而改用 Whisper |
| 真人／持續錄音／跨 App 輸入 | **尚未實測**；需要使用者配合說話及核對輸入位置 |
| 翻譯品質 | **尚未通過完整驗收**；small 在已測句中漏掉「開會」，base 誤譯更明顯 |

## 已解決問題

Windows 打包版曾在 CTranslate2 載入模型時出現 `0xc0000005`。Windows Application Event 指向產物內的 `MSVCP140.dll 14.27.29016.0`。以本機已有的 14.44 Runtime 更新產物副本後，固定音訊測試成功。`scripts/build_windows.ps1` 已納入此修正，不修改系統 DLL。

## 下一步

1. 在目標 Windows 機真人錄音，驗證各模式、快捷鍵、焦點保護、停止尾段與至少 30 分鐘運作。
2. 針對中文時間、否定與專有名詞擴充測試，改善漏譯。曾探測本機 Ollama，但固定翻譯請求在 45 秒逾時；目前未將未驗證的 LLM 路徑加入 App。
3. 取得 Mac／Xcode 環境後，解析相依套件、編譯 iPhone 專案、修正實際編譯問題、以使用者 Apple Account 簽署並完成實機驗收。

沒有可用 Mac／簽署的證據前，不能交付可安裝的 iPhone App。免費 Personal Team 需遵守 Apple 的 7 天 provisioning 限制；詳見 `ios/README.md`。整體 goal 保持 active。

另有 REA 完整 JSON 輸出仍進行中，已確認的 live tool session 為 `22682`；詳見 `verification/typeless-reference.md`。延續工作先 poll，不能僅因輸出耗時而重新啟動。
