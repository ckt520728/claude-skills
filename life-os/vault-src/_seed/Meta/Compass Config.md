---
type: compass-config
version: 0.2.0
start_date: 2026-09-29

# --- 個人（Memento mori 小工具用）----------------------------------------
# 生日填 YYYY-MM-DD。留空則儀表板只顯示「請設定」。這是你的資料，系統不會替你填。
birthdate:
life_expectancy: 80

# --- 資料夾（Compass 結構，全部放在 Life OS/ 底下）------------------------
# 夜間腳本與所有儀表板都從這裡讀路徑，不要在別處硬寫死。
# 每日筆記沿用 vault 既有的 每日筆記/，不搬家。
daily_note_folder: 每日筆記
daily_folder: 每日筆記
daily_note_format: YYYY-MM-DD
weekly_folder: Life OS/01 Journal/Weekly
quarterly_folder: Life OS/01 Journal/Quarterly
retreat_folder: Life OS/02 Retreats
planning_folder: Life OS/03 Planning
projects_folder: Life OS/04 Projects
people_folder: Life OS/05 People
tasks_file: Life OS/08 Tasks/任務總表.md
dq_prefix: dq_
habit_prefix: habit_
wheel_prefix: wheel_
board_done_lanes: 完成,已發表,封存,Done
reflection_heading: 💡 今日反思
journal_heading: 📝 日記
wins_heading: 🏆 今日小勝
gratitude_heading: 🙏 感恩
priority_heading: 明日優先事項

# 臨床區塊的存取層級。使用者於 2026-09-29 決定為 derived。
#
#   never    完全不讀
#   local    程式可以讀，但推導出的任何東西都不得傳出去
#   derived  ← 目前：程式可以讀，且只有「數字」可以進 prompt
#   full     原始文字可以進 prompt
#
# derived 的實際意思：夜間腳本在你的機器上數一下待處理幾筆，
# 把 clinical_pending / clinical_load 兩個數字寫進 frontmatter。
# 教練只讀 frontmatter，所以它知道「今天 6 例」，但永遠看不到那 6 例是誰。
#
# 這個邊界是程式結構擋的（lifeos/clinical.py 的 ClinicalDigest 裝不下字串），
# 不是靠 prompt 裡寫一句「請不要讀」。
#
# 打錯字會 fallback 回 never，不會意外放寬。
clinical_heading: 🏥 臨床
clinical_access: derived

# --- 漸進解鎖（Compass Build Order，Guide/11）--------------------------
# 天數從 start_date 起算，第 1 天 = start_date 當天。由 lifeos/unlock.py 執行。
# 上游原文：「上一層一致性低於 80% 時，不要加下一層。」
# 所以第 31 天之後，還要「最近 30 天有評分的天數 ≥ 80%」才會打開下一層。
unlock_days:
  journal: 1
  habits_weekly: 31
  retreat: 61
  tasks: 91
  writing: 121

# --- 每日提問 dq_* ------------------------------------------------------
# ⚠️ 以下是「草稿範例」，不是你的題目。
# 第一件該做的事：把這幾題改成你自己真正想每晚面對的問題，或刪掉換成別的。
#
# 兩條寫題規則（來自 Marshall Goldsmith《Triggers》，參考資料的核心主張）：
#   1. 問「努力」不問「結果」。「我今天是否盡力…」可控；「我今天有沒有做到…」只會變成自我審判。
#   2. 一題只問一件事。兩件事合成一題，分數就沒有意義。
#
# 建議 3–5 題。超過 5 題，30 秒的流程會變成 2 分鐘的流程，然後就不會做了。
dq_questions:
  - id: dq_read
    prompt: 我今天是否盡力進行深度閱讀（文獻或專業書）？
  - id: dq_build
    prompt: 我今天是否盡力推進手上的研究或系統建置？
  - id: dq_body
    prompt: 我今天是否盡力照顧身體（飲食、運動、睡眠）？
  - id: dq_present
    prompt: 我今天是否盡力對身邊的人保持專注與在場？

# --- 習慣追蹤 habit_* ---------------------------------------------------
# 布林值（true / false），不是分數。同樣是草稿，請改成你自己的。
# 建議一開始只放 2 個。習慣欄位每多一個，夜間流程就多一次按鍵。
habits:
  - id: habit_move
    name: 動 20 分鐘
  - id: habit_sleep_before_1
    name: 一點前上床

# --- 人生輪 wheel_* （retreat 層，第 61 天解鎖）---------------------------
# 季度退修會用，1–10 分。八大維度是 Compass 上游的標準盤面，可以改名但建議維持八個。
# criteria：描述這個領域「長什麼樣子」的字詞，給 JEV 決策層判斷收件屬於哪個領域用。
# 這是草稿，請改成你自己會寫出來的字。寫得越像你的用語，分類越準。
wheel_areas:
  - id: wheel_health
    name: 健康與體能
    criteria: 運動、睡眠、飲食、體重、健檢、看醫生、身體、跑步、重訓 exercise sleep diet gym run
  - id: wheel_career
    name: 事業與專業
    criteria: 臨床工作、門診、病房、會議、研究、論文、投稿、教學、升等、醫院 clinic ward research paper teaching
  - id: wheel_finance
    name: 財務
    criteria: 存錢、投資、保險、帳單、預算、房貸、退休 saving invest insurance budget
  - id: wheel_growth
    name: 個人成長
    criteria: 學習、讀書、課程、語言、技能、寫作、反思 learn book course language skill
  - id: wheel_relationships
    name: 人際關係
    criteria: 朋友、同事、聚餐、聯絡、社群、人脈 friend colleague dinner network
  - id: wheel_family
    name: 家庭與感情
    criteria: 家人、父母、孩子、另一半、家裡、陪伴 family parents kids partner home
  - id: wheel_fun
    name: 娛樂與休閒
    criteria: 旅行、電影、音樂、遊戲、嗜好、放假、休息 travel movie music game hobby vacation
  - id: wheel_meaning
    name: 生命意義
    criteria: 意義、價值、信仰、志工、使命、感恩、人生主題 meaning values faith volunteer purpose

# --- 顯示用的色帶 ------------------------------------------------------
# 只影響儀表板上的 🟢🟡🔴，不影響任何自動化行為。
# 注意：真正會「替你做事」的門檻（自動歸檔的信心值）不在這裡，
# 在 lifeos/gtd.py 的具名常數裡。設定檔管顯示，程式碼管決策。
display_bands:
  good: 8
  watch: 6
---

# Compass Config — 單一真實來源

這個檔案是整套 Life OS 唯一的設定來源（SSOT, Single Source of Truth）。

改這裡的 frontmatter，夜間腳本、儀表板、模板會一起跟著變，**不需要改任何程式碼**。
反過來說：任何儀表板如果把 `dq_read` 這種欄位名直接寫死在查詢裡，那是 bug。它應該從這裡讀。

## 為什麼要有這個檔案

不用 SSOT 的做法是把題目寫在模板裡、把欄位名寫在每個儀表板裡、把分數區間寫在第三個地方。
三個月後你想把一題改掉，就要同時記得改四個檔案，其中一個一定會忘記 —— 這叫 schema drift，
是這類系統最常見的死法。

## 改題目之後會發生什麼

- **新增一題**：今晚開始就會問你。之前的日子沒有這個欄位，儀表板會自動跳過，不會報錯。
- **改掉題目文字**（`prompt`）但保留 `id`：歷史分數仍然有效，因為資料是綁 `id` 的。
- **改掉 `id`**：等於開了一個新指標，歷史資料不會跟過來。想保留趨勢就別動 `id`。
- **刪掉一題**：不會刪掉歷史資料，只是今晚不再問。舊分數還在舊筆記裡。

## 現在是第幾天

`start_date` 決定一層一層打開的進度，照上游 Compass 的 Build Order（`Guide/11`）：

| 天 | 打開 |
|---|---|
| 1 | 每日提問、夜間評分、日記、收件（收件永遠開著） |
| 31 | 習慣畫布、週記與週回顧 |
| 61 | 季度退修、人生輪、人生主題／核心價值／理想的一週 |
| 91 | 任務儀表板、專案、人物、GTD 自動歸檔 |
| 121 | 創作看板 |

上游的另一條規則也寫進程式了：**上一層一致性低於 80%，不加下一層**。
所以第 31 天之後，還要「最近 30 天至少 80% 的日子有評分」，下一層才會亮。

（更正 2026-09-30：之前這裡寫「上游沒有 30 天規則」，是錯的。完整複製 repo 後，
`Guide/11 Build Order.md` 明文寫著：挑一個工作流、跑 30 天、再加下一個。）

還沒解鎖的層不會藏起來，會以灰色顯示解鎖日期，也可以按「先偷看一下」。
要提早解鎖就改 `start_date`，但請先問自己：每晚 30 秒，是不是已經變成不用想的事了？
