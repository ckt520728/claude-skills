# Handoffs

Session-to-session handoff log. Newest entry first. Each entry: date, what was done, current state, next steps, open risks.

---

## 2026-11-16 — 本機網址 127.0.0.1:8787 無法使用的原因與 v5 修正

使用者回報 `http://127.0.0.1:8787/recording.html` 不能用。證據 `verification/recording-v5-local-2026-11-16.json`。

- **直接原因**：8787 沒有任何伺服器在執行（curl 回 000）。先前只有測試 agent 手動跑 `python -m http.server` 時才可用。新增 `scripts/serve_pwa.py`（HTML／sw.js 送 `Cache-Control: no-cache`、WASM 正確 MIME）與根目錄 `開啟本機網頁版.cmd`（雙擊啟動並開啟網頁）。127.0.0.1 只代表這台電腦，iPhone／iPad 不能用這個網址。
- **v4 程式缺陷**：錄音前 `await audioContext.resume()` 且無逾時。沒有使用者手勢時 resume() 永遠不回應（實測 3 秒仍 pending），頁面卡在「正在啟用麥克風」且所有按鈕停用。v5 錄音不再建立／等待 AudioContext，getUserMedia 加 60 秒逾時；解碼改用 16 kHz OfflineAudioContext（30 秒逾時）。真人點擊在桌面 Chrome 的 v4 仍可錄音；iPad 是否因此失敗**未驗證**。
- **桌面 Chrome（tiny）v5 結果**：上傳中文 1.8 秒「今天下午4點開會,請記得帶研究報告」（v4 為「戴」）；英文 JFK 正確；中翻英錯誤（tiny 不可用）；真人點擊錄音全流程成功。npm test 8/8。
- **未做**：真麥克風、iPad／iPhone 實機、v5 尚未部署到 chatgpt.site（正式站仍是 v4，部署需 Sites 工具與憑證）、子專案 git 因檔案擁有者是另一個 Windows 帳號（dubious ownership）未 commit。
- **尚未處理的使用者要求**：推送到 GitHub `ckt520728/claude-skills` 與寫 Obsidian 收尾文件（使用者後續改為本項目，尚未執行）。

---

## 2026-11-16 收尾（2026-11-15 工作）— 使用者要求停止：逐字稿仍無法產生，尚未解決

**這是最新有效狀態，優先於下方先前的成功測試與發布敘述。** 使用者在 v4 後明確回報「The app still cannot generate transcripts」，並要求停在這裡、保存 `D:\2026 Voice2Txt` 的產物、寫收尾文件與交接。目前工作依使用者要求停止，不得自行續做修復、模型下載、部署或變更服務存取權。

先讀 `WRAP_UP_2026-11-15.md`，其中整理產物、各平台驗證邊界、實際陷阱與恢復工作後的順序。精簡來源／證據封裝在 `output/Voice2Txt-handoff-2026-11-15.zip`，存在性／大小／SHA-256 與 ZIP CRC 結果在 `output/HANDOFF_ARTIFACTS_2026-11-15.json`。完整來源、部署 tar、測試與截圖仍保留原本本機位置；封裝刻意排除憑證、mobile-runtime、node_modules、GPU/runtime 與大模型。

最新正式來源仍為子專案 `sites/voice2txt-independent/` 的 `629baa2bd7b9cd4c138de6380af9caafba9fe284`；正式私人入口 `/recording`，v4。v4 只解除錄音被 ready 鎖住、保留 pending 音訊並提供載入診斷。**不能說 iPad 已能產生逐字稿或根因已修復。** 8 項檢查、模擬麥克風／Worker 回歸與 Chrome 合成檔案推論，只證明各自測試範圍；最新使用者失敗回報是目前端到端結果。

尚缺 iPad/iPadOS、頁首版本、v4 診斷與具體失敗階段；不能把缺少 ready、記憶體、WASM 或 AudioContext/getUserMedia 等可能原因寫成已確診。下次恢復時先取得裝置端證據並建立真正 Safari 的失敗回饋，避免再次只修 UI、換模型、重貼網址或要求反覆下載。雲端錄音／付費服務的偏好尚未確認，不能自行啟用。

本次收尾不改功能、不重跑模型、不重新部署；只更新文件與保存交接產物。

---

## 2026-11-15 — iPad 灰色錄音按鈕：v4 解除模型依賴

使用者補充：頁面可開、已下載，Start Recording 灰色不能按。已發布 v4 `/recording`，source commit `629baa2bd7b9cd4c138de6380af9caafba9fe284`，正式證據 `verification/recording-v4-deployment-2026-11-15.json`。不要只叫使用者再下載。

重現：`scripts/check_recording_readiness.js` 使用真實 App 頁面與事件，模擬 Worker 送模型檔案 done 但不送 ready，v3 按鈕仍 disabled，紅燈結果在 `recording-readiness-red-2026-11-15.txt`。依診斷 skill 的回饋迴圈修正：錄音/upload/模式不再依賴 ready 或 loading；模型就緒之前保留 pending Blob，可匯出；ready 後若沒有錄音／起始麥克風動作則自動轉錄。初始化兩個 ONNX 檔案完成後超過兩分鐘明確失敗；下載保留10分鐘逾時；失敗不鎖錄音、不丟待轉錄 Blob。新增本機顯示與手動複製診斷（版本、階段、錯誤、能力與 UA，不含錄音／文字）。

驗證：綠燈腳本含錄音、停止、保留、ready 自動轉錄與用 Playwright clock 推進兩分鐘後的逾時保留；mic/Worker 皆模擬，不能作 iPad 實機驗收。`check_recording_real_asr.js` 另以實際 Chrome + tiny q8，先選合成中文音訊再載入模型，實際成功轉錄；未測真實麥克風。8 項 source/build 檢查全過。根本原因只確認 UI 把錄音綁定模型 ready；**iPad 為何沒有 ready（慢、失敗、記憶體或 WASM 相容性）仍未確立**。請用新版複製診斷追查，不要聲稱辨識引擎已修復。

正式網址維持私人；新入口 avoids 舊 HTML 快取，頁首「錄音流程修正 · v4」。使用者先試點開始錄音，不必為了啟用按鈕再下載；若停止後仍等待模型，請其提供「載入診斷」。音訊只在頁面暫存，關閉前需完成轉錄或手動匯出。

---

## 2026-11-15 — iPad 失敗回報，等待裝置端錯誤

使用者回報 `https://voice2txt-independent.safecoconut4.chatgpt.site/quality` 在 iPad 失敗，即使重複下載。已詢問失敗階段（登入／模型載入／錄音轉錄），尚未收到錯誤文字或型號/iPadOS；不能視為已修復。

已做正式站唯讀 HTTP 檢查，證據 `verification/ipad-access-diagnostic-2026-11-15.json`：未登入時三個入口皆為 401 ChatGPT gate。使用既有 Sites token 驗證後，`/quality` 與 `/` 為 App HTML 200；`/quality.html` 為 307 Location `/quality`。**使用者的 `/quality` 是正確入口，少 `.html` 不是原因。** App JS、Worker、manifest、SW、WASM 均 200，WASM MIME 為 application/wasm。這只證明 HTTP 檔案可取，不代表 iPad 執行或 Hugging Face 模型下載成功。網站仍為 owner-private、version 3，沒有更動存取權或生產程式。

檢查工具 `scripts/check_site_routes.mjs` 由隱藏 stdin 接受既有 `get_site` token，僅送到本站的 `OAI-Sites-Authorization: Bearer ...`，redirect manual，不保存 token。初次未加 Bearer 前綴而收到 401，已修正並取得上述結果；不要誤用那次 401 判斷網站不可用。下一步必須取得 iPad 的實際錯誤與版本，再分辨登入、模型下載、WASM 相容性、記憶體或錄音問題；不要再僅重貼網址或要求重複下載大模型。

---

## 2026-11-15 — 獨立 PWA v3 準確度與舊快取修正

使用者回報新獨立版繁中／英文不準，要求繼續處理。本次已發布 v3，入口 https://voice2txt-independent.safecoconut4.chatgpt.site/quality.html ，source commit `380132acb99bedabdb94c2d63b005ef659bbd92e`，正式部署紀錄 `verification/accuracy-v3-deployment-2026-11-15.json`。網站仍私人存取；沒有修改桌面或舊橋接引擎。

結論：預設升為多語 Whisper small q8（約 249 MB），保留 base/tiny 供低資源裝置選用。實際比較後，base fp32 encoder 沒有改善（中文 4/50 字元差異 vs q8 3/50），故撤回；small fp32 encoder 與 small q8 都是 2/50，選較小且較快的 q8。tiny 為 8/50。差異均在標點、數字格式正規化後計算，僅中文 3 句合成語料。四句合成英文在 base 與 small 正規化 WER 都為 0；沒有重現使用者真人英文錯誤，不能聲稱英文已修復。small 中文仍把「三份／四份」寫成「三分／四分」。原始結果與方法：`verification/accuracy-*.txt`、`accuracy-comparison-2026-11-15.json`、`scripts/benchmark_pwa_accuracy.js`、`scripts/score_pwa_accuracy.py`；新增 `tests/fixtures/accuracy-corpus.json` 的 3 句 Zira 合成英文。

快取：曾連續重新載入兩次仍顯示舊模型選項。已改為 hash 命名 app/worker/CSS、獨立 quality.html 與 manifest-quality.webmanifest、SW install 使用 cache reload、線上導覽優先網路、離線回退快取；client 使用 updateViaCache none 並 update。8 項檢查通過，保留原 localStorage 草稿與歷史鍵。small 也已在 navigator.onLine=false 時重開、重載模型、完成中英文各一段，見 `accuracy-offline-small-2026-11-15.txt`。390px 無水平溢出，截圖在 `output/playwright/accuracy-v3-offline-390.png`。

限制：所有速度（small q8 每段約 9 秒、完整 encoder 約 11 秒）是 Windows Chrome，不是手機。沒有手機峰值 RAM、真人口音、噪音、主畫面新版錄音驗收。已向使用者詢問模型與「原句→辨識結果」，以及是否接受雲端錄音辨識／按用量計費；尚未收到回覆，不得自行上傳其錄音或啟用付費服務。

執行注意：System.Speech 合成在 sandbox 內 SelectVoice 曾回 NullReference，正常升權後成功。期間自動核准審查因使用額度失敗、動作未執行；使用者要求 continue 後，正常重試核准並通過，沒有繞過。新 Source credential 經隱藏 stdin 傳入 Sites helper，未保存 token。發佈 archive：`output/voice2txt-independent-v3.tar.gz`。

---

## 2026-11-15 — 跨裝置獨立 PWA

使用者已在 iPhone／iPad 確認舊橋接版繁中／英文錄音，但要求解決 Windows 需持續開機的限制。本次另建 `sites/voice2txt-independent/` 靜態 PWA，沒有更動既有 Windows 引擎或手機橋接服務。固定私人網址：https://voice2txt-independent.safecoconut4.chatgpt.site 。每台裝置首次需登入同一 ChatGPT 帳號並下載自己的模型，Safari 可加入主畫面；根目錄新增「開啟獨立網頁版.cmd」。

架構：Transformers.js 3.8.1 + ONNX Runtime Web 單執行緒 WASM q8；Dedicated Worker 內執行 Whisper，tiny/base revision 固定在 models.mjs；OpenCC cn2t/twp 輸出繁中。模型從 Hugging Face 下載，程式與 WASM 在 Sites，不上傳錄音、不呼叫 Windows、不讀 API keys。Service Worker 與模型 Cache API 支援離線重載。草稿與 20 段紀錄存在裝置 localStorage；無跨裝置同步，無 LLM 整理，錄完才辨識。

證據：`verification/independent-pwa-2026-11-15.json`、`output/playwright/independent-offline-390.png`。5 項音訊處理測試通過；Chrome 已在 navigator.onLine=false 時重開頁面、重載 tiny、執行英文推論（2.2 秒）。tiny/base 中文把「帶」辨為「戴」；中翻英兩者都明顯誤譯，因此介面與結果明確標示為試驗。所有時間是 Windows Chrome，不能當手機效能。新架構尚未經 iPhone／iPad 實機驗收、也未編譯 Swift 原生版。

Sites project_id 與 Git 位於子專案 `.openai/hosting.json` 與 `.git`；不要把它誤當根資料夾 Git。部署請依 Sites skill，用目前子專案來源與已驗證的 archive 進行。Git Windows schannel 起初失敗，僅針對 workflow process 設 `GIT_CONFIG_COUNT=1` / `GIT_CONFIG_KEY_0=http.sslBackend` / `GIT_CONFIG_VALUE_0=openssl` 後成功；沒有停用 TLS 驗證。雲端 repo credential 只留 session memory 並從隱藏 stdin 傳入 helper，不寫檔。品質提醒修訂需以最新 commit/deployment 為準。

下一步：使用者在新網址完成 iPhone／iPad 的 tiny 載入、繁中／英文各 10–20 秒，關桌機後重試，並在主畫面入口完成快取後測飛航模式。若手機記憶體或速度不合需求，再評估原生 CoreML App 的雲端建置與簽署；目前不能宣稱所有裝置已通過。

---

## 2026-11-13 — JEV wave D: 隨便問 (ask-anything), foreground context, auto dictionary, sounds, mute-others, insights, retention, appearance

**Roles (JEV).** Same as the previous entry: planner = main session, executors = Sonnet (`claude-sonnet-5-5`), independent Opus auditor writing `verification/audit-*-2026-11-13.json`. Wave D was requested by the user after the wave C close-out ("continue with the remaining Typeless gaps"); specs: `queue/PLAN-2026-11-13.md` (sections "Wave D" and "Wave D amendments after audit E"), `queue/T14.json` ... `queue/T22.json`.

**Task table (T14–T22)**

| Task | What | Audit | Verdict |
| --- | --- | --- | --- |
| T14 | `translation.py` context + `TASKS['ask']` + `decode_segment(context, ask_language)`; new `context.py` (foreground window, Ctrl+C selection capture with clipboard restore) | `audit-E` | PASS |
| T15 | `learning.py`, `sounds.py`, `audiofocus.py` (Core Audio via ctypes) with tests | `audit-E` | PASS |
| T16 | `core.py` store additions (stats rows, prune), `insights.py`, `theme.py` | `audit-E` | PASS |
| T17 | `desktop.py`/`run_desktop.py` integration: ask hotkey and mode, context-aware setting, hotkey auto paste-back with clipboard restore, auto dictionary UI, sounds, mute-others, 洞察 tab, retention, appearance | `audit-E` | FAIL (Alt not released before Ctrl+C; default `Right Alt + Space` opens the system menu; consecutive deferred pastes lost or duplicated) |
| T18 | Documentation: USER_MANUAL, README, CLAUDE.md, STATUS, handoffs (this entry) | `audit-F` | PASS |
| T19 | Final rebuild with `-IncludeGpu`, packaged self-tests incl. an `ask` self-test, manual copied into `dist` | `audit-F` | PASS (superseded by T19b/T19c rebuilds; final evidence `verification/packaged-waveD3-2026-11-14.json`, see Done) |
| T20 | Fix audit E: default ask = `RightAlt+RightCtrl` with migration of the old default; narrow swallow rule in `hotkeys.py`; release held keys (incl. Alt) before selection capture; merged paste | `audit-E2` | FAIL (a synthetic key-up release made `_sync_physical` drop the key after 1.2 s and stop a held ask) |
| T21 | Fix audit E2: `PushToTalk.mark_synthetic_release`; read-only clipboard-format check before injecting anything; swallowed-key repeat timeout; `hotkeys_version` = 2 marker; audiofocus docstring | `audit-E3` | PASS |
| T22 | Small fix from audit E3 minors: apply the swallowed-key timeout only after a repeat was seen; read `hotkeys_version` with a safe int | `audit-F` | PASS. Done: 136 tests pass; swallowed-key timeout applies only after an auto-repeat was observed; `hotkeys_version` is read with a safe int cast (evidence `verification/hotkey-hook-2026-11-13.json`, `ok` true) |
| T23 | Fix audit F D1/D4: `capture_selection` waits 0.9 s, returns `('', False)` with reason `late` on timeout, daemon `_late_watch` restores the clipboard; `_write_text` owner fix | `audit-G` | PASS (4 minors G1-G4 -> T24) |
| T19b | Rebuild after T23 (`verification/packaged-waveD2-2026-11-13.json`) | `audit-G` | PASS (superseded by T19c) |
| T24 | Fix audit G minors G1-G3 (clipboard owner pid check, no false timeout on no-selection, `timeout_used` recorded); 142 tests | none (planner verified with file hashes and the test run; no further audit) | DONE |
| T19c | Final rebuild after T24, evidence `verification/packaged-waveD3-2026-11-14.json` (supersedes `packaged-waveD-2026-11-13.json` and `packaged-waveD2-2026-11-13.json`) | none (planner verified) | DONE |
| T18c | Docs update after audit G: STATUS.md and handoffs.md point to waveD3 and record audit F/G | none | DONE |

Audit verdict summary: E = T14/T15/T16 PASS, T17 FAIL (-> T20); E2 = T20 FAIL (-> T21); E3 = T21 PASS (`replan_needed` empty); F = T22/T18/T18b/T19 PASS but overall FAIL on D1 (-> T23); G = T23/T19b PASS, overall PASS with 4 minors (-> T24; G1-G3 closed by T24, verified by the planner, 142 tests, no further audit). Unit tests: 117 (E), 129 (E2), 133 (E3), all passing. Audit files are append-only; do not edit them.

**Done**
- 隨便問 (`ask`): hotkey default `RightAlt+RightCtrl`; transcript + window title + app name + Ctrl+C selection go to the LLM chain with `TASKS['ask']`; no Whisper fallback (transcript shown with the warning `沒有可用的 LLM，顯示原始轉錄`, not pasted). Old default `RightAlt+Space` is migrated once (`hotkeys_version` = 2); customised values and a deliberate later `RightAlt+Space` are kept.
- Narrow swallow rule: modifiers are never swallowed; only the non-modifier key completing a configured Alt combo is hidden (so Alt+Space no longer opens the system menu). Selection capture releases held keys including Alt first, then `mark_synthetic_release`; multi-segment paste-back is merged into one clipboard write and one Ctrl+V; non-text clipboard -> capture skipped, nothing injected, status line explains.
- Context-aware formatting (setting, default on), hotkey auto paste-back (default on) with CF_UNICODETEXT clipboard restore, sounds (default on), mute-others (default off), auto dictionary (learns only from edits in the Voice2Txt editor; user accepts/ignores), 洞察 tab (words = CJK chars + latin words; time saved assumes 40 wpm), retention (`1 週`/`1 個月`/`3 個月`/`永久`, default `永久`), appearance (`系統`/`淺色`/`深色`).
- Docs updated by T18 (this entry): USER_MANUAL (new sections 隨便問, 依前景 App 調整格式, 快捷鍵錄音後自動貼回與剪貼簿還原, 互動聲音, 語音輸入時靜音其他音訊, 洞察分頁, 自動新增, 保留歷史紀錄, 外觀), README (feature list, Typeless comparison), CLAUDE.md (new modules, settings keys, `decode_segment`), STATUS (new rows, 下一步, 已知限制).
- T22 done: 136 unit tests pass (count cited from `verification/audit-F-2026-11-13.json`; the hotkey-hook JSON has no test count). The swallowed-key release timeout now applies only after an auto-repeat of that key was seen, and `hotkeys_version` is coerced safely. Hook check `verification/hotkey-hook-2026-11-13.json` (`ok` true): swallowed key F24 held 1.5 s gives exactly one start and one stop; two-key combo F24+F23 held 3.0 s gives one start/stop with stop at 3.032 s.
- T19 done (superseded by `verification/packaged-waveD3-2026-11-14.json`, see T19c below), evidence `verification/packaged-waveD-2026-11-13.json`: build exit 0 in 161.3 s, 0 PyInstaller ERROR lines; `dist` = 8276929974 bytes in 1330 files; exe SHA-256 starts `7f366fdd8467`; bundled `msvcp140` is 14.44.35211.0; `voice2txt.ico` present. Five packaged self-tests, all exit 0, `stage` completed, `ok` true: (a) UI only; (b) `zh` backend `Ollama gemma4:latest`; (c) `translate` with `--cloud Anthropic:low` (no key in env), backend `Ollama gemma4:latest`; (d) `en` backend `Whisper`; (e) `ask` with no LLM, backend `Whisper`, warning `沒有可用的 LLM，顯示原始轉錄`. `--minimized` was still running after 8 s with the tray window class found; a second instance exited 0 in 0.28 s. `USER_MANUAL.md` and the manual in `dist` are byte-identical (SHA-256 `cb037cbd...`). `--help` lists `ask`, `Anthropic:low` and `--minimized`.
- T19c done, final evidence `verification/packaged-waveD3-2026-11-14.json` (supersedes waveD and waveD2): build exit 0 in 171.0 s, 0 PyInstaller ERROR lines; `dist` = 8276931737 bytes in 1330 files; exe SHA-256 starts `1ddef70343db`; `msvcp140` 14.44.35211.0; five packaged self-tests (UI only, zh, translate with `--cloud Anthropic:low`, en, ask) all exit 0 with `ok` true; `--minimized` still running after 8 s with the tray window found; second instance exited 0 in 0.39 s; `USER_MANUAL.md` and the `dist` copy have identical SHA-256; the PYZ `context` module contains `clipboard_owner_pid`.
- T23 done (audit F D1/D4): `context.capture_selection` now waits 0.9 s; on timeout returns `('', False)` with `last_skip_reason='late'` and starts a daemon `_late_watch` that restores the saved clipboard text when the target writes late (one write burst; two bursts = user copied, do nothing; cancelled by the next capture). `_write_text` opens the clipboard with the desktop window as owner (OpenClipboard(NULL) made SetClipboardData fail intermittently, error 1418). Evidence: `verification/context-capture-2026-11-13.json` (fast + delayed 700 ms scenarios). T24 (audit G G1–G3): the watcher now also checks the clipboard owner: `GetClipboardOwner` -> `GetWindowThreadProcessId` must equal the target pid captured at capture time (`_late_watch(..., target_pid, owner_pid)`), otherwise (different process, unknown owner) it does not restore, so a user copy from another program is never overwritten. `check_context_capture.py` now records `timeout_used` per scenario (700 ms scenario uses 0.4 to reproduce the defect; shipped default 0.9) and adds `no_selection_user_copy`.
- Evidence: `verification/context-capture-2026-11-13.json`, `verification/audiofocus-2026-11-13.json`, `verification/wave-d-2026-11-13.json`, `verification/hotkey-hook-2026-11-13.json`, `verification/audit-E-2026-11-13.json`, `audit-E2`, `audit-E3`.

**Findings**
- Not implemented on purpose: UI Automation field capture, learning from edits in other apps, cloud sync. The context is window title + app name + category + the Ctrl+C selection only.
- A hook that swallows a key makes `GetAsyncKeyState` stale for that key; recovery needs the repeat heuristic. A key we released with injected key-ups looks physically up, so physical sampling must be suppressed for it (`mark_synthetic_release`). Both bugs were found only by real-key cross-process checks, not by the pure state machine tests.
- Force-killing the process cannot restore other apps' mute; Windows remembers per-app mute. The manual points users to the Volume Mixer.
- E3 minor (fixed by T22): a swallowed key that never auto-repeats used to be treated as released 1.2 s after being swallowed; the timeout now applies only after an auto-repeat was observed.
- Still no live Anthropic call (no key), no compile of the iOS project, no human-typed or real-microphone evidence. The packaged build now includes wave D (`verification/packaged-waveD3-2026-11-14.json`); right Alt injection against the packaged exe was not attempted because Typeless was running, and there is no human-typed evidence.

**Next**
1. Wave D audits are complete (`verification/audit-F-2026-11-13.json`, `verification/audit-G-2026-11-13.json`); no further audit is planned. Final packaged evidence: `verification/packaged-waveD3-2026-11-14.json`.
2. Real-person test of wave D in real apps (ask with selection, paste-back, clipboard restore, mute-others on real apps).
3. Carry-over: `ANTHROPIC_API_KEY` benchmark, 30-minute recording, Mac/Xcode build.

**Risks**
- Everything about hotkeys and capture is verified with injected keys and test processes. Other low-level hooks or apps that treat Ctrl+C differently may behave differently.
- Selected text and window titles reach the configured LLM; with cloud fallback enabled they leave the machine (text only, never audio).

---

## 2026-11-13 — JEV session: Anthropic stage-2 backend, iPad + iOS stage 2, push-to-talk hotkeys, tray/indicator/login start

**Roles (JEV).** Planner: the main session (high effort); its specs are in `queue/` (`PLAN-2026-11-13.md`, `T*.json`). Executors: Sonnet (`claude-sonnet-5-5`). Auditor: an independent Opus run per wave, writing `verification/audit-*-2026-11-13.json`. Wave A = T01 → T02 in parallel with T03; wave B = T06 → T05; wave C was added after the user chose "push-to-talk hotkeys + tray" from the Typeless gap analysis (`verification/typeless-feature-inventory-2026-11-13.md`).

**Task table (T01–T12 with audit outcome)**

| Task | What | Audit | Verdict |
| --- | --- | --- | --- |
| T01 | Anthropic `CloudTranslator` (raw urllib, Messages API, `claude-sonnet-5-5`/`low`), chain Ollama → Anthropic → OpenAI → Gemini → Whisper | `audit-A1` | PASS |
| T02 | Desktop UI rows for 3 providers, settings roundtrip, `--cloud Anthropic:*`, benchmark wiring | `audit-A1` | PASS |
| T03 | iOS: iPhone + iPad (orientations, layout), `Refiner.swift` stage 2 (cloud only, off by default), `Record.source`, `scripts/check_ios_project.py` | `audit-A2` | FAIL (missing `import Combine` and minors) |
| T03b | Fixes for the A2 defects (Combine, `@MainActor` RefinerChain, `systemUptime` pause, empty translate fallback status, 儲存 button) | `audit-C` | PASS |
| T05 | Documentation (this entry's files: USER_MANUAL, README, CLAUDE, STATUS, handoffs) | `audit-D` | PASS (minor defects fixed in T13) |
| T05b | Doc follow-up edits to STATUS.md and handoffs.md | `audit-D` | PASS (dist_bytes fixed in T13) |
| T06 | `-IncludeGpu` rebuild + packaged self-tests → `verification/packaged-anthropic-2026-11-13.json` | `audit-A1` noted ordering | done (4 reports `ok`); predates wave C |
| T07 | `voice2txt/hotkeys.py`: `PushToTalk` state machine + `WH_KEYBOARD_LL` hook (never swallows keys) | `audit-C` | FAIL (paste while key held, no single instance, race, no watchdog, …) |
| T08 | `tray.py`, `startup.py`, indicator, close-to-tray, `--minimized`, `.ico` | `audit-C` | FAIL (same audit; follow-ups in T10) |
| T09 | Final rebuild after wave C → `verification/packaged-waveC-2026-11-13.json`, copy of the manual into `dist` | `audit-D` | PASS (exit 0, 173.0 s; 4 packaged self-tests `ok`; sha/bytes/path fields corrected in T13) |
| T10 | Fix audit C: deferred paste, single instance, no-op race, reset-while-held, per-combo stop, watchdog, TaskbarCreated retry, … | `audit-C2` | FAIL (new major: `_sync_physical` flapping on a swallowed key) |
| T11 | Fix audit C2: swallowed-key hold, `release_held_modifiers`, liveness probe, `CreateMutexW` NULL | `audit-C3` | FAIL (multi-key swallowed combo dropped at 1.2 s; liveness probe resets the system idle timer) |
| T12 | Fix audit C3: only keys seen physically down are recovered; liveness gated on recent user input; UIPI filter | `audit-C4` | PASS |

No T04 exists in `queue/`. Audit verdict summary: A1 PASS (T01, T02), A2 FAIL (T03), C: T03b PASS / T07 FAIL / T08 FAIL, C2 FAIL (T10), C3 FAIL (T11), C4 PASS (T12). Audit files are append-only evidence; do not edit them.

**Done**
- Anthropic backend and UI. Chain is Ollama → Anthropic → OpenAI → Gemini → Whisper; Anthropic default `claude-sonnet-5-5`/`low`, `claude-opus-5-5` documented as an option, OpenAI alternative `gpt-6.1-terra`. 30 unit tests at A1 (24 original + 6 new), 80 at C4. Evidence: `audit-A1`, `verification/desktop-anthropic-ui-2026-11-13.json`, `verification/packaged-anthropic-2026-11-13.json`.
- iOS: universal target (`TARGETED_DEVICE_FAMILY = 1,2`), iPad layout, optional cloud stage 2 in `Refiner.swift`, `ios/README.md` updated. Evidence is structural only: `verification/ios-project-structure-2026-11-13.json`.
- Hotkeys: Right Alt dictate, Right Alt + Right Shift translate, legacy Alt+Shift+Space; hold ≥ 0.35 s = hold-to-talk, shorter = tap-to-toggle; custom combos captured in the settings tab; paste-back waits for release; Typeless-conflict warning. Evidence: `verification/hotkey-hook-2026-11-13.json`, `audit-C4`.
- Tray/indicator/login start/`--minimized`/single instance: `verification/tray-indicator-2026-11-13.json`, `verification/single-instance-2026-11-13.json`.
- Docs: USER_MANUAL (Anthropic, 快捷鍵, 系統匣, iPhone/iPad), README, CLAUDE.md, STATUS (new rows, 下一步, 已知限制).

**Findings**
- No Anthropic API key was available (`anthropic_key_in_env` false in `packaged-anthropic-2026-11-13.json`; `ant` CLI not installed), so **no live Anthropic call was made**: no quality or latency numbers exist. Unit tests pin the wire shape only.
- Hotkey bugs came in layers: each fix exposed a new interaction with a downstream hook that swallows a key (Typeless swallows Right Alt, which never shows as physically down). The final rule (T12): physical-state recovery applies only to keys seen physically down at least once.
- A liveness probe injecting input resets the system idle timer; it must only run while the user is recently active.
- Menu-bar suppression for a bare Alt tap is best-effort: `audit-C` measured 0/38 activations at 10–80 ms taps and 3/8 with instantaneous synthetic taps (measured in audit-C on the T07 version, not re-measured after T10-T12; Left Alt proxy; Right Alt itself was unverifiable because Typeless was running).
- Final rebuild (T09), evidence `verification/packaged-waveC-2026-11-13.json`: `-IncludeGpu` build exit 0 in 173.0 s; `dist_bytes` 8,276,858,735 (1329 files; recomputed in T13 with os.walk); exe SHA-256 `CB1FBD18CBC3EE07461334AEBB84DC07661B902EA7048ECD7C5F3C7775945E82` (recomputed in T13; prefix `CB1FBD18CBC3`) (exe timestamp 2026-11-13 07:37:34); `msvcp140_version` 14.44.35211.0; `icon_present` true. Four packaged self-tests all `ok` true with `stage` `completed`: UI-only (`desktop_ui` true); zh (backend `Ollama gemma4:latest`, 6.125 s); translate (backend `Ollama gemma4:latest`, 12.5 s); en (backend `Whisper`, 5.25 s). `--minimized` launch: process running after 8 s observed, tray window class found; a second instance exited in 0.41 s with exit code 0. The manual copy in `dist` and `USER_MANUAL.md` have identical SHA-256 (`identical` true). `--help` lists `--minimized` and `Anthropic:low`. Caveats: WM_CLOSE on the tray window did not end the process within 2 s (ended with `taskkill /F /T`); Right Alt injection not attempted (Typeless running); no cloud key in the env, so the translate chain had no Anthropic and live cloud calls remain unverified.

**Accepted residual limitations (from `audit-C4`)**: (1) a key whose key-up is lost before the first 20 ms sampling stays held until pressed again; (2) after a genuinely lost key-up, re-pressing within 1.5 s is ignored once; (3) with Typeless running, Right Alt is intercepted (warning shown); (4) iOS still uncompiled; (5) no live Anthropic call verified.

**Next**
1. Audit of T05 docs and T09 (evidence: `verification/packaged-waveC-2026-11-13.json`; the manual in `dist` is byte-identical to `USER_MANUAL.md`).
2. The user supplies `ANTHROPIC_API_KEY` and runs `PYTHONPATH=. .\.build-venv\Scripts\python.exe scripts\benchmark_refine.py small`.
3. Real-microphone test (modes, hotkeys, paste-back, tray, 30 minutes) and a Mac/Xcode build for iPhone/iPad.
4. Remaining Typeless gaps: insert-anywhere + context capture + 隨便問, auto dictionary, audio options, dashboard.

**Risks**
- Everything about hotkeys is verified with injected keys, not human typing. Anti-virus or other low-level hooks may interfere.
- Anthropic request shape (`anthropic-version: 2026-10-21`, `output_config.effort`) is from the planner's spec and unit tests, not from a live response.
- iOS code has never been compiled; Swift errors are likely on the first Xcode build.
- Cloud LLMs remain opt-in and send transcript text only; keep it that way.

---

## 2026-10-18 (later) — Two-stage redesign: Whisper → LLM refine, chain Ollama → OpenAI → Gemini → Whisper

**User direction (verbatim intent):** "Whisper do the voice to text work first, plus the effort by LLM to organize and denoise the transcripts." Chain: Ollama → OpenAI high → Gemini low → Whisper.

**Done**
- `translation.py`: every backend now has `refine(text, mode, vocabulary)`, and the LLM runs in all three modes, not only translate. Prompt rules are in `RULES`/`TASKS`. `CLOUD` holds the fixed order and defaults (OpenAI `gpt-6-luna` high, Gemini `gemini-3.8-flash` low). `build_translator(ollama, clouds)`. In zh/en mode, a failed LLM returns the raw Whisper text; translate falls back to Whisper translate.
- Desktop settings: `Whisper + LLM 整理` / `僅 Whisper`, with rows ① Ollama, ② OpenAI, ③ Gemini (each has a checkbox, model, effort and DPAPI-encrypted key; old settings migrate). The source panel is now labelled "Whisper 原始轉錄".
- `run_desktop.py --self-test`: `--cloud PROVIDER:EFFORT` (repeatable) and `--vocabulary`.
- New fixtures `tests/fixtures/disfluent-*` (made with `scripts/create_quality_audio.ps1 -Corpus disfluent`) and `scripts/benchmark_refine.py`.
- 24 unit tests and `scripts/smoke_desktop.py` (run with `PYTHONPATH=.`) pass. Rebuilt `dist` (`-IncludeGpu`).
- Evidence: `verification/refine-small-2026-10-18.json`, `verification/packaged-chain-2026-10-18.json`.
- USER_MANUAL (design section, chain, settings), README, CLAUDE.md and STATUS updated.

**Findings**
- Whisper alone 0/5 on the messy clips; Ollama 5/5 (about 0.6 s); OpenAI high 5/5 (2–3.3 s). Whisper "translate" once returned Simplified Chinese instead of English.
- The first prompt let OpenAI and Gemini drop 「不是禮拜二」, treating it as a self-correction. Fixed with explicit rules: only treat signalled corrections as corrections, and keep contrasts and negations.
- Gemini latency swung from 2.6 s to over 60 s on the same day, then the account returned HTTP 429 "exceeded your current quota". The user needs to check Gemini billing or plan in AI Studio.

**Next**
- The user should check the Gemini quota, then rerun `scripts/benchmark_refine.py` with keys to get a full Gemini 5/5 result.
- Real-microphone testing of the refine latency: Ollama adds about 0.6 s per segment on CPU Whisper small.
- Possible addition: let the LLM drop Whisper hallucinations on silence (e.g. 「字幕由…提供」). Not done; it needs an "empty output is valid" path.
- iOS still has stage 1 only.

---

## 2026-10-18 — Session: /init + goal restatement

**Done**
- Ran `/init`: created `CLAUDE.md` (commands, desktop/iOS architecture, build gotchas, project rules).
- Created this `handoffs.md`.
- Confirmed the existing state: `.\.build-venv\Scripts\python.exe -m unittest discover -s tests` → 12 tests OK.

**State inherited from earlier sessions** (details in `STATUS.md`, `verification/`)
- Windows desktop app exists (`voice2txt/`, `dist/Voice2Txt/Voice2Txt.exe`) with three modes (zh / en / zh→en), pause-based chunking, dictionary prompt, history, export, `Alt+Shift+Space` hotkey, optional paste-back.
- Optional CUDA (medium / large-v3) and local Ollama LLM translation (`gemma4:latest` default) are in the code and have benchmark JSON in `verification/`. `README.md` and `STATUS.md` were written before these and do not fully describe them yet.
- iOS SwiftUI + WhisperKit project in `ios/`. **Never compiled.** No Mac available.
- Typeless analyzed statically (7-Zip + REA on `app.asar`). Ghidra was not used: there was no native target that needed it.

**Done later this session**
- Rebuilt `dist` with `scripts/build_windows.ps1 -IncludeGpu` (7.8 GB). Note: running it via PowerShell `*>` redirection fails spuriously (stderr + `ErrorActionPreference=Stop`); run `powershell -File scripts/build_windows.ps1 -IncludeGpu > log 2>&1` instead.
- Packaged `--self-test`: 6/6 ok → `verification/packaged-2026-10-18.json`; STATUS.md row added.
- User request: make Ollama the default when it is installed, add a cloud backup (Gemini Flash 3.8 / GPT Luna), and write a user manual. Done:
  - `translation.py`: `ollama_models()`, `CloudTranslator` (Gemini `gemini-3.8-flash` via generateContent + `thinkingLevel`; OpenAI `gpt-6-luna` via Responses + `reasoning.effort`; default effort `high`), `TranslatorChain` (60 s pause on failure), `build_translator()`. Last resort is Whisper `translate`.
  - `keystore.py`: DPAPI-encrypted API key. Desktop has a new 雲端備援 LLM settings section. The engine choice is now saved as `translation_backend_v2`, so the Ollama default applies once to users who had saved the old key.
  - `run_desktop.py --self-test` accepts `--fallback-provider/--fallback-model/--fallback-effort`.
  - `USER_MANUAL.md` (Traditional Chinese), shipped as `dist/Voice2Txt/使用者手冊.md`.
  - Rebuilt `dist`; 7/7 packaged self-tests ok → `verification/packaged-fallback-2026-10-18.json`.
  - Model IDs come from the official docs as of 2026-10-18: ai.google.dev "latest-model" / "thinking" pages and developers.openai.com models + reasoning guides. Neither model is on a free tier.

**Next steps**
1. (done 2026-10-18) README.md updated: model/compute/translation-engine table, quality comparison, GPU build and packaged self-test commands.
2. (done 2026-10-18) Rebuild + packaged self-test.
3. Real-microphone acceptance on Windows: all modes, hotkey, paste-back, 30-minute run. The user has to speak for this.
4. iOS: needs a Mac with Xcode 16+ to resolve WhisperKit, build, sign with a Personal Team, and test on a device.
5. Optional: a Typeless-style LLM polish step (cleaning up self-corrections and filler words), local-only.

**Risks / constraints**
- Whisper built-in zh→en drops meaning at every size on the 3-sentence corpus (small 1/3, medium 2/3 drops 「明天」, large-v3 2/3 drops 「開會」). Only small + local Ollama gemma4 got 3/3. Ollama is now the default when installed.
- Cloud backup was verified with real keys (supplied by the user in a key file outside the repo; never copy keys into the repo or into reports). Results: `verification/cloud-fallback-2026-10-18.json`. OpenAI took 3.5–5.6 s at every effort level. Gemini took 8–12 s at low/medium; at `high` it took 28 s once and hit the 30 s timeout once. Decided: OpenAI high, Gemini low.
- Cloud backup is opt-in, pay-per-use, and sends transcript text (never audio). Keep it off by default.
