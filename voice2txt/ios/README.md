# iPhone / iPad 版

此資料夾提供原生 SwiftUI 專案。**尚未在 Xcode 編譯或 iPhone / iPad 實測，不能視為可安裝完成品。**

支援的實作：繁體中文轉錄、英文轉錄、中文語音翻成英文、手機端 WhisperKit 推論、歷史紀錄、複製與分享。錄音最長 8 秒分段送入模型；停止時處理尾段。保持 App 在前景，音訊中斷或切換背景會停止錄音。使用 CoreML 模型，無需桌面主機。

## iPad 注意事項

- 專案為 iPhone + iPad 通用（`TARGETED_DEVICE_FAMILY = 1,2`）。iPad 支援四個方向；iPhone 支援直向與左右橫向（`INFOPLIST_KEY_UISupportedInterfaceOrientations_iPad` / `_iPhone`）。
- 在 iPad 的 regular 尺寸類別下，主編輯欄限制最大寬度 760 pt 並置中，避免全寬版面；尚未在實體 iPad 或模擬器確認實際外觀。
- 麥克風、背景切換與音訊中斷的行為與 iPhone 相同；iPad 分割畫面／Stage Manager 下的錄音行為尚未驗證。

## LLM 整理（選用，雲端）

App 內建與桌面版相同語意的第二階段：Whisper 轉錄後，可由雲端 LLM 去除贅詞、套用明確自我更正、補標點；中翻英模式同時翻譯。iOS 版沒有 Ollama，只提供雲端，並預設關閉（關閉時完全離線）。

- 在「設定 → LLM 整理（選用）」開啟主開關，再為各服務設定啟用、模型、推理強度與 API key。固定順序 Anthropic（預設 `claude-sonnet-5-5`／low）→ OpenAI（`gpt-6-luna`／high）→ Gemini（`gemini-3.8-flash`／low）；只有已啟用且有 key 的服務會加入，失敗者暫停 60 秒。
- 只送出 Whisper 轉錄文字，不送錄音；依用量計費，需自備 API key；無訂閱。API key 存放在 iOS 鑰匙圈，其餘設定存在 UserDefaults。
- 全部 LLM 失敗時：中文／英文保留 Whisper 原文；中翻英改用 WhisperKit `.translate` 再解碼一次（離線）。歷史紀錄會保留 Whisper 原文與產生該段的後端。
- 提示詞與桌面版 `voice2txt/translation.py` 的 `RULES`／`TASKS` 逐字相同，修改時須兩邊同步。雲端呼叫尚未以真實 API key 驗證。

## 在 Mac 建置與安裝

1. 將 `ios` 整個資料夾複製到 Mac。安裝 Xcode 16 或更新版本，開啟 `Voice2Txt.xcodeproj`。
2. 等待 Swift Package Manager 取得固定版本 WhisperKit `0.9.4` 及相依套件。
3. 在 target → Signing & Capabilities 選擇自己的 Personal Team，並將 Bundle Identifier 改成唯一值。
4. 接上 iPhone 或 iPad，依 Xcode 提示啟用 Developer Mode。選擇該裝置後按 Run。
5. 在 App「設定」下載並載入 `small` 模型。首次需要網路與數百 MB 空間；後續推論在手機處理。若資源不足，可改用 `base`，但中文／翻譯品質可能降低。

免費 Apple Account 可用 Personal Team 安裝測試，但 provisioning profile 在 7 天後到期，需要重新建置與安裝。App 本身沒有訂閱、付費 API 或帳號；Apple 的個人安裝限制仍適用。[Apple 官方說明](https://developer.apple.com/help/account/basics/about-your-developer-account)

CLI 編譯檢查（在 Mac）：

```sh
xcodebuild -resolvePackageDependencies -project Voice2Txt.xcodeproj
xcodebuild -project Voice2Txt.xcodeproj -scheme Voice2Txt -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
```

`project.yml` 是替代的 XcodeGen 定義；已提供 `.xcodeproj`，一般使用不需要安裝 XcodeGen。可用根目錄 `scripts/generate_xcode_project.py` 重建專案設定。

## 實機驗收（尚待執行）

- 繁體中文與英文各錄音 60 秒，確認內容、順序、延遲與尾段。
- 中翻英包含數字、否定句、時間及專有名詞，核對語意有無漏譯。
- 初次模型下載、離線重新載入、拒絕麥克風權限、音訊中斷、切換背景、長時間錄音。
- 關閉重開後歷史保留；複製、分享、刪除可用。
- 確認目標 iPhone 的記憶體用量與持續運行溫度。

此版本是獨立錄音 App；跨 App 輸入透過複製／分享，沒有 iOS 系統鍵盤擴充。
