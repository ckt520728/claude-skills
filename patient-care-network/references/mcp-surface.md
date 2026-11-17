# MCP surface reference

## Design rules

- Tools call services and never duplicate clinical logic. Every call is audited
  with `role="mcp"`, recording identifiers only.
- **Read tools** return deterministic results with inputs, citations and
  `dashboard_url`.
- **Stage-only tools** write rows whose status is a draft (`staged`, `draft` or
  `proposed`). They return `requires_confirmation` and run the guardrail first.
- **Prompts** script the safe workflow:
  1. call the tools;
  2. cite `[wiki:id]`;
  3. call `verify_draft`;
  4. stage only if the result is `pass`.

  Every prompt ends with the same safety paragraph.
- Use the bearer token as a separate trust boundary from dashboard sessions.
  Give **each clinician a personal token** and scope tools by role
  (`references/roles-and-access.md`). Production should move to hospital
  OIDC with short-lived tokens; the policy table and `RoleGate` stay.

## Reference tool set (23)

Role scoping: physician sees all 23 tools and 3 prompts; educator 21 tools
(no `stage_visit_summary`, `export_fhir_risk`) and 2 prompts; dietitian the
17 read tools in `READ_TOOLS` (everything under Read except
`run_previsit_pipeline` and `export_fhir_risk`) and no prompts.

- **Read:**
  - `list_patients`, `get_patient_summary`, `calculate_organ_risk`
  - `audit_care_gaps`, `get_cgm_summary`, `get_medication_audit`
  - `search_guidelines`, `search_knowledge` (ring and verified filters), `list_guidelines`
  - `get_dashboard_overview`, `show_patient_panel` (UI), `get_five_dimension_profile`
  - `get_agp_profile`, `get_meal_cgm_response`, `list_cgm_alerts` (UI)
  - `run_previsit_pipeline`, `verify_draft`, `export_fhir_risk`, `list_outreach_templates`
- **Stage-only:** `stage_line_message`, `create_care_gap_task`,
  `stage_visit_summary`, `propose_outreach_schedule`.
- **Prompts:** `previsit_brief(chart)`, `care_gap_review(chart)`,
  `patient_education_draft(chart, topic)`.
- **Resources:** `wiki://{doc_id}` (markdown), `ui://<app>/patient-panel`,
  `ui://<app>/nurse-desk`.

## MCP Apps panels

- **Resource:** MIME type `text/html;profile=mcp-app`, self-contained, with no
  CDN.
- **Linking:** the tool carries `meta={"ui": {"resourceUri": uri}, "ui/resourceUri": uri}`.
  Include both spellings: the nested form for current hosts, the flat key for
  older drafts.
- **Bridge inside the panel:**
  1. Post `ui/initialize`.
  2. Then post `ui/notifications/initialized`.
  3. Render on `ui/notifications/tool-result`.
  4. Call read tools with `tools/call`.
  5. Report `ui/notifications/size-changed`.
- **Reading the result:**
  - Use `structuredContent.result ?? structuredContent`.
  - Fall back to `JSON.parse(content[0].text)`. Dict-returning tools often
    produce no structuredContent.
- **Outside a host:** show a message and a dashboard link.
- **Panels are read-only.** Acknowledge, sign and send stay in the
  authenticated dashboard.

## Python SDK notes (mcp 2.x `MCPServer`)

- Mount `mcp.streamable_http_app(streamable_http_path="/", json_response=True, transport_security=...)`
  under `/mcp`, behind a bearer ASGI gate. Rewrite `/mcp` to `/mcp/`.
- **DNS-rebinding protection** is on by default and allows only localhost Host
  headers. Every other host gets **HTTP 421 "Invalid Host header"**. That
  includes the TestClient's `testserver` and the LAN hostname. Configure:
  `TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=[...,"<intranet-host>:*"], allowed_origins=[...])`.
- **Per-request identity and role filtering** use a server middleware:
  `MCPServer(..., middleware=[RoleGate()])`. A `ServerMiddleware` gets
  `ctx.method`, raw `ctx.params` and `ctx.request` (Starlette, so
  `ctx.request.scope`). Return `CallToolResult(is_error=True)` for a
  forbidden tool, raise `MCPError(-32602, ...)` for a forbidden prompt, and
  filter list results after `call_next`. Details in `roles-and-access.md`.
- **The session manager starts only once per process.** Use one
  session-scoped TestClient in `conftest.py` for every API/MCP test module.
- **Testing over HTTP:**
  1. Initialize, and read the `mcp-session-id` response header.
  2. Send it back on every later call.
  3. Send `notifications/initialized` (the server replies 202 with no body).

## Connecting Claude Desktop

Claude Desktop starts local servers over **stdio**. Use `scripts/mcp_stdio_bridge.py`:
- it reads JSON-RPC lines from stdin;
- it POSTs each one with the bearer token and session id;
- it writes the JSON reply to stdout, with logs on stderr only;
- after a 404 (server restarted) it replays `initialize` and retries.

**Config file location (Windows):**

| Build | Path |
|---|---|
| Microsoft Store | `%LOCALAPPDATA%\Packages\Claude_<id>\LocalCache\Roaming\Claude\claude_desktop_config.json` |
| Standard installer | `%APPDATA%\Claude\claude_desktop_config.json` |

- The `Claude-3p` folder is a different profile.
- To confirm which file the app reads, grep `%LOCALAPPDATA%\Claude\Logs\main.log`
  for "Reading claude_desktop_config.json from".

```json
{"mcpServers": {"smart-dm-care": {
  "command": "<repo>\\.venv\\Scripts\\python.exe",
  "args": ["-I", "<repo>\\scripts\\mcp_stdio_bridge.py"],
  "env": {"SMARTDM_MCP_URL": "http://127.0.0.1:8000/mcp/", "MCP_TOKEN": "<personal token>", "PYTHONIOENCODING": "utf-8"}}}}
```

- Use the clinician's **personal** token; the dashboard's token dialog shows
  this block already filled in. A shared demo token should work only in
  demo mode.

- Read the file first. Merge into an existing `mcpServers` rather than
  overwriting it.
- Fully quit Claude Desktop from the tray (closing the window is not enough) and
  reopen it.
- The uvicorn server must be running. If it is not, the bridge returns a clear
  "server unreachable" error.
- **Third-party alternative:** `npx mcp-remote <url> --header "Authorization:${AUTH}"`
  with `AUTH` set in `env`. This works too, but downloads an npm package.
