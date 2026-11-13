// Life OS task dashboard: Compass's Task Dashboard, built on Dataview's task index instead of
// the Tasks plugin (not installed here). Dataview reads the same emoji format:
//   📅 due   ⏳ scheduled   ➕ created   ⏫ high priority   #project/<slug>  #p/<slug>  #discuss
// Usage: await dv.view("Life OS/Meta/views/tasks", { section: "all" })
//        sections: overdue | today | week | discuss | priority | inbox | done | project | person
//        project / person also take { tag: "#project/slug" }
const cfg = dv.page("Life OS/Meta/Compass Config") || {};
const TASKS = String(cfg.tasks_file || "Life OS/08 Tasks/任務總表.md").replace(/\.md$/, "");
const SCOPE = '"Life OS" or "每日筆記" or "創作庫"';
const today = moment().startOf("day");
const due = t => t.due ? moment(t.due.toISODate ? t.due.toISODate() : String(t.due)) : null;
const sched = t => t.scheduled ? moment(t.scheduled.toISODate ? t.scheduled.toISODate() : String(t.scheduled)) : null;
const open = dv.pages(SCOPE).file.tasks.where(t => !t.completed && t.text.trim());
const sec = (input && input.section) || "all";
const want = s => sec === "all" || sec === s;
const show = (title, list, empty) => {
  if (sec === "all") dv.header(3, title);
  if (list.length) dv.taskList(list, false); else dv.paragraph(`_${empty}_`);
};

if (want("overdue")) show("⏰ 已逾期", open.where(t => due(t) && due(t).isBefore(today)).sort(t => due(t).valueOf()), "沒有逾期的事。");
if (want("today")) show("📅 今天", open.where(t => (due(t) && due(t).isSame(today, "day")) || (sched(t) && !sched(t).isAfter(today))), "今天沒有排定的事。");
if (want("week")) show("🗓️ 未來 7 天", open.where(t => due(t) && due(t).isAfter(today) && due(t).diff(today, "days") <= 7).sort(t => due(t).valueOf()), "未來一週沒有到期的事。");
if (want("discuss")) {
  if (sec === "all") dv.header(3, "💬 待討論（依人）");
  const d = open.where(t => t.tags.includes("#discuss"));
  if (!d.length) dv.paragraph("_沒有待討論的事。_");
  for (const g of d.groupBy(t => (t.tags.find(x => x.startsWith("#p/")) || "（未指定人）"))) {
    dv.paragraph(`**${g.key}**`); dv.taskList(g.rows, false);
  }
}
if (want("priority")) show("⏫ 高優先、未排日期", open.where(t => /⏫|🔺/.test(t.text) && !due(t)), "沒有。");
if (want("inbox")) {
  const inbox = open.where(t => t.path === `${TASKS}.md` && t.section && String(t.section.subpath || "").includes("收件匣"));
  show("📥 收件匣（尚未釐清）", inbox, "收件匣是空的。");
  if (inbox.length >= 10) dv.paragraph("收件匣超過 10 則。在終端機跑 `python scripts/triage.py`（JEV 釐清），或用 Prompts/06 任務分流。");
}
if (want("project")) show("專案任務", open.where(t => t.tags.includes(input.tag)), "還沒有標這個專案標籤的任務。");
if (want("person")) show("跟這個人有關", open.where(t => t.tags.includes(input.tag)), "還沒有。");
if (want("done")) {
  const since = today.clone().subtract(7, "days");
  show("✅ 這週完成", dv.pages(SCOPE).file.tasks.where(t => t.completed && t.completion && moment(t.completion.toISODate()).isAfter(since)), "這週還沒勾掉任何事。");
}
