---
type: weekly
week: {{week}}
quarter: {{quarter}}
tags:
  - weekly
---
« [[{{prev_week}}|上週]] · [[{{quarter}}|本季]] · [[指南針儀表板]] · [[{{next_week}}|下週]] »

# {{week}}（{{week_start}} → {{week_end}}）

> [!info]- 本季意圖
> ![[{{quarter}}#本季意圖]]

## 本週意圖
這週如果做到，就能推動本季意圖的 3 件事。
1. 
2. 
3. 

## 理想週檢查
看一眼 [[理想的一週]]。上面這 3 件事的時間，這週實際放在哪裡？現在就調行事曆，不要等到週四。
- 

## 本週到期
```dataviewjs
const s = moment("{{week_start}}"), e = moment("{{week_end}}").endOf("day");
dv.taskList(dv.pages('"Life OS" or "每日筆記" or "創作庫"').file.tasks
  .where(t => !t.completed && t.due && moment(t.due.toISODate()).isBetween(s, e, null, "[]")), true);
```

## 週回顧（週五或週日）
每天的努力分數與習慣。數字由程式算，不要自己心算。
```dataviewjs
await dv.view("Life OS/Meta/views/week", { week: dv.current().file.name });
```

### 這週順利的

### 這週不順的

### 本週小勝
```dataviewjs
const s = "{{week_start}}", e = "{{week_end}}";
const cfg = dv.page("Life OS/Meta/Compass Config") || {};
const H = cfg.wins_heading || "🏆 今日小勝";
for (const p of dv.pages(`"${cfg.daily_note_folder || "每日筆記"}"`).where(p => p.file.name >= s && p.file.name <= e).sort(p => p.file.name)) {
  const wins = p.file.lists.where(l => l.section && String(l.section.subpath) === H && l.text.trim());
  if (wins.length) { dv.paragraph(`**${p.file.name}**`); dv.list(wins.text); }
}
```

> 要 AI 幫你做週回顧：在 Claude Code 說「讀 `Life OS/Prompts/03 每週回顧.md`，照它做」。
