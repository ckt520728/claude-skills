# Profile: web-system

醫院藥品管理系統、醫師/員工出勤打卡系統，以及一般的 CRUD + auth web 應用。

## Deliverables

| Name | Target | Split |
|---|---|---|
| `spec` | `docs/system_spec.json` | held_in |
| `schema` | `db/schema.sql` | held_in |
| `api` | `services/api/` | held_in |
| `ui` | `web/` | held_in |
| `e2e` | `tests/e2e/report.json` | held_out |

## Contracts

```bash
$K contract --name spec --target docs/system_spec.json --split held_in \
  --checks "exists,valid_json,json_keys:system_name;modules;database;auth_model"
$K contract --name api --target services/api/app.py --split held_in \
  --checks "exists,python_compiles,no_placeholder,cmd:pytest -q services/api/tests"
$K contract --name schema --target db/schema.sql --split held_in \
  --checks "exists,min_bytes:200,regex_present:CREATE TABLE,cmd:sqlite3 :memory: < db/schema.sql"
$K contract --name e2e --target tests/e2e/report.json --split held_out \
  --checks "exists,valid_json,json_keys:passed;failed,cmd:npx playwright test --reporter=json"
```

`cmd:` checks are the whole point in this domain — it has real verifiers.
Use them instead of structural proxies wherever one exists.

## Decomposition

`db_schema` → `api_auth` → `api_domain` → `ui_pages` → `e2e`.

Schema first. Every later job reads it, and changing it after the API exists
costs three rewrites.

## Known failure mechanisms

| Mechanism | Symptom | Component to fix |
|---|---|---|
| `session_lost_under_concurrency` | 401s only when several people check in at once | middleware — shared session store, not in-process memory |
| `schema_drift_api_vs_db` | API writes a column that no longer exists | middleware — regenerate types from schema, verify in CI |
| `tz_naive_timestamps` | Attendance times shift by 8 hours | tool — one timestamp helper; store UTC, render Asia/Taipei |
| `output_path_never_registered` | Build "succeeds", `dist/` is empty | middleware — assert artifact exists after every build |
| `seed_data_in_prod_path` | Test patients appear in real queries | middleware — environment guard |
| `async_write_race` | Duplicate or lost check-in rows | tool — transactional write with a uniqueness constraint |

## Domain cautions

- 藥品管理與出勤資料屬於個資與醫療資料。Never put real patient or staff records
  into a sandbox, a job log, a trace, or a prompt. Seed with synthetic data, and
  contract it: `regex_absent` on national-ID and phone patterns.
- Controlled-substance inventory needs an append-only audit trail. Make that a
  contract — a `cmd:` script asserting no UPDATE/DELETE against the audit table —
  not a code comment.
- Attendance rounding rules touch labour law (勞基法). They are a user decision.
  Ask; do not infer a default.
