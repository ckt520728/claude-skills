# Deployment and team sharing

What it takes to move the care network from a developer PC to a team, and the
guide hospital IT needs. Reference: `docs/DEPLOYMENT_IT.md` in the reference
build (Traditional Chinese, 13 sections plus a LAN appendix).

## "There is no Share button"

The dashboard is a local web server (`127.0.0.1:8000`), not a hosted page, so
nothing can be "shared" from it. Say this plainly and offer two routes:

| Route | When | What it needs |
|---|---|---|
| **LAN demo** | show colleagues, synthetic data only | the developer PC stays on and the server keeps running |
| **IT deployment** | real team use (and later real data) | an intranet VM, HTTPS, accounts, review approvals |

A published document (manual, guide) can be shared from its own page; the
running app cannot.

## LAN demo (verified)

```powershell
$env:MCP_ALLOWED_HOSTS   = "127.0.0.1:*,localhost:*,testserver,<LAN IP>:*"
$env:MCP_ALLOWED_ORIGINS = "http://127.0.0.1:*,http://localhost:*,http://<LAN IP>:*"
$env:PUBLIC_BASE_URL     = "http://<LAN IP>:8000"     # dashboard_url links in MCP results
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Find the IP with `Get-NetIPAddress -AddressFamily IPv4` (skip 127.* and
  169.254.*). DHCP addresses change; say so.
- Verify on the LAN IP itself: `/api/health` and an MCP `initialize`. Without
  the IP in `MCP_ALLOWED_HOSTS`, MCP answers 421.
- Firewall: **check read-only, never change it** (security settings are the
  user's or IT's call): `Get-NetFirewallApplicationFilter` / port filters for
  inbound rules on python.exe or the port, and `Get-NetConnectionProfile` for
  Public/Private. Requests from the same PC skip the firewall, so a local test
  does not prove colleagues can connect; say it was not tested from a second PC.
- No HTTPS → synthetic data only, intranet only. A server started from an agent
  session stops with the session (or on memory pressure); for a longer demo the
  user starts it in their own terminal.
- Ask before switching to network mode: binding to `0.0.0.0` is outward-facing.

## IT deployment guide: sections that worked

Write it for the hospital IT department, in their language, as an editable
document (export to Word/PDF) plus a copy in the repo (`docs/DEPLOYMENT_IT.md`).

1. **Components and network zones**: a table of component · zone · port · who
   connects. The HIS is *not* connected (clinicians paste).
2. **Server requirements**: 2 vCPU / 4 GB / 20 GB local disk (never a synced
   or network drive for SQLite), Ubuntu LTS or Windows Server, Docker, no GPU,
   no runtime internet except optional LINE.
3. **Install**: get the code, `.env` with fresh secrets
   (`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`), a
   `docker-compose.override.yml`, `docker compose up -d --build`, health check.
4. **HTTPS / reverse proxy** (nginx): bind the app to `127.0.0.1:8000`;
   `proxy_set_header Host $host` (the MCP Host allow-list needs it, else 421);
   `client_max_body_size` above the import limit; no long-lived cache on
   dashboard files (they are served `no-cache`); `DM_COOKIE_SECURE=true`.
5. **Firewall table**: in 443 from clinical desktop VLANs only; 8000 denied
   except localhost; nothing from the internet; DMZ → server only for the LINE
   webhook and CGM stream paths; out to `api.line.me` only in LINE live mode.
6. **Accounts and roles**: role table; disable the demo accounts; create real
   users (password via `getpass`, never on the command line); deactivating a
   user also kills their MCP tokens.
7. **Desktop AI rollout**:
   - **prerequisite first**: the desktop model runs in the vendor cloud, so
     tool results (patient data) leave the hospital; no real data until
     security/privacy approval (enterprise agreement, no retention,
     de-identified output) or a local model; until then, dashboard only;
   - personal tokens (self-service panel or IT CLI), role-scoped tool counts;
   - package the stdio bridge as one `.exe` (PyInstaller) and push it with
     the config via Intune/GPO; standardise on one Claude Desktop build because
     the config path differs (Store vs installer); the token sits in plain text
     in the user profile.
8. **Optional LINE / CGM**: keep demo mode until consent, retention and
   after-hours escalation are owned; the two auto-send reasons; the bridge key;
   one worker only (in-process scheduler).
9. **Backup, update, monitoring**: SQLite online backup
   (`sqlite3.connect(src).backup(dst)`), never a raw copy of a WAL database;
   encrypt backups (they hold PHI) and rehearse restore; schema migrates on
   start, so back up before updating; `/api/health`; no request-body logging.
10. **Verification** (six checks): health over HTTPS; each role logs in and the
    demo accounts cannot; MCP without a token → 401; the shared demo token →
    401; a dietitian token sees 17 tools and staging is refused; ports closed
    from outside.
11. **Pre-launch checklist** (tickable): DPIA/security review, IRB/TFDA,
    cloud-model approval, secrets rotated, HTTPS, firewall, demo accounts and
    synthetic patients handled, personal accounts and tokens, backups, LINE/CGM
    mode, simulator removed, penetration test.
12. **Known gaps** table (current state vs production): SSO, OIDC tokens,
    PostgreSQL, HIS interface, scheduler as a service, seeding, compose file.
13. **References** inside the repo.

## Repository gaps a deployment exposes

Check these before writing the guide; each needs a code fix or a documented
workaround:

- **The shipped `docker-compose.yml` hard-codes demo mode** and passes none of
  the newer settings. Workaround: an override file
  ```yaml
  services:
    smart-dm-care:
      env_file: .env
      environment: [DM_DEMO_MODE=false, LINE_DEMO_MODE=true]
      ports: !override
        - "127.0.0.1:8000:8000"     # !override needs Docker Compose ≥ 2.24
  ```
  Better: make the compose file read `.env` from the start.
- **An empty database is seeded with synthetic patients and demo accounts at
  startup, even outside demo mode.** Gate first-run seeding on demo mode in
  the code; until then, document disabling the demo accounts.
- **No user-management UI or CLI.** Add `python -m app.users add|disable`
  before handing over; until then, a documented Python one-liner.
- Leftover demo affordances (a CGM simulator button) must be removed before
  live use.

## Handing over documents

- An editable cloud document (Docs) suits IT: they edit and export it. Keep a
  Markdown copy in the repo so the guide is versioned with the code.
- A document export may come back as base64 inside the tool result. Do not
  retype base64 into a file (one wrong character corrupts it); regenerate the
  Markdown from the content you wrote instead.
- Keep personal details out of the repo copy (the user's name in a byline,
  the developer PC's IP or Wi-Fi name); use placeholders.
- Documents are private until the owner shares them; say so every time.
