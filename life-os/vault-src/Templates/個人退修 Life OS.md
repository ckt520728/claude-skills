---
type: retreat
quarter: {{quarter}}
date: {{date}}
{{wheel_props}}
tags:
  - retreat
---
# {{title}}

一季一次，一整天（或幾個小時），全部寫在這一則。上游 Mike Schmitz：「你不需要去森林小屋。
你需要的是幾個小時、一份文件，以及真的回答困難問題的意願。」

## 1. 回顧人生主題與核心價值
![[人生主題#主題]]
![[核心價值#價值]]
還貼切嗎？哪裡要改？（要改就去原筆記改，並在它的「檢視紀錄」加一行。）
- 

## 2. 回顧這一季的日記
```dataviewjs
await dv.view("Life OS/Meta/views/dailyquestions", { from: moment("{{date}}").subtract(90, "days").format("YYYY-MM-DD"), to: "{{date}}" });
```
重讀幾篇讓你印象深的日記，把你自己的話抄幾句在這裡：
- 

## 3. 人生輪
在上方屬性填 1–10 分：每個領域「現在有多滿意」。
```dataviewjs
await dv.view("Life OS/Meta/views/wheel", { page: dv.current().file.path });
```
未來 90 天要照顧的**一個**領域：

## 4. 回顧（兩段）
### 這一季發生了什麼
- 
### 開始 / 停止 / 繼續
| 開始 | 停止 | 繼續 |
|---|---|---|
|  |  |  |

## 5. 下一季意圖
最多 3 個，每個都要能追溯到上面選的領域或核心價值。
1. 
2. 
3. 

## 6. 理想的一週
打開 [[理想的一週]]：上面的意圖，時間在哪裡？
- 

## 7. 跟上一次退修比
```dataview
LIST FROM "Life OS/02 Retreats" WHERE type = "retreat" AND file.name != this.file.name SORT file.name DESC LIMIT 4
```
「兩年前你自己寫的字盯著你看的時候，你沒辦法騙自己。」我是真的在改變，還是只是換句話重寫同一批目標？
- 
