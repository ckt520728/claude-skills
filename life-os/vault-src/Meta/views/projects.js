// Life OS projects overview (Compass Projects Dashboard): every project note with its
// status, quarter, and open-task count from its #project/<slug> tag.
// Usage: await dv.view("Life OS/Meta/views/projects")
const cfg = dv.page("Life OS/Meta/Compass Config") || {};
const FOLDER = cfg.projects_folder || "Life OS/04 Projects";
const projects = dv.pages(`"${FOLDER}"`).where(p => (p.file.frontmatter || {}).type === "project").array();
const tasks = dv.pages('"Life OS" or "每日筆記" or "創作庫"').file.tasks.where(t => !t.completed).array();
if (!projects.length) {
  dv.paragraph("_還沒有專案筆記。在指南針儀表板按「📁 新專案」。_");
} else {
  const order = { active: 0, waiting: 1, someday: 2, done: 3 };
  const rows = projects.sort((a, b) => (order[a.status] ?? 9) - (order[b.status] ?? 9)).map(p => {
    const tag = `#project/${p.slug || ""}`;
    const n = tasks.filter(t => t.tags.includes(tag)).length;
    return [p.file.link, p.status || "", p.quarter || "", p.area || "", n, p.due ? String(p.due).slice(0, 10) : ""];
  });
  dv.table(["專案", "狀態", "季", "領域", "未完成任務", "期限"], rows);
}
