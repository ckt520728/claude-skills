// Reusable Cognitive Battery Headless Simulation Runner (Node.js)
// Part of cognitive_task_pilot_skill
//
// 用法（在實驗專案根目錄執行，專案需有 tests/helpers/run-task.mjs 與 web/js/core/rng.js）：
//   import { runBatterySimulation } from '<skill-dir>/scripts/simulate_battery_template.mjs';
//   await runBatterySimulation({ projectRoot: process.cwd(), taskModules: { A01 }, taskIds: ['A01'],
//     responders: { A01: (req, plan, ctx) => ({ value: plan.stimulus.correct_response, rt_ms: 450 }) } });
//
// 規則（2026-10-21 稽核）：
// - responder 簽名是 (req, plan)：條件在 plan.condition、刺激在 plan.stimulus（不是 info.trial）。
// - 每個 RT 加試次層級高斯雜訊（預設 SD 40 ms）；正確率用機率。否則每位 SIM 的 summary 相同，SD = 0。
// - summary 保持 summarize 原樣，不補寫假說指標。
// - 組間設計用 overrides(i) 分派（例如 i 奇數 misled、偶數 control）。
import { writeFileSync, mkdirSync, existsSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

export async function runBatterySimulation({
  projectRoot = process.cwd(),
  taskModules = {},
  taskIds = [],
  responders = {},          // { [taskId]: (req, plan, { rng, ability, gain }) => answer | undefined }
  overrides = {},           // { [taskId]: object | (i) => object }
  presets = {},             // { [taskId]: 'demo' | 'full' }
  participantCount = 10,
  outDir = 'output/battery-pilot-10',
  preset = 'demo',
  baseSeed = 2026102100,
  rtNoiseSd = 40,
}) {
  const imp = (p) => import(pathToFileURL(path.join(projectRoot, p)).href);
  const { runTaskHeadless } = await imp('tests/helpers/run-task.mjs');
  const { validateSession } = await imp('tests/helpers/validate.mjs');
  const { createRng } = await imp('web/js/core/rng.js');
  if (!existsSync(outDir)) mkdirSync(outDir, { recursive: true });

  const allSessions = [], allTrials = [], executionAudit = [];
  for (let i = 1; i <= participantCount; i++) {
    const pid = `SIM${String(i).padStart(2, '0')}`;
    const personRng = createRng(baseSeed + i);
    const ability = (personRng.random() - 0.5) * 0.16;
    const gain = 0.8 + personRng.random() * 0.4;
    const participantSessions = [];

    for (const tid of taskIds) {
      const mod = taskModules[tid];
      if (!mod) { console.warn(`Module for task ${tid} not provided, skipping.`); continue; }
      const rng = createRng(baseSeed + i * 100 + parseInt(tid.replace(/\D/g, '') || '0', 10));
      const noise = rng.fork('rt-noise');
      const custom = responders[tid];
      const responder = (req, plan) => {
        const r = custom ? custom(req, plan, { rng, ability, gain }) : undefined;
        if (r && Number.isFinite(r.rt_ms) && !r.timedOut) {
          const z = Math.sqrt(-2 * Math.log(1 - noise.random())) * Math.cos(2 * Math.PI * noise.random());
          r.rt_ms = Math.max(150, r.rt_ms + rtNoiseSd * z);
        }
        return r; // undefined → 執行器的預設作答
      };
      const ov = typeof overrides[tid] === 'function' ? overrides[tid](i) : (overrides[tid] || {});
      const session = await runTaskHeadless(mod, { preset: presets[tid] || preset, seed: i, participant_id: pid, responder, overrides: ov });
      Object.assign(session, { session_id: `pilot-${pid}-${tid}`, data_source: 'simulation' });
      session.simulation_provenance = { runner: 'cognitive_task_pilot_skill', ability, gain, rt_noise_sd: rtNoiseSd, ui_executed: false };
      const val = validateSession(session);
      if (!val.ok) throw new Error(`Session validation failed for ${pid} ${tid}: ${JSON.stringify(val.errors)}`);

      participantSessions.push(session);
      allSessions.push(session);
      for (const t of session.trials || []) {
        allTrials.push({
          participant_id: pid, task_id: tid, trial_index: t.trial_index, is_practice: t.is_practice,
          condition: JSON.stringify(t.condition || {}), response: JSON.stringify(t.response?.value ?? null),
          rt_ms: t.response?.rt_ms ?? null, correct: t.correct ?? null,
        });
      }
      executionAudit.push({ participant_id: pid, task_id: tid, schema_valid: val.ok, trials: session.trials?.length || 0 });
    }
    writeFileSync(path.join(outDir, `${pid}.json`), JSON.stringify(participantSessions, null, 2), 'utf-8');
    console.log(`[OK] ${pid}: ${participantSessions.length} tasks.`);
  }

  writeFileSync(path.join(outDir, 'sessions.json'), JSON.stringify(allSessions), 'utf-8');
  writeFileSync(path.join(outDir, 'execution-audit.json'), JSON.stringify(executionAudit, null, 2), 'utf-8');
  if (allTrials.length) {
    const headers = Object.keys(allTrials[0]);
    writeFileSync(path.join(outDir, 'trials.csv'), [headers.join(','), ...allTrials.map((r) => headers.map((h) => JSON.stringify(r[h] ?? '')).join(','))].join('\n'), 'utf-8');
  }
  console.log(`Simulation complete: ${allSessions.length} sessions, ${allTrials.length} trials -> ${outDir}`);
  return { sessions: allSessions, audit: executionAudit };
}
