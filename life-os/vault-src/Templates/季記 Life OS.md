---
type: quarterly
quarter: {{quarter}}
tags:
  - quarterly
---
« [[指南針儀表板]] · [[{{quarter}} 個人退修|本季退修]] »

# {{quarter}}（{{q_start}} → {{q_end}}）

## 焦點領域
從退修的人生輪挑出的那一個領域：

## 本季意圖
> [!info] 從退修筆記的「下一季意圖」帶過來
> ![[{{quarter}} 個人退修#下一季意圖]]

## 本季專案
```dataview
TABLE status AS "狀態", area AS "領域", due AS "期限"
FROM "Life OS/04 Projects"
WHERE type = "project" AND quarter = "{{quarter}}" AND status != "done"
```

## 本季週記
```dataview
LIST FROM "Life OS/01 Journal/Weekly" WHERE quarter = "{{quarter}}" SORT file.name ASC
```

## 本季每日提問
```dataviewjs
await dv.view("Life OS/Meta/views/dailyquestions", { from: "{{q_start}}", to: "{{q_end}}" });
```
