// Life OS Build Order gate. Renders a view only when its layer is open; otherwise a greyed
// card with the unlock date and why. Dormant layers are shown, never hidden.
//
// Usage:
//   await dv.view("Life OS/Meta/views/gate", { layer: "habits_weekly", view: "habits", args: { days: 21 } })
//   await dv.view("Life OS/Meta/views/gate", { status: true })     // the full layer table
//
// [C] rule mirrored from lifeos/unlock.py. These two constants must equal the Python ones;
// scripts/checks.sh fails the build if they drift.
const CONSISTENCY_WINDOW = 30;
const CONSISTENCY_REQUIRED = 0.80;

const CFG = "Life OS/Meta/Compass Config";
const cfg = dv.page(CFG) || {};
const LAYERS = [
  ["journal", "每日提問與日記", 1],
  ["habits_weekly", "習慣畫布與週回顧", 31],
  ["retreat", "季度退修、人生輪、人生規劃", 61],
  ["tasks", "任務、專案、人物、GTD 歸檔", 91],
  ["writing", "創作看板", 121],
];
const legacy = { daily: "journal", weekly: "habits_weekly", quarterly: "retreat" };
const days = {};
for (const [k, , d] of LAYERS) days[k] = d;
for (const [k, v] of Object.entries(cfg.unlock_days || {})) days[legacy[k] || k] = Number(v);

const folder = cfg.daily_folder || cfg.daily_note_folder || "每日筆記";
const dq = cfg.dq_prefix || "dq_";
const today = moment().startOf("day");
const startRaw = String(cfg.start_date || "").slice(0, 10);
const start = startRaw ? moment(startRaw, "YYYY-MM-DD") : null;
const dayN = start ? today.diff(start, "days") + 1 : 0;

// Journal consistency: days with any dq_* score in the window, never counting days before start.
let first = today.clone().subtract(CONSISTENCY_WINDOW - 1, "days");
if (start && start.isAfter(first)) first = start.clone();
const denom = Math.max(0, today.diff(first, "days") + 1);
const scored = dv.pages(`"${folder}"`).where(p => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(p.file.name)) return false;
  const d = moment(p.file.name, "YYYY-MM-DD");
  if (d.isBefore(first) || d.isAfter(today)) return false;
  const fm = p.file.frontmatter || {};
  return Object.keys(fm).some(k => k.startsWith(dq) && typeof fm[k] === "number");
}).length;
const consistency = denom ? scored / denom : 0;

function state(layer) {
  if (layer === "journal") return { open: true, why: "" };
  if (!start) return { open: false, why: "設定檔缺 start_date" };
  if (dayN < days[layer]) return { open: false, why: `還有 ${days[layer] - dayN} 天` };
  if (consistency < CONSISTENCY_REQUIRED)
    return { open: false, why: `日期到了，但近 ${denom} 天只評分 ${scored} 天（${Math.round(consistency * 100)}%，需 ${CONSISTENCY_REQUIRED * 100}%）` };
  return { open: true, why: "" };
}
const dateOf = layer => start ? start.clone().add(days[layer] - 1, "days").format("YYYY-MM-DD") : "?";

const root = dv.container.createEl("div", { cls: "lifeos-widget" });
if (input && input.status) {
  root.createEl("p", { text: start ? `第 ${dayN} 天（起算 ${startRaw}）· 近 ${denom} 天評分 ${scored} 天（${Math.round(consistency * 100)}%）` : "⚠️ 設定檔缺 start_date" });
  const t = root.createEl("table", { cls: "lifeos-table" });
  const h = t.createEl("thead").createEl("tr");
  for (const c of ["", "層", "解鎖日", "狀態"]) h.createEl("th", { text: c });
  const b = t.createEl("tbody");
  for (const [k, label] of LAYERS) {
    const s = state(k), r = b.createEl("tr");
    r.createEl("td", { text: s.open ? "✅" : "💤" });
    r.createEl("td", { text: label });
    r.createEl("td", { text: `第 ${days[k]} 天 · ${dateOf(k)}` });
    r.createEl("td", { text: s.open ? "已開放" : s.why });
  }
  root.createEl("p", { text: "上游 Compass 的規則：一層一層加，上一層一致性低於 80% 就先別加下一層。" }).style.opacity = "0.6";
} else {
  const layer = (input && input.layer) || "journal";
  const s = state(layer);
  if (s.open) {
    await dv.view(`Life OS/Meta/views/${input.view}`, input.args || {});
  } else {
    const label = (LAYERS.find(l => l[0] === layer) || [layer, layer])[1];
    const card = root.createEl("div");
    card.style.cssText = "opacity:.55;border:1px dashed var(--background-modifier-border);border-radius:8px;padding:.6em 1em";
    card.createEl("p", { text: `💤 「${label}」第 ${days[layer]} 天（${dateOf(layer)}）解鎖 —— ${s.why}` });
    const btn = card.createEl("button", { text: "先偷看一下" });
    btn.addEventListener("click", async () => { btn.remove(); card.style.opacity = "1"; await dv.view(`Life OS/Meta/views/${input.view}`, input.args || {}); });
  }
}
