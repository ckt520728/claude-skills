# Architecture reference

## Tiers and trust boundaries

| Tier | Runs | May | May not |
|---|---|---|---|
| 1 Desktop agent | Claude Desktop / Cursor / OpenCode (MCP client) | read tools, draft text, stage drafts | touch the DB, compute scores, send, sign, resolve |
| 2 Intranet server | FastAPI + SQLite (PostgreSQL for a pilot), no GPU | calculate, audit, serve REST + MCP + dashboard, auto-send for the 2 permitted reasons | call a cloud LLM with identifiers (vision/STT adapters are LAN-only or off) |
| 3 Patient edge | LINE OA webhook, CGM bridge | deliver inbound events, receive fixed messages | receive doses, diagnoses or raw risk scores |

Production shape:
- reverse proxy + TLS + hospital SSO + network allow-list;
- the webhook and the CGM bridge sit in a DMZ;
- the MCP endpoint is reachable from the LAN only.

## Module map (reference build)

```
app/
  config.py        env settings (MCP_ALLOWED_HOSTS, CGM_BRIDGE_KEY, SCORE2_REGION, ...)
  db.py            schema + additive migrations + per-thread connection cache
  auth.py audit.py signed-cookie sessions, roles (physician/educator/admin), append-only audit
  risk/            PURE: kfre, fib4, watch_dm, eye, cgm, cgm_rules, agp, meal_response,
                   score2_diabetes, five_dimension
  services/
    patients.py    get_bundle(chart) — one query layer
    clinical.py    build_assessment(bundle) — single source of truth for REST/MCP/UI
    cgm_stream.py  ingest → evaluate → alert → auto_send(safety_rule) → nurse desk → recheck
    outreach.py    templates, schedules, run_due(), asyncio scheduler_loop
    nutrition.py   vision adapter | STT → food table; confidence routing; dietitian queue
    line_service.py webhook, signature, auto_send(), stage/confirm, Flex, rich menu
    knowledge.py   three rings, hybrid retrieval, review state
    guardrail.py   verify_draft()
    orchestrator.py named deterministic agents → structured summary + LINE draft
    fhir_export.py RiskAssessment bundle
  api/             REST routers (auth, validation, audit only)
  mcp_server.py    MCP tools/prompts/resources; calls services, never duplicates logic
static/            index.html, app.js (v1), app-v2.js (v2 pages/hooks), mcp-apps/*.html
knowledge/*.md     wiki pages with front-matter
scripts/mcp_stdio_bridge.py
tests/             conftest.py (one session TestClient), engine/API/MCP tests
```

## Tables (v2)

- **Clinical data:** `patients`, `labs`, `screenings`, `medications`, `conditions`
  (with explicit 0/1 rows: `prior_mi`, `ascvd` and `current_smoker`, where a
  missing row means unknown), `ecg`, `cgm_traces`, `diet_logs` (with
  `input_modality`, `review_status` and `confidence_score`).
- **Care workflow:** `care_gaps`, `care_gap_tasks`, `assessments` (PHQ-9,
  GAD-7, PAID, WHO-5, MoCA, CFS, ABI, NT-proBNP; status `done`/`refused`).
- **Messaging:** `line_links` (HMAC hash of the user id plus the id encrypted
  with Fernet, plus consent), `line_messages` (status
  `received|staged|sent|blocked|failed`, `meta.auto_reason`).
- **v2 workflow:** `outreach_templates` (`approved_by`/`approved_at`),
  `outreach_schedules` (`proposed|active|paused|done`), `cgm_alerts`
  (`recheck_status`), `wiki_reviews`, `visit_summaries` (`draft|signed|discarded`
  plus `guardrail_status`).
- **Governance:** `audit_log` (identifiers and metadata only, never clinical
  free text), `imports`.

## Key flows

1. **CGM hypo**:
   1. The bridge POSTs to `/api/cgm/stream` with `X-CGM-Bridge-Key`.
   2. The batch is stored, idempotent per timestamp.
   3. `evaluate_cgm(last 3 h)` runs.
   4. On an event:
      - an alert opens (deduplicated within 30 min);
      - `auto_send(safety_rule)` sends Rule of 15;
      - a nurse-desk card is posted;
      - `recheck_due_at` is set to now + 15 min.
   5. The scheduler tick sends the recheck. A later reading ≥ 70 marks the
      alert recovered.
2. **Pre-visit brief**:
   1. Desktop prompt `previsit_brief`.
   2. `run_previsit_pipeline` runs 6 agents with provenance and returns
      guardrail verdicts.
   3. The LLM rewrites and calls `verify_draft`.
   4. `stage_visit_summary` creates a draft.
   5. A physician signs it in the UI.
3. **Proactive outreach**:
   1. An agent or educator proposes a schedule.
   2. A physician approves the template.
   3. A clinician activates the schedule.
   4. The scheduler sends only with consent, between 06 and 21 h.
   5. Revoking the template pauses its schedules.
4. **Meal**:
   1. Photo (vision adapter) or voice (STT → food table).
   2. Below the confidence threshold the meal goes to the dietitian queue.
   3. The meal is linked to the post-meal CGM response, and large rises are
      flagged for education.
