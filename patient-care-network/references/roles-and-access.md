# Roles, dietitian monitoring and per-user MCP access

The reference build (0.3) has four roles, a personal MCP token for each
clinician, and one policy table that decides what each role's desktop agent can
see. The server enforces every rule; the UI only hides buttons.

## Role matrix

| Action | Physician | Educator (DM nurse) | Dietitian | Admin (IT) |
|---|:-:|:-:|:-:|:-:|
| Read patients, risks, gaps, CGM, knowledge | ✓ | ✓ | ✓ | ✓ (read-only) |
| Resolve gaps, stage/confirm LINE, acknowledge alerts, record assessments, propose/activate schedules | ✓ | ✓ | – | – |
| **Validate meals in the dietitian review queue** | ✓ | ✓ | ✓ | – |
| Sign summaries, approve templates, verify wiki pages | ✓ | – | – | – |
| Hold a personal MCP token | ✓ | ✓ | ✓ | – |
| Issue/revoke tokens for others | – | – | – | ✓ |
| Paste from HIS → import (new patients or clinical rows) | ✓ (scoped) | – | – | ✓ |
| Upload CSV/XLSX, templates, audit log | – | – | – | ✓ |

Define role groups **once** (`app/auth.py`) and use them in every router:

```python
ROLES = {"physician", "educator", "dietitian", "admin"}
CLINICAL_READ_ROLES   = ("physician", "educator", "dietitian", "admin")
CLINICAL_WRITE_ROLES  = ("physician", "educator")
NUTRITION_REVIEW_ROLES = ("physician", "educator", "dietitian")
```

Mirror them in the UI with small helpers, never `role !== 'admin'` checks that
silently give a new role write buttons:

```js
function canWriteClinical()     { return ['physician', 'educator'].includes(state.user?.role); }
function canValidateNutrition() { return ['physician', 'educator', 'dietitian'].includes(state.user?.role); }
```

Adding a role later touches: `ROLES`, the role groups, the `users.role` CHECK
constraint (with a migration), `ROLE_TOOLS`/`ROLE_PROMPTS`, the UI helpers, the
seed (a demo account plus a quick-login button) and the docs' role tables.

### Widening a SQLite CHECK constraint

SQLite cannot alter a CHECK. Rebuild the table in a migration, guarded by the
stored schema text, and only when no foreign key references it:

```python
row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
if row and "'dietitian'" not in row["sql"]:
    conn.executescript("BEGIN; CREATE TABLE users_v3 (...CHECK (role IN (...,'dietitian',...))...);"
                       "INSERT INTO users_v3 SELECT ... FROM users; DROP TABLE users;"
                       "ALTER TABLE users_v3 RENAME TO users; COMMIT;")
```

Test it on a database created with the *old* schema. Also: the seed only runs
on an empty database, so in demo mode call the idempotent `seed_users()` at
startup to add demo accounts introduced by an upgrade.

## Dietitian monitoring workflow

What the dietitian does, and which part of the system supports it:

1. **Review queue.** Meals from LINE (photo → vision adapter, voice → STT →
   food table) carry a `confidence_score`. Below `NUTRITION_CONFIDENCE_MIN`
   (0.75) the meal gets `review_status = dietitian_review`. Any simulated
   adapter (`mode`/`stt_mode` = demo) is capped below the threshold, so it is
   always reviewed. The queue page shows modality, estimate, confidence and a
   **Validate** button (`NUTRITION_REVIEW_ROLES`), optionally with corrected
   carbohydrates.
2. **Meal ↔ CGM response.** `meal_responses(meals, readings)`: baseline = last
   reading at or before the meal (≤ 30 min), peak within 0–180 min, delta,
   time-to-peak, 2-h value; flag Δ > 60 mg/dL or 2-h > 180. Use it for
   education, never as a dose signal.
3. **AGP and CGM summary.** Time-of-day percentile bands show *when* glucose
   runs high (e.g. after lunch) and link back to logged meals.
4. **Desktop agent (read-only).** A dietitian token sees only the read tools,
   e.g. `get_meal_cgm_response`, `get_agp_profile`, `get_cgm_summary`,
   `get_patient_summary`, `search_knowledge`, `verify_draft`. It cannot stage
   LINE messages; education the dietitian drafts goes through an educator or
   physician, or the dashboard.
5. **Audit.** Each validation is audited (`dietitian_validate`, field names and
   ids only).

Extension ideas (not in the reference build): a `dietitian_meal_review(chart)`
prompt, a weekly carbohydrate-pattern summary, and letting dietitians stage
education messages that a nurse confirms.

## Per-user MCP tokens

One shared bearer token means every desktop gets every tool and the audit log
can only say "agent". Replace it with personal tokens:

- **Format** `smdm_` + `secrets.token_urlsafe(32)`. Store only `sha256(token)`
  and a 12-character prefix for display. Show the plaintext **once**, in a
  dialog that also shows a ready-to-paste Claude Desktop bridge config.
- **Resolution** on every request: hash → token row → *current* user role and
  `active` flag. A role change, a deactivation or a revocation takes effect on
  the next request. Reject revoked and expired tokens (default TTL 180 days).
- **Bookkeeping**: update `last_used_at` at most once a minute (SQLite on a
  synced drive is slow).
- **Who can hold one**: clinical roles only. Admin issues and revokes tokens
  for others (desktop provisioning) but holds none.
- **Issue paths**: self-service panel in the dashboard, `POST /api/mcp-tokens`
  (admin may name a user), and an IT CLI
  `python -m app.mcp_access create|list|revoke`.
- **Shared token**: keep it only behind `MCP_SHARED_TOKEN_ENABLED` (default on
  in demo mode, off otherwise), mapped to the physician tool set and audited as
  `mcp:shared`.

Table:

```sql
CREATE TABLE mcp_tokens (token_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, label TEXT NOT NULL,
  token_prefix TEXT NOT NULL, token_hash TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL, created_by TEXT NOT NULL,
  expires_at TEXT, last_used_at TEXT, revoked_at TEXT, revoked_by TEXT);
```

## Role-scoped MCP surface (`RoleGate`)

One policy table, enforced by one server middleware:

```python
READ_TOOLS = frozenset({...17 read tools...})
ROLE_TOOLS = {
    "physician": READ_TOOLS | {"run_previsit_pipeline", "stage_visit_summary", "export_fhir_risk",
                               "stage_line_message", "create_care_gap_task", "propose_outreach_schedule"},
    "educator":  READ_TOOLS | {"run_previsit_pipeline", "stage_line_message", "create_care_gap_task",
                               "propose_outreach_schedule"},
    "dietitian": READ_TOOLS,
}
ROLE_PROMPTS = {"physician": {...3...}, "educator": {"care_gap_review", "patient_education_draft"}, "dietitian": set()}
```

Wiring with the Python SDK (`mcp` 2.x `MCPServer`):

1. The ASGI bearer gate resolves the token to an `Identity` and stores it in
   the ASGI scope under a private key (`scope["smartdm.mcp_identity"]`). Do not
   pass identity in a header the client could forge.
2. `MCPServer(..., middleware=[RoleGate()])`. A `ServerMiddleware` is
   `async __call__(ctx, call_next)`; `ctx.method`, raw `ctx.params` and
   `ctx.request` (the Starlette request, so `ctx.request.scope`) are available.
3. In `RoleGate`:
   - set a `contextvars.ContextVar` with the identity around `call_next`, so
     tool handlers can audit `mcp:<username>`; it propagates into the handler;
   - `tools/call` outside the role → return a `CallToolResult(is_error=True)`
     with a readable message ("not permitted for role 'dietitian'");
   - `prompts/get` outside the role → raise `MCPError(-32602, ...)`;
   - after `call_next`, filter `tools/list` / `prompts/list` results (they may
     be a model or a dict; handle both).
4. Keep the audit `role` column as `mcp` if telemetry counts agent calls by it;
   put the person in `actor` and the role in the detail.
5. **Policy-coverage test**: the union of `ROLE_TOOLS` must equal the
   registered tool names, and the same for prompts. A new tool then fails CI
   until someone places it in the policy on purpose.

Verified result in the reference build: physician 23 tools / 3 prompts,
educator 21 / 2, dietitian 17 / 0; a dietitian token through the stdio bridge
gets 17 tools and `stage_line_message` is refused.

## Tests worth copying

- each role's `tools/list` and `prompts/list` equal the policy;
- a forbidden call returns `isError` and writes nothing (row counts unchanged);
- revoked, expired, unknown and inactive-user tokens → 401;
- only the hash is stored; plaintext never appears in listings;
- the shared token can be switched off;
- token API: admin cannot hold one, a clinician cannot issue for others or
  revoke others' tokens, a listing shows only one's own tokens;
- dietitian dashboard: read 200, validate 200, stage LINE 403, acknowledge 403;
- migration from an old-schema database.
