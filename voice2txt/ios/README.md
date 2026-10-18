# iPhone 版

此資料夾提供原生 SwiftUI 專案。**尚未在 Xcode 編譯或 iPhone 實測，不能視為可安裝完成品。**

支援的實作：繁體中文轉錄、英文轉錄、中文語音翻成英文、手機端 WhisperKit 推論、歷史紀錄、複製與分享。錄音每約 5 秒分段送入模型；停止時處理尾段。保持 App 在前景，音訊中斷或切換背景會停止錄音。使用 CoreML 模型，無需桌面主機。

## 在 Mac 建置與安裝

1. 將 `ios` 整個資料夾複製到 Mac。安裝 Xcode 16 或更新版本，開啟 `Voice2Txt.xcodeproj`。
2. 等待 Swift Package Manager 取得固定版本 WhisperKit `0.9.4` 及相依套件。
3. 在 target → Signing & Capabilities 選擇自己的 Personal Team，並將 Bundle Identifier 改成唯一值。
4. 接上 iPhone，依 Xcode 提示啟用 Developer Mode。選擇此 iPhone 後按 Run。
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
