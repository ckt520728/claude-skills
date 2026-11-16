# 目前狀態：依使用者要求暫停；行動版逐字稿仍無法產生

**最新回報：使用者在 v4 後仍無法產生逐字稿，要求停止並交接；收尾於 2026-11-16 完成。端到端問題尚未解決；下方發布、Chrome、模擬與固定音訊結果不能視為 iPad 驗收通過。** 本次只保存產物、撰寫 `WRAP_UP_2026-11-15.md` 與更新 `handoffs.md`；沒有繼續修改功能或重新部署。精簡交接封裝與雜湊清單在 `output/`，檔名保留工作日期 2026-11-15。

2026-11-15 v4 已發布，入口 https://voice2txt-independent.safecoconut4.chatgpt.site/recording ，commit `629baa2bd7b9cd4c138de6380af9caafba9fe284`。使用者已確認 iPad 按鈕為灰色。以實際 App DOM 模擬模型下載完成但未 ready，先重現原版 disabled；修正後可先錄音／暫存／匯出，ready 後自動轉錄，初始化兩分鐘逾時後仍可錄音且音訊保留。8 項檢查與實際瀏覽器 Whisper 的「先選取音訊、後載入模型、自動轉錄」測試通過。麥克風與 Worker 的 UI 回歸是模擬；真正 Whisper 測試使用合成檔案，沒有實機麥克風驗收。iPad 初始化停住的原因仍未知，不可宣稱其轉錄已恢復。

2026-11-15 v3 已部署至 https://voice2txt-independent.safecoconut4.chatgpt.site/quality.html ，source commit `380132acb99bedabdb94c2d63b005ef659bbd92e`。針對使用者回報獨立版中英文不準，新增 small q8（約 249 MB）並設為預設；8 項檢查通過。重現舊快取問題，改用具內容雜湊的程式路徑、強制檢查 SW 更新、線上導覽優先網路／離線回退快取。small 通過離線重開、模型重載與中文／英文轉錄。固定三句中文 CER：tiny 16%、舊 base q8 6%、base fp32 encoder 8%、small fp32 encoder 4%、small q8 4%；fp32 base 沒有改善，已撤回。選 small q8 而非更大的完整 encoder 版，因本語料結果相同、下載量較小、桌面推論較快（約 9 秒 vs 11 秒）。英文四句合成語料在 base/small 正規化 WER 均為 0，**未重現真人英文問題**。此為小型合成語料結果，不能視為手機實機驗收或一般準確度。新證據：`verification/accuracy-comparison-2026-11-15.json`、`accuracy-offline-small-2026-11-15.txt`、`accuracy-v3-deployment-2026-11-15.json`。

2026-11-15 新增獨立 PWA：`sites/voice2txt-independent/`，固定私人網址 https://voice2txt-independent.safecoconut4.chatgpt.site 。Whisper tiny／base q8 在目前裝置的瀏覽器 Worker 執行，不依賴桌機 API；Service Worker 快取程式與 WASM、Transformers.js 快取模型，草稿與最近 20 段文字存在裝置。Chrome 已完成中文／英文實際辨識、完全離線重開與模型重載後英文辨識，5 項新測試通過。tiny／base 皆在固定中翻英句誤譯，該功能標示試驗並要求核對。新架構的 iPhone／iPad 麥克風、記憶體、速度與加入主畫面尚未實機驗收，見 `verification/independent-pwa-2026-11-15.json`。既有橋接版已由使用者回報 iPhone／iPad 的繁中及英文可用，但不能視為獨立版驗收。

2026-11-15 新增 Windows 橋接手機網頁版（不是 Swift 原生版）：Safari 可用 HTTPS 連結開啟並手動加入主畫面，桌機須持續開機與連網。支援錄完後轉錄（每段 90 秒）、繁中／英文／中翻英、選用本機 LLM、複製／分享／匯出。Quick Tunnel 為臨時網址。`verification/mobile-local-2026-11-15.json` 與 `verification/mobile-public-2026-11-15.json` 記錄本機及公開 HTTPS 的固定音訊測試，包含 AAC/MP4 解碼；148 項測試執行成功（1 項略過）。手機實機錄音與主畫面安裝尚待使用者驗收，不能視為原生 iOS 完工。

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
| Anthropic（Claude）雲端 LLM 後端（2026-11-13） | 單元測試 30 項通過（含 Anthropic 請求格式、解析、refusal／截斷、鏈順序 Anthropic → OpenAI → Gemini；測試未連網）：`verification/audit-A1-2026-11-13.json`。UI 設定列、DPAPI 金鑰、環境變數備援、設定往返：`verification/desktop-anthropic-ui-2026-11-13.json`（`providers_in_ui`: Anthropic／OpenAI／Gemini，`ok` true）。打包版 self-test：`verification/packaged-anthropic-2026-11-13.json`。**沒有進行任何 live Anthropic 呼叫（2026-11-13 沒有可用的 API key，`anthropic_key_in_env` false），因此 Anthropic 的整理品質與延遲都沒有量測。** |
| iOS iPad 版面＋第二階段 LLM（2026-11-13） | `verification/ios-project-structure-2026-11-13.json`：5 個 `.swift`（含新增的 `Refiner.swift`）皆在 pbxproj 的 PBXFileReference、PBXBuildFile 與 Sources 建置階段，`TARGETED_DEVICE_FAMILY` 為 `1,2`，iPhone／iPad 方向鍵存在，`ok` true；稽核紀錄 `verification/audit-A2-2026-11-13.json`（T03 FAIL，缺陷由 T03b 修正）與 `verification/audit-C-2026-11-13.json`（T03b PASS）。**僅有結構與程式碼審查證據，仍未編譯、未在 Xcode／模擬器／實機執行；雲端整理未以真實 API key 驗證。** |
| 重建證據（2026-11-13，Anthropic 之後） | `verification/packaged-anthropic-2026-11-13.json`：`-IncludeGpu` 重建（`dist_bytes` 8,276,871,866，`msvcp140_version` 14.44.35211.0，exe 時間 2026-11-13 01:38:06）後 4 組 self-test 的 `ok` 皆 true（UI、zh、translate、en）；`--help` 的 `--cloud` 選項列出 `Anthropic:low`。zh 該組因 Ollama 冷啟動逾時 20 秒而退回 Whisper（`fallback_warning` 已記錄）。此次建置早於快捷鍵／系統匣功能。 |
| 最終重建證據（2026-11-13，快捷鍵／系統匣之後） | `verification/packaged-waveC-2026-11-13.json`：`-IncludeGpu` 重建（exit 0，173.0 秒；`dist_bytes` 8,276,858,735（1329 個檔案，T13 以 os.walk 重算）；exe SHA-256 `CB1FBD18CBC3EE07461334AEBB84DC07661B902EA7048ECD7C5F3C7775945E82`（T13 重算，前 12 碼 `CB1FBD18CBC3`），exe 時間 2026-11-13 07:37:34；`msvcp140_version` 14.44.35211.0；`icon_present` true）。打包版 4 組 self-test 的 `ok` 皆 true、`stage` 皆為 `completed`：UI（`desktop_ui` true）；zh（`backend` `Ollama gemma4:latest`，6.125 秒）；translate（`backend` `Ollama gemma4:latest`，12.5 秒）；en（`backend` `Whisper`，5.25 秒）。`--minimized` 啟動後觀察 8 秒，程序執行中且找到系統匣視窗（`tray_window_class_found` true）；第二份實例 0.41 秒退出（exit code 0）。`dist\Voice2Txt\使用者手冊.md` 與 `USER_MANUAL.md` 的 SHA-256 一致（`identical` true）。`--help` 列出 `--minimized` 與 `Anthropic:low`。限制：WM_CLOSE 送到系統匣視窗後程序 2 秒內未結束（僅關閉系統匣視窗），以 `taskkill /F /T` 結束；未注入 Right Alt（Typeless 執行中）；環境無 Anthropic key，translate 組的鏈不含 Anthropic，雲端實呼叫未驗證。 |
| 全域快捷鍵（Right Alt 口述、Right Alt + Right Shift 翻譯、舊 Alt+Shift+Space；真機檢查以 Left Alt／F24 代替 Right Alt（本機 Typeless 攔截 Right Alt）） | `verification/hotkey-hook-2026-11-13.json`（`scripts/check_hotkey_hook.py`，真實 WH_KEYBOARD_LL hook 與注入按鍵，`ok` true）：事件序列與預期相同、前景視窗不變、`keys_not_swallowed` true、注入 no-op 按鍵 4 次；吞鍵情境（含兩鍵）放開前不誤停。單元測試 80 項通過（`verification/audit-C4-2026-11-13.json`）。稽核鏈：`audit-C`（T07／T08 FAIL）→ `audit-C2`（T10 FAIL）→ `audit-C3`（T11 FAIL）→ `audit-C4`（T12 PASS）。以注入按鍵驗證，**尚未有真人按鍵與跨 App 實測**；Typeless 執行時會攔截 Right Alt。 |
| 系統匣、浮動指示器、登入自動啟動、`--minimized` | `verification/tray-indicator-2026-11-13.json`（`scripts/check_tray_indicator.py`，`ok` true）：系統匣圖示建立與刪除、點擊顯示視窗、關閉視窗縮到系統匣、指示器顯示時前景視窗不變（`indicator_foreground_unchanged` true；視窗樣式含 NOACTIVATE｜TOOLWINDOW）、Run 鍵啟用／停用往返（使用暫存鍵）、設定保存、`--minimized` 啟動時無主視窗。 |
| 單一執行個體 | `verification/single-instance-2026-11-13.json`（`scripts/check_single_instance.py`，`ok` true）：第二個執行個體 0.34 秒內結束（exit code 0），系統匣視窗仍只有 1 個，第一個視窗被顯示；結束後無殘留程序與 mutex。後續稽核 `verification/audit-C2-2026-11-13.json`（T10 FAIL，其餘缺陷由 T11／T12 修正）、`verification/audit-C3-2026-11-13.json`、`verification/audit-C4-2026-11-13.json`（T12 PASS）。 |
| 稽核紀錄（JEV，2026-11-13） | `audit-A1`：T01／T02 PASS；`audit-A2`：T03 FAIL → T03b；`audit-C`：T03b PASS、T07／T08 FAIL → T10；`audit-C2`：T10 FAIL → T11；`audit-C3`：T11 FAIL → T12；`audit-C4`：T12 PASS。檔案皆為 `verification/audit-*-2026-11-13.json`。選單列抑制（單獨 Alt 不啟動功能表）：`verification/audit-C-2026-11-13.json` 以 Left Alt 代理測得 10–80 毫秒短按 0／38 次啟動，0 毫秒瞬間合成按鍵 3／8 次啟動（量測於 audit-C（T07 版本），T10–T12 之後尚未重測）；屬盡力而為。 |
| 隨便問與前景脈絡（wave D，T14／T17） | `verification/context-capture-2026-11-13.json`（`scripts/check_context_capture.py`，`ok` true）：前景視窗（標題 `V2T-context-check`）中選取「Voice2Txt 選取測試 12345」，以 Ctrl+C 擷取的結果與選取相符（`selection_matches` true），擷取後剪貼簿還原為原本的文字（`clipboard_restored` true，`had_other_formats` false）；不擷取時 `selection` 為空字串。`verification/wave-d-2026-11-13.json`（`scripts/check_wave_d.py`，`ok` true，19 項 `results` 全為 true）：隨便問會話（LLM 以測試替身代替，收到脈絡與選取文字）、歷史 `ask` 篩選、隨便問不計入洞察、前景是 Voice2Txt 自己時不擷取、無 LLM 時狀態列顯示「沒有可用的 LLM，顯示原始轉錄」且不貼回。真實本機 LLM 的抽查見 `verification/audit-E-2026-11-13.json`（gemma4:latest，翻譯／改寫／回答 7／8，1／8 只複誦問題）。**沒有 UI Automation 欄位擷取**，只有視窗標題、程式名稱與 Ctrl+C 複製的選取文字。 |
| 快捷鍵貼回、合併貼上、窄範圍吞鍵（wave D，T17／T20／T21） | `verification/wave-d-2026-11-13.json` 的跨程序檢查：以 `LeftAlt+VK0x86` 當隨便問按住 3.0 秒，錄音在放開前沒有中斷（`recording_still_on_before_release` true，`ask_stop_seconds_after_press` 3.0），仍取得選取文字，目標視窗收到的 C 鍵不含 Alt；三段文字合併成單一貼上（`merged_paste_text` 為 `SEG-ONE`／`SEG-TWO`／`SEG-THREE` 以換行相接，`ctrl_v_count` 1），貼後剪貼簿還原；剪貼簿為非文字時略過擷取且不注入任何按鍵（`skip_path_injected_keys` 為空）。`verification/hotkey-hook-2026-11-13.json`（`scripts/check_hotkey_hook.py`，`ok` true）的 `swallow_rule`：把 `LeftAlt+Space` 設為隨便問，對照組按住期間前景視窗系統選單旗標為 12，啟用 App 後為 0（放開後也是 0）；單獨按 Space 仍到達視窗；修飾鍵未被吞（`alt_not_swallowed` true）；hook 的回傳路徑恰為兩條（吞鍵、`CallNextHookEx`）。以注入按鍵驗證，**尚無真人按鍵實測**。 |
| 靜音其他音訊（wave D，T15） | `verification/audiofocus-2026-11-13.json`（`scripts/check_audiofocus.py`，`ok` true）：啟動一個會發聲的子程序，找到它的音訊工作階段（`child_session_found` true，`sessions_seen` 2）；靜音前 `GetMute` false、靜音期間 true、`restore` 後 false，`errors` 為空。`verification/wave-d-2026-11-13.json` 另證實錄音停止、處理速度不足自動停止與關閉程式時都會還原。測試對象是測試用子程序，不是真實 App。強制結束程式時無法還原，Windows 會記住各 App 的靜音狀態，需到音量混音程式取消靜音（已寫入手冊）。 |
| 其他 wave D 功能（T16／T17） | `verification/wave-d-2026-11-13.json`（Tk 視窗自動化，非真人操作）：洞察分頁（統計與畫面標籤一致、方格圖已繪製；字數 = 中日韓字元 + 拉丁單字，節省時間以每分鐘打字 40 字估算）、外觀三種選項與設定保存、保留期限清理（`forever_keeps`、`one_week_prunes`、啟動時清理）、自動新增字典（候選、加入、合併進詞彙並送進 Whisper、忽略會記住）、互動聲音設定被遵守、舊設定檔載入後各新鍵取得預設值、舊的隨便問預設遷移為 `RightAlt+RightCtrl` 且自訂值保留。 |
| wave D 稽核鏈（2026-11-13） | `verification/audit-E-2026-11-13.json`：T14／T15／T16 PASS，T17 FAIL（隨便問擷取前未放開 Alt；預設 `Right Alt + Space` 會打開系統選單；連續貼上遺失或重複）→ T20。`verification/audit-E2-2026-11-13.json`：T20 FAIL（擷取前以注入放開按鍵後，約 1.2 秒被實體取樣誤判為放開，會中斷按住的隨便問）→ T21。`verification/audit-E3-2026-11-13.json`：T21 PASS，`replan_needed` 為空。單元測試數：audit-E 117 項、audit-E2 129 項、audit-E3 133 項，皆通過。E3 的 minor：不會自動重複的鍵被吞後，1.2 秒就被視為放開，已由 T22 修正：吞鍵逾時只在看過該鍵的自動重複後才套用，`hotkeys_version` 以安全轉型讀取；單元測試 136 項皆通過（見 `verification/audit-F-2026-11-13.json`；`verification/hotkey-hook-2026-11-13.json` 只記錄 hook 實測，不含測試數）。audit F（`verification/audit-F-2026-11-13.json`）：T22／T18／T18b／T19 各 PASS，但 overall FAIL，原因為 D1（`capture_selection` 目標程式晚寫入剪貼簿時，使用者剪貼簿被覆蓋卻回報成功）→ T23。audit G（`verification/audit-G-2026-11-13.json`）：T23／T19b PASS，overall PASS，4 項 minor（G1–G4）→ T24。T24 關閉 G1–G3（監看程式還原前先確認剪貼簿擁有者行程為目標程式；無選取文字不再誤報逾時；延遲檢查記錄所用逾時），單元測試 142 項；由 planner 自行以 hash 與測試驗證，不再另開稽核。 |
| wave D 打包版（最終，T19c） | `verification/packaged-waveD3-2026-11-14.json`（T24 之後重建；取代 `packaged-waveD-2026-11-13.json` 與 `packaged-waveD2-2026-11-13.json`，兩者皆標為 superseded）：建置 exit 0（171.0 秒，PyInstaller ERROR 行 0）；`dist` 共 8276931737 位元組、1330 個檔案；`Voice2Txt.exe` SHA-256 前 12 碼 `1ddef70343db`（與 `Get-FileHash` 一致）；內含 `msvcp140` 為 14.44.35211.0；圖示檔 `voice2txt.ico` 存在（`icon_present` true）。打包版五組 self-test 皆 exit 0、`stage` 為 `completed`、`ok` true：(a) 僅 UI；(b) `zh`，backend `Ollama gemma4:latest`；(c) `translate` 加 `--cloud Anthropic:low`（環境無 Anthropic key），backend `Ollama gemma4:latest`；(d) `en`，backend `Whisper`；(e) `ask`，沒有可用 LLM，backend `Whisper`，警告「沒有可用的 LLM，顯示原始轉錄」。`--minimized` 啟動 8 秒後仍在執行且找到系統匣視窗；第二份執行個體 0.39 秒 exit 0。`--help` 列出 `ask`、`Anthropic:low`、`--minimized`。`USER_MANUAL.md` 與 `dist` 內手冊 SHA-256 一致（`identical` true）。PYZ 內 `context` 模組含 `clipboard_owner_pid`（`has_clipboard_owner_pid` true）。未嘗試對打包版注入 Right Alt（Typeless 執行中）。 |
| 真人／持續錄音／跨 App 輸入 | **尚未實測**；需要使用者配合說話及核對輸入位置 |
| 翻譯品質 | **尚未通過完整驗收**；small 在已測句中漏掉「開會」，base 誤譯更明顯 |

## 已解決問題

Windows 打包版曾在 CTranslate2 載入模型時出現 `0xc0000005`。Windows Application Event 指向產物內的 `MSVCP140.dll 14.27.29016.0`。以本機已有的 14.44 Runtime 更新產物副本後，固定音訊測試成功。`scripts/build_windows.ps1` 已納入此修正，不修改系統 DLL。

## 下一步

1. 使用者提供 `ANTHROPIC_API_KEY`（及選用的 OpenAI／Gemini key）後執行 `scripts/benchmark_refine.py`，取得 Anthropic 的真實整理品質與延遲；在此之前不得宣稱 Anthropic 已驗證。
2. 在目標 Windows 機真人錄音：各模式、快捷鍵（按住說話／短按切換）、焦點保護、貼回、系統匣常駐，以及至少 30 分鐘運作。
3. wave D 稽核已完成（audit F、audit G，見上方稽核鏈）；最終打包證據為 `verification/packaged-waveD3-2026-11-14.json`，不再另開稽核。
4. 取得 Mac／Xcode 環境後，解析相依套件、編譯 iPhone／iPad 專案、修正實際編譯問題、以使用者 Apple Account 簽署並完成實機與 iPad 驗收，再測試選用的雲端 LLM 整理。
5. 針對中文時間、否定與專有名詞擴充中翻英測試語料，改善漏譯（目前固定語料只有 3 句合成語音）。
6. 與 Typeless 的剩餘差距（對照見 `verification/typeless-feature-inventory-2026-11-13.md`）：wave D 已涵蓋隨便問、前景 App 脈絡（視窗標題、程式名稱、Ctrl+C 選取文字）、快捷鍵貼回、自動字典、互動聲音、靜音其他音訊、洞察、保留期限與外觀；仍不同的是：沒有 UI Automation 的輸入欄位擷取、不會從其他 App 內的修改學習字典（只學 Voice2Txt 編輯區的修改）、沒有雲端同步。
7. 在目標 Windows 機真人驗證 wave D：隨便問在實際 App（含 Word／瀏覽器／終端機）中的選取擷取與貼回、剪貼簿還原、靜音其他音訊對真實 App 的效果、含 Alt 的組合在各 App 是否仍會打開選單。

## 已知限制

- 快捷鍵：某個鍵的 key-up 若在第一次 20 毫秒取樣前就遺失，該鍵會被視為仍按著，直到使用者再按它一次。
- 快捷鍵：真正遺失 key-up 後的 1.5 秒內再按同一個鍵，會被忽略一次（已接受的取捨，見 `verification/audit-C4-2026-11-13.json`）。
- Typeless 執行時會攔截 Right Alt（App 會顯示警告，需改設其他組合或關閉 Typeless）。
- 快捷鍵（E3 的 minor）：被吞掉的非修飾鍵若不會自動重複，過去被吞後 1.2 秒就被視為放開，已由 T22 修正（吞鍵逾時只在看過自動重複後才套用）。
- 隨便問的選取文字擷取用 Ctrl+C：剪貼簿含非文字內容時會略過擷取（狀態列說明），貼回後只還原剪貼簿文字，圖片等其他格式無法還原。
- 隨便問擷取選取文字時，目標程式必須在約 0.9 秒內回應 Ctrl+C，逾時則該次不使用選取文字（回傳 `('', False)`，狀態列提示）；逾時後背景 watcher 監看 2 秒，目標晚寫入剪貼簿時自動還原原本文字（延遲 700 ms 的實測見 `verification/context-capture-2026-11-13.json`），使用者在這段時間另外複製則不動剪貼簿（兩次寫入不還原；且 watcher 還原前會檢查剪貼簿擁有者視窗的 pid 必須等於擷取時目標視窗的 pid，不同或取不到就不還原；`no_selection_user_copy` 情境實測使用者自己的複製未被覆蓋）。證據中「延遲 700 ms」情境為重現原缺陷，刻意使用逾時 0.4 秒（JSON 的 `timeout_used` 欄位記錄各情境實際逾時），出貨預設為 0.9 秒。此缺陷由 `verification/audit-F-2026-11-13.json` 的 D1 發現並由 T23 修正；audit F 之後尚未重新稽核。
- 靜音其他音訊：程式被強制結束時無法還原其他 App 的靜音；Windows 會記住各 App 的靜音狀態，需到音量混音程式取消靜音。
- wave D 功能只以模擬按鍵、Tk 自動化與測試子程序驗證；打包版已有 self-test 證據（`verification/packaged-waveD3-2026-11-14.json`），但沒有真人、真實麥克風或跨 App 證據。
- iOS 仍未編譯；沒有任何 Xcode 編譯或實機證據。
- 尚未驗證任何 live Anthropic 呼叫（沒有 API key），Anthropic 品質與延遲皆無量測。

沒有可用 Mac／簽署的證據前，不能交付可安裝的 iPhone App。免費 Personal Team 需遵守 Apple 的 7 天 provisioning 限制；詳見 `ios/README.md`。整體 goal 保持 active。

另有 REA 完整 JSON 輸出仍進行中，已確認的 live tool session 為 `22682`；詳見 `verification/typeless-reference.md`。延續工作先 poll，不能僅因輸出耗時而重新啟動。
