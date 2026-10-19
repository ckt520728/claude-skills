# 2026 Life OS

照 **Compass**（Mike Schmitz 的系統、Daniel Agrici 的 Obsidian 模板）結構，蓋在既有 Obsidian vault 上的 Life OS。
GTD 五個階段裡的**非生成性判斷**交給 **jev-engineering** 技能（本機、校準過信心、以信心設閘），
算術交給程式，對話交給 Claude。

這個資料夾是工作區。**產品是 vault。**

```
G:\我的雲端硬碟\2026 Life OS\     ← 這裡（工作區）
G:\我的雲端硬碟\Second Brain\     ← 實際的 vault（產品），部署在 Life OS/
D:\2026 JEV Engineering\          ← jev-engineering 技能；lifeos/jev/ 是它的原封複本
```

## 使用者從哪裡開始

vault 裡的 **`Life OS/00 開始這裡.md`** → [[設定清單]] → [[使用手冊]]（`Life OS/Guide/使用手冊.md`）。
每天兩個熱鍵：`Ctrl+Shift+I` 收件、`Ctrl+Shift+Q` 夜間評分（30 秒）。

## 三層

```
[G] 生成    → Claude：教練對話、週回顧、退修引導（Life OS/Prompts/）
[D] 決策    → jev-engineering：Choice / Score / Noul，一次 decide() 問完，jev.gate() 設閘
[C] 硬規則  → 程式碼：日期、7 日平均、連續天數、Build Order 解鎖、80% 一致性、只追加保護
```

## Compass 結構（全部在 vault 的 `Life OS/` 底下）

`00 Dashboards/`（指南針儀表板等 8 頁）· `01 Journal/`（週記、季記）· `02 Retreats/` · `03 Planning/`
（人生主題、核心價值、理想的一週）· `04 Projects/` · `05 People/` · `06 Writing/` · `08 Tasks/` ·
`Meta/`（Compass Config + `views/*.js`）· `Prompts/`（12 則）· `Guide/`。每日筆記留在 vault 原本的 `每日筆記/`。

和上游的差異與理由見 `references/compass-upstream.md`（重點：不裝 Templater / Periodic Notes / Tasks，
由儀表板自己建檔、Dataview 讀任務）。

## 一層一層打開（上游 Build Order）

| 天 | 層 |
|---|---|
| 1 | 每日提問、日記、收件 |
| 31 | 習慣畫布、週記 |
| 61 | 季度退修、人生輪、人生規劃 |
| 91 | 任務、專案、人物、GTD 自動歸檔 |
| 121 | 創作看板 |

第 31 天之後，還要近 30 天評分率 ≥ 80% 才開下一層。

## 開發

```bash
bash scripts/checks.sh           # 70 項客觀證據，跑這個才算完成
bash scripts/deploy.sh --dry-run # 先看會改什麼
bash scripts/deploy.sh           # vault-src/ → vault；程式覆寫，你改過的種子檔保留，退役檔只在雜湊相符時刪
python scripts/sync_jev.py       # 技能更新後重新同步 lifeos/jev/
python scripts/triage.py         # GTD 釐清：JEV 逐則提議，你裁決，每次裁決都是校準資料
python scripts/lifeos_status.py  # 所有 prompt 用的 [C] 數字
```

改 `vault-src/`，然後 deploy。**不要手改 vault 裡部署好的程式檔**（儀表板、views、prompts、手冊）。

## 最大的未知

1. **Obsidian 端沒有在真實 app 裡跑過**：`nightly.js`、`capture.js`、12 個 Dataview views 都通過語法檢查，
   但 QuickAdd 的 Macro 從來沒被建立（`data.json` 裡 0 個選項），所以夜間評分一次都沒真的執行過。
2. **決策層的 criteria 字詞是盲寫的**，還沒有任何真實收件可以對照。校準讓它在不準時會問你，
   但它要多久才會變準，取決於你實際回答了多少。

完整清單見 `UNKNOWNS.md`。
