/**
 * nightly.js — Life OS 夜間評分（QuickAdd User Script）
 *
 * 設計約束（來自 UNKNOWNS.md）：
 *   - 零新外掛：只用 QuickAdd + Obsidian 原生 API。不需要 Dataview，不需要 Templater。
 *   - 只追加不覆寫：既有內容一個字都不動（invariant 2）。
 *   - 臨床區塊：clinical_access: derived —— 只在本機數筆數，只把數字寫進 frontmatter（U4）。
 *   - API 全部先偵測再用：QuickAdd 的 API 介面未經實機驗證（U2），
 *     缺什麼就明確說缺什麼，不要丟一個沒人看得懂的 stack trace。
 *
 * 綁定方式見 Life OS/00 開始這裡.md
 */

const CONFIG_PATH = "Life OS/Meta/Compass Config.md";

module.exports = async function nightly(params) {
  const { app, quickAddApi } = params;

  // Notice 本身也要偵測：QuickAdd 傳不傳 obsidian module 沒有實機驗證過（U2）。
  // 三層後備 —— params.obsidian、全域 Notice、最後 console。
  const notice = (msg, ms) => {
    try {
      const N = (params.obsidian && params.obsidian.Notice) ||
                (typeof Notice !== "undefined" ? Notice : null);
      if (N) { new N(msg, ms || 6000); return; }
    } catch (e) { /* fall through */ }
    console.log("[LifeOS]", msg);
  };

  // ---- 0. API 偵測 ------------------------------------------------------
  // 缺任何一個就停下來講清楚，不要半路失敗。
  if (!quickAddApi || typeof quickAddApi.inputPrompt !== "function") {
    notice("❌ QuickAdd 沒有提供 inputPrompt()。請確認 QuickAdd 已更新到近期版本。", 10000);
    return;
  }
  const hasWideInput = typeof quickAddApi.wideInputPrompt === "function";
  const hasYesNo = typeof quickAddApi.yesNoPrompt === "function";
  const canWriteFrontmatter =
    app.fileManager && typeof app.fileManager.processFrontMatter === "function";

  const moment = window.moment;
  if (!moment) {
    notice("❌ 找不到 window.moment，無法計算日期。", 10000);
    return;
  }

  // ---- 1. 讀 SSOT ------------------------------------------------------
  const configFile = app.vault.getAbstractFileByPath(CONFIG_PATH);
  if (!configFile) {
    notice(`❌ 找不到設定檔：${CONFIG_PATH}`, 10000);
    return;
  }
  const fm = (app.metadataCache.getFileCache(configFile) || {}).frontmatter;
  if (!fm) {
    notice("❌ 設定檔讀不到 frontmatter。檔案開頭是否有 --- ？", 10000);
    return;
  }

  // `questions` with key/text is upstream Compass's shape; accepted so its config drops in.
  const questions = Array.isArray(fm.dq_questions) ? fm.dq_questions
    : (Array.isArray(fm.questions) ? fm.questions.map(q => (typeof q === "string" ? { id: q, prompt: q }
        : { id: q.key || q.id, prompt: q.text || q.prompt })) : []);
  const habits = Array.isArray(fm.habits) ? fm.habits : [];
  if (questions.length === 0 && habits.length === 0) {
    notice("⚠️ 設定檔裡沒有任何 dq_questions 或 habits。先去 Compass Config 填題目。", 10000);
    return;
  }

  const folder = fm.daily_note_folder || "每日筆記";
  const dateFmt = fm.daily_note_format || "YYYY-MM-DD";
  const reflectionHeading = fm.reflection_heading || "💡 今日反思";
  const clinicalHeading = fm.clinical_heading || "🏥 臨床";
  const priorityHeading = fm.priority_heading || "明日優先事項";

  const todayStr = moment().format(dateFmt);
  const dailyPath = `${folder}/${todayStr}.md`;

  // ---- 2. 問分數 -------------------------------------------------------
  // 空白 = 跳過這題（不寫這個欄位）。允許跳過是刻意的：
  // 半夜累到只想答兩題時，兩題也要能存檔，否則今晚就整個放棄了。
  const scores = {};
  let answered = 0;

  for (const q of questions) {
    if (!q || !q.id) continue;
    const raw = await quickAddApi.inputPrompt(
      `${q.prompt || q.id}`,
      "1–10 分，直接按 Enter 可跳過"
    );
    if (raw === undefined || raw === null) {
      notice("⚠️ 已取消，今晚沒有寫入任何資料。");
      return; // Esc = 整個取消
    }
    const trimmed = String(raw).trim();
    if (trimmed === "") continue; // 跳過這題
    const n = parseInt(trimmed, 10);
    if (isNaN(n)) continue;
    scores[q.id] = Math.min(10, Math.max(1, n));
    answered++;
  }

  // ---- 3. 問習慣 -------------------------------------------------------
  for (const h of habits) {
    if (!h || !h.id) continue;
    const label = h.name || h.id;
    let done;
    if (hasYesNo) {
      done = await quickAddApi.yesNoPrompt(label, "今天做到了嗎？");
      if (done === undefined) { notice("⚠️ 已取消。"); return; }
    } else {
      const raw = await quickAddApi.inputPrompt(`${label}（y / n，Enter 跳過）`, "y");
      if (raw === undefined || raw === null) { notice("⚠️ 已取消。"); return; }
      const t = String(raw).trim().toLowerCase();
      if (t === "") continue;
      done = (t === "y" || t === "yes" || t === "1" || t === "true");
    }
    scores[h.id] = !!done;
    answered++;
  }

  if (answered === 0) {
    notice("⚠️ 全部跳過了，沒有東西可以寫入。");
    return;
  }

  // ---- 4. 問一句反思（可空）--------------------------------------------
  const reflectPrompt = "今天最重要的一個突破或一個卡點（可留空）";
  const reflection = hasWideInput
    ? await quickAddApi.wideInputPrompt("今日反思", reflectPrompt)
    : await quickAddApi.inputPrompt("今日反思", reflectPrompt);
  // 這裡不檢查取消：分數已經收好了，反思留空也要存。

  // ---- 5. 找到或建立今天的筆記 -----------------------------------------
  // 建立時沿用使用者原本的日記結構（臨床 / 反思 / 明日優先），
  // 不另外發明一套格式。
  let dailyFile = app.vault.getAbstractFileByPath(dailyPath);
  if (!dailyFile) {
    const folderObj = app.vault.getAbstractFileByPath(folder);
    if (!folderObj) {
      try { await app.vault.createFolder(folder); } catch (e) { /* 已存在則忽略 */ }
    }
    const initial =
      `---\n` +
      `title: ${todayStr}\n` +
      `date: ${todayStr}\n` +
      `type: 每日筆記\n` +
      `tags:\n  - 每日筆記\n` +
      `---\n\n` +
      `# ${todayStr}\n\n---\n\n` +
      `## ${clinicalHeading}\n\n-\n\n---\n\n` +
      // Compass capture sections (capture.js appends here). Keep in step with capture.js.
      `## ${fm.journal_heading || "📝 日記"}\n\n## ${fm.wins_heading || "🏆 今日小勝"}\n\n` +
      `## ${fm.gratitude_heading || "🙏 感恩"}\n\n---\n\n` +
      `## ${reflectionHeading}\n\n>\n\n---\n\n` +
      `## ${priorityHeading}\n\n1.\n2.\n3.\n`;
    dailyFile = await app.vault.create(dailyPath, initial);
  }

  // ---- 5b. 臨床負荷：本機推導，只留數字 --------------------------------
  // clinical_access: derived（使用者 2026-09-29 決定）
  //
  // 這一段在 Obsidian 內部讀 `## 🏥 臨床` 的內文，數一下待處理筆數，
  // 然後**只把數字**寫進 frontmatter。原始文字從頭到尾沒有離開這台機器，
  // 也沒有被寫到別的地方去。
  //
  // 教練 prompt 只讀 frontmatter，所以它看得到「待處理 6 例」，
  // 永遠看不到那 6 例是誰。邊界是程式結構，不是一句叮嚀。
  const clinicalAccess = fm.clinical_access || "never";
  const clinicalLocalOK = ["local", "derived", "full"].includes(clinicalAccess);
  let clinicalPending = null;
  let clinicalLoad = null;

  if (clinicalLocalOK) {
    try {
      const raw = await app.vault.read(dailyFile);
      const secRe = new RegExp(`^##\\s*${escapeRe(clinicalHeading)}\\s*$`, "m");
      const hit = raw.match(secRe);
      if (hit) {
        const rest = raw.slice(hit.index + hit[0].length);
        const nextH2 = rest.search(/^##\s+/m);
        const section = nextH2 === -1 ? rest : rest.slice(0, nextH2);

        let cases = 0;
        for (const line of section.split("\n")) {
          const m = line.match(/^\s*[-*+]\s+(.*)$/);
          if (m) {
            const body = m[1].trim();
            if (body && !["-", "—", "…"].includes(body)) cases++;
          }
        }
        clinicalPending = cases;
        clinicalLoad = cases <= 0 ? 1 : (cases <= 2 ? 2 : (cases <= 5 ? 3 : (cases <= 9 ? 4 : 5)));
        // `section` 與 `raw` 在這裡就結束生命週期，沒有被回傳、記錄或傳送。
      }
    } catch (e) {
      // 推導失敗不該讓整個夜間流程掛掉 —— 分數比這個重要。
      console.error("[LifeOS] 臨床負荷推導失敗（不影響評分）", e);
    }
  }

  // ---- 6. 寫 frontmatter ----------------------------------------------
  // processFrontMatter 是原生 API，會保留內文與註解，不會把檔案重寫壞。
  let frontmatterOK = false;
  if (canWriteFrontmatter) {
    try {
      await app.fileManager.processFrontMatter(dailyFile, (f) => {
        for (const k of Object.keys(scores)) f[k] = scores[k];
        f.type = f.type || "每日筆記";
        f.lifeos_scored_at = moment().format("YYYY-MM-DD HH:mm");
        // 只有數字會進來。這兩個欄位是教練唯一看得到的臨床資訊。
        if (clinicalPending !== null) {
          f.clinical_pending = clinicalPending;
          f.clinical_load = clinicalLoad;
        }
      });
      frontmatterOK = true;
    } catch (e) {
      console.error("[LifeOS] processFrontMatter 失敗", e);
    }
  }

  // ---- 7. 追加到反思區塊 ----------------------------------------------
  // 只追加。既有文字不動。臨床區塊完全不碰。
  const stamp = moment().format("HH:mm");
  const lines = [];
  if (reflection && String(reflection).trim() !== "") {
    lines.push(`- **${stamp} 夜間反思**：${String(reflection).trim()}`);
  }
  if (!frontmatterOK) {
    // 後備路徑：frontmatter 寫不進去時，至少把分數以純文字留下來，
    // 今晚的資料不能因為 API 問題就消失。
    const pairs = Object.keys(scores).map((k) => `${k}=${scores[k]}`).join(", ");
    lines.push(`- **${stamp} 評分**（frontmatter 寫入失敗，暫存於此）：${pairs}`);
  }

  if (lines.length > 0) {
    const content = await app.vault.read(dailyFile);
    const block = lines.join("\n");
    const headingRe = new RegExp(`^##\\s*${escapeRe(reflectionHeading)}\\s*$`, "m");
    let next;
    const m = content.match(headingRe);
    if (m) {
      const at = m.index + m[0].length;
      next = content.slice(0, at) + `\n\n${block}` + content.slice(at);
    } else {
      next = content.replace(/\s*$/, "") + `\n\n## ${reflectionHeading}\n\n${block}\n`;
    }
    await app.vault.modify(dailyFile, next);
  }

  // ---- 8. 回報 --------------------------------------------------------
  const scored = Object.keys(scores).length;
  notice(
    `🟢 已寫入 ${todayStr}：${scored} 個欄位` +
    (frontmatterOK ? "" : "（frontmatter 失敗，已存成文字）"),
    8000
  );
};

function escapeRe(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
