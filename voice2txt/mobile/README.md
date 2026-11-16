# 手機網頁版（Windows 橋接）

不需要 Mac。在 Windows 雙擊根目錄 `啟動手機網頁版.cmd`，複製顯示的完整連結，在 iPhone／iPad Safari 開啟，使用「分享 → 加入主畫面」。

- Windows 必須保持開機、連網；Python 服務使用既有 small CPU 模型，Cloudflare Tunnel 提供 HTTPS。這不是 iOS 原生版，也不是手機離線推論。
- 支援繁中、英文、中翻英。每段最多錄製 90 秒，停止後轉錄。支援上傳音訊、編輯、複製、分享、匯出 TXT。切換 App 或鎖屏會停止錄音，不支援背景持續錄音。
- 可選桌機本機 Ollama 整理；預設關閉。不讀桌面 API keys，不使用雲端 LLM。
- 錄音經過 Cloudflare 通道，在桌機記憶體處理，不保存錄音；文字只留在當前頁面，離開前請匯出。
- 完整連結含配對碼。不要公開分享。配對碼只放在 URL fragment，載入後從網址列移除；裝置使用 localStorage 保存。若加入主畫面後未保留配對，貼入完整連結或配對碼即可。
- `mobile-runtime/手機連結.html` 與 `current-link.txt` 保存目前入口，`pairing.json` 保存配對碼；該目錄已排除版本控制。
- 這是臨時 Quick Tunnel 網址，重新建立 tunnel 後網址會改變，主畫面捷徑需重加。固定網址尚未設定。關閉命令視窗不會停止背景服務；停止方式見下方。

## 停止手機服務

在工作管理員找出本次 `run_mobile.py` 的 Python 程序與 `tools/mobile/cloudflared.exe` 程序後結束。透過啟動腳本建立的 PID 記錄在 `mobile-runtime/server.pid` 與 `tunnel.pid`；請先確認程序路徑再結束，勿結束其他 Python 工作。

## 驗證界線

`tests/test_mobile_server.py` 驗證配對、輸入限制、忙碌處理與靜態檔案範圍；固定 WAV 音訊測試只代表後端可執行。iPhone／iPad Safari 的麥克風、加入主畫面與背景切換需要實機驗收，不以電腦瀏覽器模擬代替。
