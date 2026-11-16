# Voice2Txt 獨立語音筆記

在 Windows Chrome／Edge、iPhone Safari、iPad Safari 的目前裝置執行 Whisper，移除配對碼、Python API 與桌機常開需求。這是另外的獨立 PWA，既有 Windows portable App 與橋接版不受影響。

## 使用

1. 在各裝置開啟正式網站。私有網站首次需要登入同一個 ChatGPT 帳號。
2. iPhone／iPad 可用「分享 → 加入主畫面」。從主畫面入口再準備模型，避免 Safari 與主畫面入口快取分離。
3. v3 預設選 small（約 249 MB），按「下載／載入模型」，保持畫面開啟。若手機記憶體或速度不合適，可選 base（約 77 MB）或 tiny（約 41 MB），但準確度可能較差。
4. 模型載入後錄音或選擇音訊檔。每段最多 90 秒，建議先錄 10–20 秒測試速度。錄完後辨識，不是逐字串流。
5. 頁面與模型快取完成後，可切飛航模式測試離線。瀏覽器可能清除快取，屆時需重新下載。

## 架構與資料

- 靜態網站只提供程式、WebAssembly 與授權檔，不執行語音辨識。
- Dedicated Worker 執行 Transformers.js 3.8.1、ONNX Runtime Web 的單執行緒 WASM q8 Whisper。優先相容 Safari，不依賴 WebGPU 或 SharedArrayBuffer。
- tiny／base／small 模型固定至 `src/models.mjs` 指定的 Hugging Face revision；首次下載會連線 Hugging Face。音訊不會送到該站或桌機。
- MediaRecorder 錄音 → 裝置 AudioContext 解碼 → 聲道平均與 16 kHz 重採樣 → Whisper → 中文經 OpenCC `twp` 轉換。
- Service Worker 快取本站程式與 WASM，Transformers.js Cache API 快取模型。程式更新使用內容雜湊版本，不清除模型快取。
- 草稿與最近 20 段紀錄存在這台裝置 localStorage，沒有跨裝置同步。錄音不會自動保存，辨識前或失敗時暫存在頁面記憶體；使用者按「匯出這段錄音」才會匯出檔案。關閉頁面前請完成轉錄或匯出。
- 未提供 LLM 去贅詞與潤飾。中翻英直接使用 Whisper translate，小模型會誤字或漏譯，不能視為桌面 small + LLM 的等品質替代品。

## 開發與驗證

```powershell
npm install
npm run build
npm test
python -m http.server 8787 --bind 127.0.0.1 --directory dist
```

只部署 `dist/`；正式 Sites 專案識別在 `.openai/hosting.json`。部署依 Sites source workflow 完成 commit/push、打包與保存版本後發布；不得用開發伺服器網址替代固定入口。

單元測試確認重採樣長度、尾端、聲道平均、靜音與文字追加。瀏覽器需實際驗證模型推論、離線重開、英中模式與無音訊上傳。Chrome 離線測試不代表 iPhone／iPad 的實機通過：Safari 麥克風、記憶體、速度、主畫面與離線須另行驗收。鎖屏／切換背景會停止錄音，不提供背景持續錄音。

## v3 準確度與快取更新

新版入口為 `/quality.html`，頁首顯示「辨識品質更新 · v3」。程式、Worker、CSS 使用內容雜湊路徑，線上導覽優先讀取網路，失去網路才回退快取；避免升級後仍使用舊模型選項。草稿與歷史仍使用原儲存鍵，升級不刪除文字。

同一組合成語音（中文 3 句、英文 4 句）在 Windows Chrome 的比較：中文 50 個正規化單位中，tiny 有 8 個差異、舊 base q8 有 3 個、base 完整 encoder 有 4 個、small 完整 encoder 與 small q8 都有 2 個。small q8 每段約 9 秒，完整 encoder 約 11 秒；選 q8 以降低下載量與資源需求。**base 改用 fp32 encoder 沒有改善，因此沒有保留這個改動。**

四句合成英文在舊 base 與 small 均保留內容，正規化後 WER 為 0；這組語料未重現使用者的真人英文問題，不能宣稱實機英文已修復。中文 small 仍把「三份／四份」辨成「三分／四分」。所有錯誤率只適用這組語料；沒有真人、口音、噪音或手機品質證據，也沒有手機峰值記憶體量測。

測試原文、逐句結果與方法在根目錄 `verification/accuracy-comparison-2026-11-15.json`、`scripts/benchmark_pwa_accuracy.js` 與 `scripts/score_pwa_accuracy.py`。數字、標點與 mg/dL 的標準拼法正規化後計算中文 CER／英文 WER，不代表完整語意判定。

## v4 錄音不再被模型初始化鎖住

新版入口 `/recording`（檔案 `/recording.html`），頁首「錄音流程修正 · v4」。錄音與轉錄的就緒條件已分開：模型未就緒、下載中或載入失敗時，仍可開始／停止錄音；音訊先暫存在頁面，可匯出，模型就緒後自動轉錄。模式選擇不必等待模型完成。

先前回報的灰色按鈕，已用真正頁面與事件處理器重現：模擬 Worker 回報模型檔案完成，但不送出 ready，原版按鈕維持 disabled。修正後同一流程可以錄音與保留音訊；初始化超過兩分鐘會明確失敗，仍可錄音／匯出。另保留總下載 10 分鐘逾時。這只修正 UI 阻擋與錯誤處理，**沒有證明 iPad 為何沒有送出模型 ready，也沒有證明 iPad 的真實辨識引擎已可運行。**

「載入診斷」含階段、錯誤、能力旗標、模型與瀏覽器版本，不含錄音、轉錄或帳號憑證。它只在裝置顯示，使用者可按複製後提供協助診斷。模型下載完成與辨識引擎初始化完成是兩個不同狀態；請勿以錄音按鈕已可按代表轉錄引擎已修復。

回歸腳本：根目錄 `scripts/check_recording_readiness.js`（實際 DOM，模擬 Worker／麥克風）與 `scripts/check_recording_real_asr.js`（實際瀏覽器 Whisper，以模型載入前選取的合成音訊驗證自動轉錄）。
