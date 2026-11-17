---
name: patient-care-network
description: |
  Build a hospital patient care network as a local, intranet-first clinical decision-support system in three tiers:
  - a LINE (or other messaging) patient edge for meals, CGM and proactive outreach;
  - an in-hospital FastAPI + SQLite server with deterministic risk calculators, care-gap rules, a three-ring RAG / LLM-Wiki and a guardrail;
  - desktop agentic AI (Claude Desktop, Cursor, OpenCode) connected over MCP, which can read and stage but never commit.
  Covers the architecture, the build order, safety rules (no LLM arithmetic, no doses, auto-send only for hard-coded safety text and approved templates), tested clinical engines (KFRE, FIB-4, WATCH-DM, SCORE2-Diabetes, CGM rules, AGP, five-dimensional care), the MCP surface (tools, prompts, wiki:// resources, MCP Apps ui:// panels), connecting Claude Desktop through a stdio bridge, multi-role care teams (physician, diabetes educator nurse, dietitian with a meal-review and meal↔CGM monitoring workflow, admin), personal role-scoped MCP tokens, a clip-and-paste HIS ingress (deterministic parser → import CSV) for hospitals without an HIS interface, and 46 measured pitfalls from a diabetes build on Windows.
  Use when the user asks to "build a smart diabetes care network", "patient care network", "chronic disease care network", "hospital MCP server", "desktop agentic AI + MCP for clinicians", "LINE chatbot for patients with CGM / meal photos", "organ risk dashboard (kidney/heart/liver/eye)", "care-gap agent", "RAG guardrail for clinical text", "connect Claude Desktop to a hospital MCP server", "dietitian role / dietitian review queue", "per-user MCP tokens / role-based MCP tools", "paste lab data from the HIS", "copy-paste patient data into the system", "糖尿病智慧照護網", "照護網絡", "病人照護網", "營養師", "從 HIS 貼上".
---

# Patient care network (3-tier hybrid, MCP)

Build a care network that a hospital can run on one intranet server with no GPU. Language reasoning happens in desktop MCP clients. Patient data and all clinical arithmetic stay on the server.

Reference build: *Smart Diabetes Care Network 0.3* (`ckt520728/2026-open-code`, `projects/smart-dm-care`). That build is a FastAPI app with 23 role-scoped MCP tools, four roles, a paste-from-HIS import, 63 tests and a mobile-checked dashboard. Use it as the pattern; swap the disease-specific engines for other conditions (CKD, heart failure, COPD, dementia).

## When to use this pattern

- Several hospital data silos (HIS, LIS, PACS, CGM, messaging) need one patient view and care-gap alerts.
- Clinicians want an AI copilot, but the organisation will not let an LLM compute scores, prescribe or send messages on its own.
- There is no GPU budget, and patient identifiers must not leave the intranet.

Not a fit if the goal is autonomous treatment, insulin titration or a diagnostic claim. Those need regulatory evidence (SaMD / TFDA / FDA), not a software pattern.

## Architecture

```
TIER 1  Clinic desktops: desktop agent (MCP client). Reasons and drafts only.
        │  physician / educator / dietitian, each with a personal token → role-scoped tools
        │  hospital LAN · MCP streamable HTTP · bearer token · Host allow-list
        │  clinician's own HIS screen ──copy/paste──► Import page (paste → CSV → import)
TIER 2  In-hospital server (FastAPI, Docker-able)
        │  REST + MCP gateway (RoleGate) · deterministic calculators · care-gap rules
        │  three-ring RAG spine + guardrail · SQLite→PostgreSQL · audit log
        │  outreach scheduler · reverse proxy + TLS + DMZ in production
TIER 3  Patient edge: messaging webhook (text/photo/voice) + CGM device bridge
```

The HIS stays out of reach of the server and the agent: the clinician, who can
open it, carries data across by copy and paste, and fixed rules (no LLM) turn
the text into reviewable import CSV.

Module map and data model: `references/architecture.md`.

## Hard rules (put them in AGENTS.md before writing code)

1. **No LLM arithmetic.** Every score comes from pure functions in `app/risk/`. Each result carries:
   - its inputs and any missing fields;
   - the formula version and a citation;
   - a status of `calculated`, `not_calculable` or `not_applicable`.
2. **Never impute.** A missing value makes the result `not_calculable`. In care-gap terms, *a missing result is a task, not a zero*.
3. **MCP reads and stages only.** Agents may stage a message, a summary draft, a proposed schedule or a draft task. Sending, signing, activating, resolving and writing to the EHR need a clinician session in the UI, and each is audited.
4. **Auto-send has exactly two reasons**, enforced in code with a `PermissionError` for anything else:
   - `safety_rule`: hard-coded hypoglycaemia text (Rule of 15 plus the 15-minute recheck);
   - `approved_template`: the template is physician-approved, the schedule is clinician-activated, the patient has consented, and the hour is 06–21.
5. **Guardrail before staging.** Agent prose goes through `verify_draft(text, audience, assessment)`. `blocked` text is never staged, and patient-facing text may cite only clinician-verified wiki pages.
6. **No doses and no diagnosis claims to patients.** Write "consider / review / discuss".
7. **Show uncertainty honestly.** Examples:
   - The eye result is a surveillance *priority*, not a probability.
   - KFRE is reported only when eGFR < 60.
   - SCORE2 shows its calibration region, and "not validated for <country>" when the country is not one of the regions.
8. **Synthetic data only** until security, consent, IRB and regulatory review are done. Keep a visible demo banner.
9. **Least privilege per person.** Every clinician has a role and a personal MCP token. One policy table (`ROLE_TOOLS`, `ROLE_PROMPTS`) decides what each role's agent sees, and the server enforces it; the UI only hides buttons. Audit rows name the person.
10. **Ingress text never goes to an LLM.** Pasted HIS text is parsed by fixed, testable rules, shown with its source lines, edited by the clinician, and committed through the existing import (validation + audit). The text is not stored or logged.

## Build order (each phase ends with green tests)

1. **Contract.** Write `AGENTS.md` with the hard rules, `CONTEXT.md` with domain terms and `handoffs.md`. Write ADRs for each user decision.
2. **Engines** (`app/risk/*`, pure functions plus unit tests). Verify every published equation against an *independent* implementation and a worked example before trusting it. See `references/clinical-engines.md` and `scripts/score2_diabetes.py --selftest`.
3. **Data and services.**
   - Schema with additive migrations.
   - `build_assessment(bundle)` as the single source of truth for REST, MCP and the UI.
   - CGM stream ingest, outreach scheduler, nutrition (photo, or speech → food table, with confidence routing to a dietitian).
   - Orchestrator: deterministic named agents with provenance.
   - FHIR `RiskAssessment` export.
4. **RAG safety layer.**
   - Markdown wiki with front-matter `id, title_zh, title_en, tags, sources, ring, review_status`.
   - Hybrid retrieval: lexical scoring plus a CJK-bigram TF-IDF cosine, with no new dependency.
   - A `wiki_reviews` table for physician verification, plus the guardrail.

   See `references/safety-layer.md`.
5. **MCP.**
   - Read tools, stage-only tools, prompts that script the safe workflow, and `wiki://` resources.
   - MCP Apps `ui://` panels, with a `dashboard_url` fallback.
   - Configure the DNS-rebinding allow-list.

   See `references/mcp-surface.md`.
6. **Dashboard.** Vanilla JS, presentation only. Add new pages in a separate file with small hooks into the existing app rather than rewriting it.
7. **Roles and per-user agent access.**
   - Roles `physician`, `educator`, `dietitian`, `admin`; role groups defined once (`CLINICAL_READ_ROLES`, `CLINICAL_WRITE_ROLES`, `NUTRITION_REVIEW_ROLES`) and mirrored by UI helpers.
   - Dietitian monitoring: confidence-routed meal review queue with Validate, meal ↔ CGM responses, AGP, read-only agent tools.
   - Personal `smdm_…` tokens (hash only, shown once, expiry, revocation), a token panel and an IT CLI; `RoleGate` MCP middleware plus a policy-coverage test.

   See `references/roles-and-access.md`.
8. **Data ingress without an HIS interface.** A paste box on the Import page: deterministic parser → CSV in the import schema → editable → existing preview → commit. A `patients` row only for new chart numbers; physicians get a server-scoped, paste-only import. Fix the bundle so partial reports count (latest value per lab field, newest condition row).

   See `references/his-paste-import.md` and `scripts/his_paste_parser.py --selftest`.
9. **Verify** (next section), then update docs and `handoffs.md`.

## Verification checklist

- [ ] `pytest -q` green. Cover:
  - engines;
  - send policy: an unapproved template never sends, and nothing sends without consent;
  - stage-only MCP tools never change the `sent` count;
  - guardrail: dose text is blocked, an unverified page is blocked for patients, and a wrong eGFR value goes to `needs_review`.
- [ ] Live: `/api/health` ok. A CGM stream ending below 54 creates:
  - an alert row;
  - a patient Rule of 15 message;
  - a nurse-desk card;
  - a pending recheck.
- [ ] MCP over HTTP: initialize, tools/prompts/resources list; no token returns 401.
- [ ] Browser at 1280 px, and at 390×844 (headless Chrome over CDP if the window can't be resized). The page `scrollWidth` must equal the viewport.
- [ ] Every patient's auto-generated summary passes its own guardrail.
- [ ] Claude Desktop connected through `scripts/mcp_stdio_bridge.py` (see `references/mcp-surface.md`).
- [ ] Roles: each role's `tools/list` equals the policy; a dietitian token through the bridge is read-only and a forbidden call writes nothing; revoked/expired/inactive tokens → 401; every registered tool is in the policy.
- [ ] Dietitian: can read and validate a queued meal; staging LINE or acknowledging an alert → 403.
- [ ] Paste: a synthetic mixed Chinese/English HIS report parses fully (conversions, ROC dates, negations, unused lines listed) → preview has no errors → commit; a later partial paste keeps older values; the text never reaches the audit log; a physician cannot import medications or change an existing patient's identity.

## Files in this skill

- `references/architecture.md`: tiers, module map, tables, request flows
- `references/clinical-engines.md`: formulas, cut-offs, citations, test vectors
- `references/safety-layer.md`: send policy, three rings, guardrail rules, HITL
- `references/mcp-surface.md`: tool design, prompts, MCP Apps, allow-list, Claude Desktop setup
- `references/roles-and-access.md`: role matrix, dietitian monitoring workflow, per-user MCP tokens, RoleGate, CHECK-constraint migration
- `references/his-paste-import.md`: clip-and-paste HIS ingress: decision, parser rules, unit table, CSV rules, importer fixes, scope, tests
- `references/pitfalls.md`: 46 measured pitfalls with fixes
- `scripts/score2_diabetes.py`: standalone SCORE2-Diabetes with `--selftest`
- `scripts/mcp_stdio_bridge.py`: stdio ↔ streamable-HTTP bridge (httpx), re-initialises after a server restart
- `scripts/his_paste_parser.py`: standalone HIS paste parser → fields or import CSV, with `--selftest` (synthetic sample)
