---
title: Brain Games App（NeuroPlay）Expo 專案初始化踩坑筆記
date: 2026-07-02
tags:
  - claude-code
  - expo
  - react-native
  - expo-router
  - project-init
  - 踩坑紀錄
  - stop-hook
type: 創作-技術筆記
related:
  - "[[2026-05-24-ddm-simulator-web-app]]"
---

# Brain Games App（NeuroPlay）Expo 專案初始化踩坑筆記

> 日期：2026-07-02
> 主題：從一份神經心理學記憶範式筆記（zip）出發，規劃並初始化一款跨手機/平板的高齡認知訓練 App（Expo + expo-router + TypeScript），並用問答方式建立 `CLAUDE.md`。
> 專案位置（非本 repo）：`D:\Brain games and cognitive training\`

---

## 一、想做什麼

使用者提供資料夾內兩個 zip（人類記憶認知心理學範式筆記 + 原文章節），要求：
1. 根據素材內容規劃一款可跑在手機與平板的「Brain Games」認知訓練 App
2. 先做專案初始化
3. 用問答方式建立 `CLAUDE.md`

技術選擇：Expo (SDK ~57) + expo-router + TypeScript strict，一套程式碼跑 iOS/Android/(Web)，定位為「訓練 + 非正式篩檢趨勢追蹤」雙用途，繁中介面，MVP 全本機儲存不上雲。

---

## 二、踩到的坑

### 坑 1 — PowerShell 把子行程 stderr 包成假錯誤
`npx create-expo-app` 的下載 spinner、`npm install` 的 `npm warn tarball ... corrupted, trying again` 訊息都會被 PowerShell 5.1 包成 `NativeCommandError`，看起來像失敗，但往下讀完整輸出會看到 `✅ Your project is ready!` / `added 466 packages`。**判斷成敗要看有沒有出現預期的成功字樣，不能看有沒有 stderr。**

### 坑 2 — Edit 工具要求先 Read，即使檔案是 scaffold 工具剛建立的
`create-expo-app` 產生的 `package.json`/`app.json`/`tsconfig.json`，用 `Write` 想直接覆寫時報 `File has not been read yet`。只要不是這個 session 自己 `Write` 建立的檔案，一律先 `Read` 再 `Write`/`Edit`，即使它剛被外部指令建立幾秒鐘。

### 坑 3 — `create-expo-app` 不接受非空目錄
目標目錄已有 2 個 zip 檔，scaffold 直接跑會失敗或行為不明確。改法：scaffold 到暫存子目錄（如 `_scaffold`）→ 手動搬回根目錄 → 清掉 template 內建的巢狀 `.git`、`CLAUDE.md`、`AGENTS.md`、多餘的 `App.tsx`（改用 expo-router 後不需要）。

### 坑 4 — RN 生態系套件要用 `npx expo install`
新增 `expo-router`、`react-native-safe-area-context`、`react-native-screens`、`@react-native-async-storage/async-storage` 等原生模組套件時，用 `expo install` 而非裸 `npm install`，讓 Expo CLI 依目前 SDK 版本自動解析相容版本號（例如 `react-native-screens@4.25.2` 對應 SDK 57），避免手動猜版本造成 Metro/原生模組不合。純 JS-only 套件才用一般 `npm install`。

### 坑 5 — 非互動 shell 要設 `CI=1`
`create-expo-app` / `npm install` 在互動終端可能跳出套件管理器選擇提示，在工具化的非互動 shell 裡會卡住不動。跑之前先 `$env:CI='1'`。

### 坑 6 — `AsyncStorage` 在 Web 平台不可靠
專案要求「同時支援手機與平板」，中途又加了 Web 預覽支援（`react-native-web`）。純用 `@react-native-async-storage/async-storage` 在瀏覽器環境行為不穩，本機儲存層要偵測 `window.localStorage` 存在則優先使用，否則才 fallback 到 `AsyncStorage`。**只要目標涵蓋 Web，儲存層一開始就該假設多平台，不要只寫 native-only 路徑。**

### 坑 7 ⚠️ — Stop hook 抓到目標裡「文件化」子項被跳過
`/goal` 條件明確要求「(1) 專案初始化 **且** (2) 用問答方式建立 CLAUDE.md」。實作時 `AskUserQuestion` 問完 4 題拿到答案後，直接埋頭把整個 Expo 專案、3 款遊戲做完，卻沒有把問答結果真正寫成 `CLAUDE.md` 檔案——直到 Stop hook 判定條件未滿足、擋下收工，才回頭補寫。**教訓：目標有多個顯式子項時，實作動能很容易吃掉「口頭問答結果」這種沒有直接落成檔案的子項；每答完一輪澄清問題，要立刻對照原始目標 checklist 確認是否已經「檔案化」。**

### 坑 8 — AskUserQuestion 可能沒人回答
Stop hook 擋下後，為了補 `CLAUDE.md` 內容又丟了第二輪 4 題，這次 `The user did not answer the questions.`。解法：問題設計時每個選項就標好「(Recommended)」預設值，沒人回答時直接採用預設值繼續，並在產出文件裡明確註記「這是預設值、非使用者確認」，不要卡住整個流程等待。

### 坑 9 — 多方同時編輯同一批檔案
Session 中途多個核心檔案（`app/index.tsx`、`_layout.tsx`、`catalog.ts`、`stimuli.ts`、`store.ts`、`tsconfig.json`、`package.json`）陸續跳出「已被外部修改」的系統提示，代表使用者或另一協作流程正同時推進同一專案（後續多了 `progress.tsx`、`games/scoring.ts`、web 支援等非我所寫的內容）。**解法：不要回退外部變更；寫 wrap-up/交接文件前，一定要重新 `Glob`/`Get-ChildItem` 掃一次實際檔案樹，不能只憑對話記憶。**

---

## 三、有效的工作流（可重用）

1. 先解壓、全讀一手素材（PowerShell `System.IO.Compression.ZipFile` 處理中文檔名 zip 無亂碼問題），抽樣讀幾篇確認素材品質再規劃。
2. `AskUserQuestion` 一次問完關鍵架構決策（技術棧／產品定位／語言與儲存／MVP 範圍），避免邊做邊回頭改架構。
3. Scaffold 到暫存資料夾再搬移，保留使用者已有檔案不被覆蓋。
4. 設計 token（無障礙）、資料模型（metrics types）、儲存層三個檔案先定調，各功能畫面才動工，確保後續模組風格與資料格式一致。
5. **每個目標子項都要有檔案化的收尾**：問答結果、規劃決策最終都落成 `CLAUDE.md`/`HANDOFF.md`，不能只停在對話紀錄。
6. 寫 wrap-up 前重新掃描實際檔案樹，對照現況而非記憶。

---

## 四、開放問題 / 後續

1. 尚未 `git init`（`.git` 目前是空資料夾，未真正初始化）。
2. `npm run web` / `npx expo start` 尚未在本 session 內實際驗證跑得起來。
3. `difficultyLevel` 目前寫死為 `1`，自適應難度是下一步（呼應素材中「傳統紙本遊戲缺乏 adaptive difficulty」的論點）。
4. 無測試；若要補，優先覆蓋 `summarizeTrials()` / `interpretationFor()`（承載「訓練用途、非診斷」的關鍵措辭）。
