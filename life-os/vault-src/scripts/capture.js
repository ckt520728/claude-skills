/**
 * capture.js — Life OS 收件（QuickAdd User Script）
 *
 * Compass 的四個捕捉（日記、小勝、感恩、任務）合成一個熱鍵：先選類型，再打一行字。
 *
 *   📥 收件  -> Life OS/08 Tasks/任務總表.md 的「## 收件匣」，格式 `- [ ] 文字 ➕ 今天`
 *   📝 日記 / 🏆 小勝 / 🙏 感恩 -> 今天的每日筆記，追加在對應標題底下
 *
 * GTD 的 Capture 階段不做任何判斷 —— 寫下來就好。釐清（可行動嗎？哪一類？）是之後
 * `python scripts/triage.py` 用 JEV 決策層做的事，不在這裡。
 *
 * 規則：只追加，不改、不刪任何既有的字（invariant 2）。標題不存在就在檔尾新增標題。
 * 不碰 🏥 臨床 區塊。
 */

const CONFIG_PATH = "Life OS/Meta/Compass Config.md";

module.exports = async function capture(params) {
  const { app, quickAddApi } = params;
  const notice = (m, ms) => {
    try { const N = (params.obsidian && params.obsidian.Notice) || Notice; new N(m, ms || 5000); }
    catch (e) { console.log("[LifeOS]", m); }
  };
  if (!quickAddApi || typeof quickAddApi.inputPrompt !== "function" || typeof quickAddApi.suggester !== "function") {
    notice("❌ QuickAdd 沒有提供 inputPrompt / suggester，請更新 QuickAdd。", 10000);
    return;
  }
  const moment = window.moment;
  const cf = app.vault.getAbstractFileByPath(CONFIG_PATH);
  const fm = (cf && (app.metadataCache.getFileCache(cf) || {}).frontmatter) || {};
  const folder = fm.daily_note_folder || fm.daily_folder || "每日筆記";
  const tasksPath = fm.tasks_file || "Life OS/08 Tasks/任務總表.md";
  const H = {
    journal: fm.journal_heading || "📝 日記",
    wins: fm.wins_heading || "🏆 今日小勝",
    gratitude: fm.gratitude_heading || "🙏 感恩",
  };

  const kinds = ["📥 收件（要做的事、想法、任何東西）", `📝 日記`, `🏆 小勝`, `🙏 感恩`];
  const keys = ["inbox", "journal", "wins", "gratitude"];
  const kind = await quickAddApi.suggester(kinds, keys);
  if (!kind) return;
  const text = await quickAddApi.inputPrompt(kinds[keys.indexOf(kind)], "一行就好");
  if (!text || !String(text).trim()) return;
  const t = String(text).trim().replace(/\n+/g, " ");
  const today = moment().format("YYYY-MM-DD");

  // Insert `line` as the last line of the section under `## heading`; append the heading at
  // the end if it does not exist. Existing lines are never changed.
  const insertUnder = (content, heading, line) => {
    const lines = content.split("\n");
    const h = lines.findIndex(l => l.trim() === `## ${heading}`);
    if (h === -1) return content.replace(/\s*$/, "") + `\n\n## ${heading}\n\n${line}\n`;
    let end = lines.length;
    for (let i = h + 1; i < lines.length; i++) if (/^(## |---\s*$)/.test(lines[i])) { end = i; break; }
    let at = end;
    while (at > h + 1 && lines[at - 1].trim() === "") at--;
    lines.splice(at, 0, line);
    return lines.join("\n");
  };
  const write = async (file, fn) => {
    if (app.vault.process) await app.vault.process(file, fn);
    else await app.vault.modify(file, fn(await app.vault.read(file)));
  };

  if (kind === "inbox") {
    const f = app.vault.getAbstractFileByPath(tasksPath);
    if (!f) { notice(`❌ 找不到 ${tasksPath}，請先執行 deploy。`, 10000); return; }
    await write(f, c => insertUnder(c, "收件匣", `- [ ] ${t} ➕ ${today}`));
    notice("📥 已放進收件匣。之後再釐清。");
    return;
  }

  // Daily note: same skeleton nightly.js creates (keep the two in step).
  const path = `${folder}/${today}.md`;
  let f = app.vault.getAbstractFileByPath(path);
  if (!f) {
    if (!app.vault.getAbstractFileByPath(folder)) { try { await app.vault.createFolder(folder); } catch (e) {} }
    const clin = fm.clinical_heading || "🏥 臨床", refl = fm.reflection_heading || "💡 今日反思";
    const prio = fm.priority_heading || "明日優先事項";
    f = await app.vault.create(path,
      `---\ntitle: ${today}\ndate: ${today}\ntype: 每日筆記\ntags:\n  - 每日筆記\n---\n\n# ${today}\n\n---\n\n` +
      `## ${clin}\n\n-\n\n---\n\n## ${H.journal}\n\n## ${H.wins}\n\n## ${H.gratitude}\n\n---\n\n` +
      `## ${refl}\n\n>\n\n---\n\n## ${prio}\n\n1.\n2.\n3.\n`);
  }
  const stamp = kind === "journal" ? `- ${moment().format("HH:mm")} ${t}` : `- ${t}`;
  await write(f, c => insertUnder(c, H[kind], stamp));
  notice(`${kinds[keys.indexOf(kind)]}：已記下。`);
};
