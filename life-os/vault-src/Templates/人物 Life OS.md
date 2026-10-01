---
type: person
slug: {{slug}}
role:
meets:
tags:
  - person
---
標籤：`#p/{{slug}}`

想到「下次要跟他講 X」，在任何地方寫成任務：`- [ ] X #discuss #p/{{slug}}`。開會前打開這一頁。

## 待討論
```dataviewjs
const t = dv.pages('"Life OS" or "每日筆記" or "創作庫"').file.tasks
  .where(t => !t.completed && t.tags.includes("#discuss") && t.tags.includes("#p/{{slug}}"));
if (t.length) dv.taskList(t, false); else dv.paragraph("_目前沒有。_");
```

## 其他跟他有關的任務
```dataviewjs
await dv.view("Life OS/Meta/views/tasks", { section: "person", tag: "#p/{{slug}}" });
```

## 一起的專案
```dataview
LIST FROM "Life OS/04 Projects" WHERE contains(people, this.file.link) AND status != "done"
```

## 筆記


## 會議紀錄
- {{date}} 
