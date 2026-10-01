---
type: project
status: active
slug: {{slug}}
area:
quarter: {{quarter}}
started: {{date}}
due:
people: []
tags:
  - project
---
標籤：`#project/{{slug}}` —— 任何地方的任務加上這個標籤，就會出現在這裡。

## 成果
「完成」長什麼樣子：
- 

## 下一步
```dataviewjs
await dv.view("Life OS/Meta/views/tasks", { section: "project", tag: "#project/{{slug}}" });
```

## 行內任務
- [ ] 第一步 #project/{{slug}} ➕ {{date}}

## 筆記


## 紀錄
- {{date}} 建立。
