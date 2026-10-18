# Voice2Txt

Windows 桌面版與 iPhone 原生版的語音輸入工具：繁體中文、English、中翻英，無訂閱。

**設計：兩階段處理。** 第一階段由 Whisper 在本機把語音忠實轉成文字。第二階段由 LLM 整理與去雜訊：去除贅詞與重複、套用說話者明確的口誤更正、修正錯字並加標點；中翻英模式同時翻譯。LLM 不得增刪資訊，「A，不是 B」這類否定會完整保留。原始轉錄一律保存供核對。完整說明見 [USER_MANUAL.md](USER_MANUAL.md)。

**Windows 已產生可執行檔並通過固定音訊推論；iPhone 尚待 Mac／Xcode 編譯、簽署及實機驗收。整體專案尚未完成。**

## Windows 使用

雙擊根目錄 `啟動桌面版.cmd`，或執行 `dist/Voice2Txt/Voice2Txt.exe`。移動程式時必須保留整個 `dist/Voice2Txt` 資料夾，不能只複製 exe。

1. 到「字典與設定」選擇模型、運算裝置與文字處理方式後載入（見下方「模型與 LLM 整理」）。產物已附模型，載入不需下載。
2. 選擇麥克風；可加入個人字典並儲存。
3. 回「即時語音」，選繁體中文、English 或中文 → English，按開始錄音。
4. 停頓約半秒時輸出一段；連續說話最長每 8 秒切一段，停止後等待尾段完成。可複製全文、匯出 UTF-8 TXT 或查看歷史。
5. `Alt + Shift + Space` 可在其他程式中開始／停止錄音。開啟「完成後貼入原視窗」後，只有原視窗仍有焦點時才會貼上。此功能會使用系統剪貼簿。

設定與歷史存於 `%LOCALAPPDATA%/Voice2Txt`，音訊僅在記憶體暫存，不保存錄音。繁體中文使用 OpenCC `s2twp`（LLM 整理後的中文也會再轉一次）；字典同時作為 Whisper 提示詞與 LLM 的優先拼法，不保證每個術語都能正確辨識。

### 模型與 LLM 整理

| 設定 | 選項 | 說明 |
| --- | --- | --- |
| Whisper 模型 | `base`、`small`、`medium`、`large-v3` | `base`／`small` 適合 CPU；`medium`／`large-v3` 建議搭配 NVIDIA GPU |
| 運算裝置 | `cpu`、`cuda` | `cuda` 需要 NVIDIA 顯示卡，以及 GPU 版產物內附的 cuBLAS／cuDNN；偵測到 GPU 時預設選 `medium` + `cuda` |
| 文字處理 | `Whisper + LLM 整理`、`僅 Whisper` | 前者三種模式都經過 LLM 整理（中翻英同時翻譯），畫面另顯示 Whisper 原始轉錄。後者直接輸出 Whisper 結果 |

尚未手動選過時，啟動時偵測到本機 Ollama 就預設使用 `Whisper + LLM 整理`（優先 `gemma4:latest`，Whisper 改 `small` + CPU）。需先安裝並啟動 [Ollama](https://ollama.com)，並下載本機模型。App 只連線 `127.0.0.1:11434`，會拒絕 cloud／遠端模型。

LLM 順序：① 本機 Ollama → ② OpenAI `gpt-6-luna`（`high`）→ ③ Gemini `gemini-3.8-flash`（`low`）→ ④ 只用 Whisper（繁中／英文用原始轉錄；中翻英用 Whisper 直接翻譯）。沒有 API key 的雲端服務自動略過；失敗的 LLM 暫停 60 秒後才重試，錄音不中斷。雲端模型需自備 API key 並依用量付費，只送出 Whisper 轉錄文字（不含錄音）。API key 以 Windows DPAPI 加密保存，或改用環境變數 `OPENAI_API_KEY`／`GEMINI_API_KEY`。

## 品質與目前限制

- 採分段近即時處理，不是逐字串流。延遲約為停頓／分段等待時間加上推論耗時；分段邊界可能影響連續語句。
- 處理跟不上錄音時會明確停止，並完成已排入的音訊。
- 中翻英固定語料（`tests/fixtures/quality-corpus.json`，合成音訊）結果：

  | 組合 | 中文 3 句通過 | 推論時間／句 | 問題 |
  | --- | --- | --- | --- |
  | small · CPU · Whisper 翻譯 | 1／3 | 約 2 秒 | 漏「開會」；醫院句時間錯亂 |
  | medium · CPU · Whisper 翻譯 | 2／3 | 約 5–6 秒 | 漏「明天」 |
  | medium · CUDA · Whisper 翻譯 | 2／3 | 約 0.4 秒 | 漏「明天」 |
  | large-v3 · CUDA · Whisper 翻譯 | 2／3 | 約 0.6 秒（首句 2.5 秒） | 漏「開會」 |
  | small · CPU + 本機 Ollama gemma4 | 3／3 | 約 2.4–3.9 秒 | 原文曾把「三份」轉成「三分」，譯文仍正確 |

  證據見 `verification/quality-*.json`、`pipeline-small-ollama.json`、`packaged-2026-10-18.json`（RTX 3060）。只有 3 句合成語料，不代表一般準確度；所有數字、否定、日期與重要語意仍需核對。
- 已驗證 Tk 視窗、模擬麥克風分段整合、固定音訊推論與打包版 self-test；尚未完成人聲麥克風、跨 App 貼上及長時間實測。
- LLM 整理（`tests/fixtures/disfluent-corpus.json`：3 句含贅詞、重複、口誤更正與否定的合成語音，共 5 個模式組合；`scripts/benchmark_refine.py`）：僅 Whisper 0／5；Ollama gemma4 5／5（約 0.6 秒）；OpenAI `gpt-6-luna` high 5／5（約 2–3.3 秒）；Gemini `gemini-3.8-flash` low 2／2（約 2.6 秒），另 3 段因帳號額度 HTTP 429 未回應。證據見 `verification/refine-small-2026-10-18.json`。初版提示詞曾讓兩個雲端模型把「禮拜一，不是禮拜二」當成口誤刪掉；已在提示詞中明確區分口誤更正與否定。
- 雲端備援翻譯實測見 `verification/cloud-fallback-2026-10-18.json`。Gemini 速度在同一天內差異很大（2.6 秒到超過 60 秒），超過 30 秒會逾時並改用下一個方式。
- 預設不依賴雲端 LLM；目前未實作口語自我修正／LLM 潤稿。介面與程式為本專案原創，沒有使用 Typeless 的程式碼、圖示或伺服器。

## iPhone

開啟 `ios/Voice2Txt.xcodeproj`。完整說明與未完成的實機驗收項目見 [ios/README.md](ios/README.md)。首次取得 CoreML 模型需下載；之後設計為手機端推論。

免費 Personal Team 安裝需定期重新簽署；Apple 說明目前為 7 天。[官方規則](https://developer.apple.com/help/account/basics/about-your-developer-account)

## 開發與驗證

Windows / Python 3.9 或更新版本：

```powershell
python -m venv .build-venv
.\.build-venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller==6.22.3
.\.build-venv\Scripts\python.exe -m unittest discover -s tests -v
.\.build-venv\Scripts\python.exe run_desktop.py
```

打包前需要 `models/whisper-small` 內的 `config.json`、`model.bin`、`tokenizer.json`、`vocabulary.txt`。來源為 [Systran/faster-whisper-small](https://huggingface.co/Systran/faster-whisper-small)，可用 `scripts/download_models.py small` 下載。執行 `scripts/build_windows.ps1` 建立包含 small 模型與 Runtime 的 portable 資料夾。完整建置套件版本記錄於 `verification/windows-build-requirements.txt`。

GPU 版：

```powershell
.\.build-venv\Scripts\python.exe -m pip install --target gpu -r requirements-gpu.txt
.\.build-venv\Scripts\python.exe scripts\download_models.py medium large-v3
powershell -NoProfile -File scripts\build_windows.ps1 -IncludeGpu > build.log 2>&1
```

`-IncludeGpu` 會另外打包 `gpu/nvidia`，以及已下載的 `medium`／`large-v3`，產物約 7.8 GB。GPU 函式庫只加入本 App 的 DLL 搜尋路徑，不修改系統設定。不要在 PowerShell 內用 `*>` 轉向建置輸出：PyInstaller 的 stderr 警告會被當成錯誤而中止。

打包版驗證：

```powershell
dist\Voice2Txt\Voice2Txt.exe --self-test out.json --audio tests\fixtures\quality-meeting.wav --mode translate --model medium --device cuda
dist\Voice2Txt\Voice2Txt.exe --self-test out.json --audio tests\fixtures\quality-negation.wav --mode translate --model small --llm-model gemma4:latest
dist\Voice2Txt\Voice2Txt.exe --self-test out.json --audio tests\fixtures\disfluent-zh-correction.wav --mode zh --model small --llm-model gemma4:latest --cloud OpenAI:high --cloud Gemini:low
```

輸出中的 `translator_chain`、`backend`、`fallback_warning` 顯示備援順序與該段實際使用的引擎。

輸出 JSON 中的 `ok`、`stage` 及 `desktop_ui` 欄位才是驗收依據，不以建置成功代替。失敗時 `stage` 停在最後完成的步驟。

測試資料與實測結果在 `verification`。英文音訊取自 [whisper.cpp 公開 JFK 範例](https://github.com/ggml-org/whisper.cpp/blob/master/samples/jfk.wav)；中文音訊以 Windows Hanhan TTS 合成。這些測試不代表一般使用者、臨床場景或所有 iPhone 的準確度。

主要依賴：[faster-whisper](https://github.com/SYSTRAN/faster-whisper)、[WhisperKit](https://github.com/argmaxinc/WhisperKit/tree/v0.9.4)、[OpenCC Python](https://github.com/yichen0831/opencc-python)、[sounddevice](https://github.com/spatialaudio/python-sounddevice)、選用 [Ollama](https://github.com/ollama/ollama)。
