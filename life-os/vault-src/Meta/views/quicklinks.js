// Life OS quick links (port of Compass Meta/views/quicklinks.js).
// Jump to today / this week / this quarter / this retreat, creating the note from its
// template if it does not exist yet. That replaces Templater + Periodic Notes, neither of
// which this vault has: the template's {{placeholders}} are filled here, in code.
// Creating a note never overwrites one: an existing file is only opened.
// Usage: await dv.view("Life OS/Meta/views/quicklinks")
const cfg = dv.page("Life OS/Meta/Compass Config") || {};
const DAILY = cfg.daily_folder || cfg.daily_note_folder || "每日筆記";
const WEEKLY = cfg.weekly_folder || "Life OS/01 Journal/Weekly";
const QUARTERLY = cfg.quarterly_folder || "Life OS/01 Journal/Quarterly";
const RETREATS = cfg.retreat_folder || "Life OS/02 Retreats";
const PROJECTS = cfg.projects_folder || "Life OS/04 Projects";
const PEOPLE = cfg.people_folder || "Life OS/05 People";
const root = dv.container.createEl("div", { cls: "lifeos-widget" });
const notice = m => { try { new Notice(m, 6000); } catch (e) { console.log("[LifeOS]", m); } };

const slug = s => String(s).trim().toLowerCase().replace(/[\s\/\\#,.:;!?()\[\]{}"'`]+/g, "-").replace(/(^-|-$)/g, "");
function fill(text, title, when) {
  const m = when || moment();
  const wk = m.clone().startOf("week");
  const vars = {
    title, date: m.format("YYYY-MM-DD"), week: m.format("gggg-[W]ww"), quarter: m.format("YYYY-[Q]Q"),
    prev_week: m.clone().subtract(1, "week").format("gggg-[W]ww"), next_week: m.clone().add(1, "week").format("gggg-[W]ww"),
    week_start: wk.format("YYYY-MM-DD"), week_end: wk.clone().add(6, "day").format("YYYY-MM-DD"),
    q_start: m.clone().startOf("quarter").format("YYYY-MM-DD"), q_end: m.clone().endOf("quarter").format("YYYY-MM-DD"),
    slug: slug(title),
    // Retreat properties come from the SSOT, never from the template (invariant 7).
    wheel_props: (cfg.wheel_areas || []).map(w => `${(w && (w.id || w.key)) || w}:`).join("\n"),
  };
  return text.replace(/\{\{(\w+)\}\}/g, (all, k) => (k in vars ? vars[k] : all));
}
async function openOrCreate(folder, name, template) {
  const path = `${folder}/${name}.md`;
  let f = app.vault.getAbstractFileByPath(path);
  if (!f) {
    const tf = app.vault.getAbstractFileByPath(`Templates/${template}.md`);
    if (!tf) { notice(`找不到模板 Templates/${template}.md，請先執行 deploy。`); return; }
    if (!app.vault.getAbstractFileByPath(folder)) { try { await app.vault.createFolder(folder); } catch (e) {} }
    f = await app.vault.create(path, fill(await app.vault.read(tf), name));
    notice(`已建立 ${path}`);
  }
  await app.workspace.getLeaf(false).openFile(f);
}
async function askName(label) {
  const qa = app.plugins && app.plugins.plugins && app.plugins.plugins.quickadd;
  if (qa && qa.api && typeof qa.api.inputPrompt === "function") return qa.api.inputPrompt(label);
  notice("需要 QuickAdd 外掛才能輸入名稱。"); return null;
}

const now = moment();
const p = root.createEl("p");
p.appendText("前往：");
const jumps = [
  ["今天", () => app.workspace.openLinkText(`${DAILY}/${now.format("YYYY-MM-DD")}`, "", false)],
  [`本週 ${now.format("gggg-[W]ww")}`, () => openOrCreate(WEEKLY, now.format("gggg-[W]ww"), "週記 Life OS")],
  [`本季 ${now.format("YYYY-[Q]Q")}`, () => openOrCreate(QUARTERLY, now.format("YYYY-[Q]Q"), "季記 Life OS")],
  ["本季退修", () => openOrCreate(RETREATS, `${now.format("YYYY-[Q]Q")} 個人退修`, "個人退修 Life OS")],
];
jumps.forEach(([lab, fn], i) => {
  if (i) p.appendText("　·　");
  const a = p.createEl("a", { text: lab, cls: "internal-link" });
  a.addEventListener("click", e => { e.preventDefault(); fn(); });
});

const wrap = root.createEl("div");
wrap.style.cssText = "display:flex;flex-wrap:wrap;gap:.5em";
const buttons = [
  ["📥 收件（Ctrl+Shift+I）", () => runChoice("Life OS 收件")],
  ["🌙 夜間評分（Ctrl+Shift+Q）", () => runChoice("Life OS 夜間評分")],
  ["📁 新專案", async () => { const n = await askName("專案名稱"); if (n) openOrCreate(PROJECTS, n.trim(), "專案 Life OS"); }],
  ["👤 新人物", async () => { const n = await askName("人物名稱"); if (n) openOrCreate(PEOPLE, n.trim(), "人物 Life OS"); }],
];
function runChoice(name) {
  // Resolved by NAME at click time, so QuickAdd ids may change freely.
  const qa = app.plugins && app.plugins.plugins && app.plugins.plugins.quickadd;
  const c = qa && qa.settings && (qa.settings.choices || []).find(x => (x.name || "") === name);
  if (!c || !app.commands.executeCommandById(`quickadd:choice:${c.id}`))
    notice(`QuickAdd 裡找不到「${name}」這個選項（或沒勾選成指令）。見 Life OS/Guide/使用手冊 第 1 章。`);
}
for (const [lab, fn] of buttons) wrap.createEl("button", { text: lab }).addEventListener("click", fn);
