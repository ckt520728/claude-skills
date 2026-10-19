// Life OS Boards (port of Compass Meta/views/boards.js): every Kanban board under Life OS/
// with card counts per lane. Usage:
//   await dv.view("Life OS/Meta/views/boards")                   all lanes
//   await dv.view("Life OS/Meta/views/boards", { compact: true })  one line per board
const cfg = dv.page("Life OS/Meta/Compass Config") || {};
const FOLDER = (input && input.folder) || "Life OS";
const COMPACT = !!(input && input.compact);
const DONE = String(cfg.board_done_lanes || "完成,已發表,封存,Done").split(",").map(s => s.trim().toLowerCase());
const boards = dv.pages(`"${FOLDER}"`).where(p => typeof (p.file.frontmatter || {})["kanban-plugin"] === "string").sort(p => p.file.path).array();
const root = dv.container.createEl("div", { cls: "lifeos-widget" });
const link = (parent, b) => {
  const a = parent.createEl("a", { text: b.file.name, cls: "internal-link", attr: { href: b.file.path, "data-href": b.file.path } });
  a.addEventListener("click", e => { e.preventDefault(); app.workspace.openLinkText(b.file.path, "", false); });
};
if (!boards.length) {
  root.createEl("p", { text: "找不到看板（frontmatter 有 kanban-plugin 的筆記）。需先在設定開啟 Kanban 外掛。" });
} else {
  const parsed = [];
  for (const b of boards) {
    let text = "";
    try { text = await app.vault.cachedRead(app.vault.getAbstractFileByPath(b.file.path)); } catch (e) { continue; }
    text = text.replace(/^---[\s\S]*?---\n/, "");
    for (const cut of ["\n%% kanban:settings", "\n***"]) { const i = text.indexOf(cut); if (i !== -1) text = text.slice(0, i); }
    const lanes = []; let cur = null;
    for (const line of text.split("\n")) {
      const h = line.match(/^##\s+(.*)$/);
      if (h) { cur = { name: h[1].trim(), cards: [] }; lanes.push(cur); continue; }
      const c = line.match(/^- \[( |x)\]\s+(.*)$/);
      if (c && cur) cur.cards.push({ done: c[1] === "x", text: c[2].trim() });
    }
    const isDone = l => DONE.includes(l.name.toLowerCase());
    parsed.push({ b, lanes, open: lanes.filter(l => !isDone(l)).reduce((s, l) => s + l.cards.length, 0),
                  done: lanes.filter(isDone).reduce((s, l) => s + l.cards.length, 0), isDone });
  }
  if (COMPACT) {
    const t = root.createEl("table", { cls: "lifeos-table" });
    const h = t.createEl("thead").createEl("tr");
    for (const c of ["看板", "進行中", "完成", "各欄"]) h.createEl("th", { text: c });
    const tb = t.createEl("tbody");
    for (const x of parsed) {
      const r = tb.createEl("tr");
      link(r.createEl("td"), x.b);
      r.createEl("td", { text: String(x.open) });
      r.createEl("td", { text: String(x.done) });
      r.createEl("td", { text: x.lanes.filter(l => !x.isDone(l)).map(l => `${l.name} ${l.cards.length}`).join(" · ") });
    }
  } else {
    for (const x of parsed) {
      const h = root.createEl("h4"); link(h, x.b); h.appendText(`（進行中 ${x.open}，完成 ${x.done}）`);
      const t = root.createEl("table", { cls: "lifeos-table" });
      const hr = t.createEl("thead").createEl("tr");
      for (const l of x.lanes) hr.createEl("th", { text: `${l.name}（${l.cards.length}）` });
      const row = t.createEl("tbody").createEl("tr");
      for (const l of x.lanes) {
        const td = row.createEl("td"); td.style.verticalAlign = "top";
        for (const c of l.cards.slice(0, 6)) {
          const d = td.createEl("div", { text: c.text.replace(/@\{[^}]*\}/g, "").replace(/\[\[|\]\]/g, "").trim() });
          d.style.fontSize = "0.85em"; if (c.done) d.style.opacity = "0.5";
        }
        if (l.cards.length > 6) td.createEl("div", { text: `還有 ${l.cards.length - 6} 張` }).style.opacity = "0.6";
      }
    }
  }
}
