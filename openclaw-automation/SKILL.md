---
name: openclaw-automation
description: Use when OpenClaw automation, LINE webhook, Cloudflare tunnel, quick tunnel URL rotation, Windows startup recovery, Codex heartbeat automation, or LINE bot connection stops working.
---

# OpenClaw Automation

Use this skill to restore or build a portable OpenClaw automation that connects LINE to a local OpenClaw Gateway through a narrow `/line/webhook` proxy and a Cloudflare quick tunnel.

Core principle: diagnose the public webhook path first, then the local proxy, then OpenClaw Gateway, then model/auth. Do not expose the whole OpenClaw Gateway to the public internet.

## Required Context

- Windows with Node.js available.
- OpenClaw config at `%USERPROFILE%\.openclaw\openclaw.json`.
- LINE channel credentials already stored in the OpenClaw config.
- Local OpenClaw Gateway running on `127.0.0.1:18789`.
- A local LINE proxy should listen on `127.0.0.1:18790/line/webhook`.

If paths differ, pass explicit parameters to `scripts/ensure-openclaw-line.ps1`.

## Fast Recovery

1. Check the local proxy:
   `Invoke-WebRequest http://127.0.0.1:18790/line/webhook`
   Expected: `200 OK`.

2. Check OpenClaw Gateway:
   `Invoke-WebRequest http://127.0.0.1:18789/`
   Expected: `200`.

3. Recreate the proxy, Cloudflare tunnel, LINE endpoint, and startup task:
   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\ensure-openclaw-line.ps1
   ```

4. Validate with LINE official webhook test. The script prints the test result. Expected:
   `success=true`, `statusCode=200`.

## Startup Automation

For daily use, register a Windows scheduled task that runs at logon and once every morning:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\ensure-openclaw-line.ps1 -RegisterStartupRecovery
```

This handles the common failure where a reboot or stopped quick tunnel changes the `trycloudflare.com` URL. The task restarts the local proxy and tunnel, extracts the new tunnel URL from logs, updates LINE webhook endpoint, and tests the LINE endpoint.

If `Register-ScheduledTask` is blocked by Windows permissions, use `schtasks.exe` with `scripts\run-openclaw-line-ensure.cmd` as the action. Create two tasks: one `ONLOGON`, one `DAILY` at `07:05`.

## Codex Heartbeat Automation

If Codex shows `cannot resume running thread ... stale path`, the issue is usually a heartbeat automation still bound to an old thread/session. Recreate or update the automation in the current thread instead of repairing LINE.

Use a daily heartbeat for the user-facing assistant work, for example:

- `kind`: `heartbeat`
- `destination`: current thread
- `status`: `ACTIVE`
- schedule: `FREQ=DAILY;BYHOUR=7,20;BYMINUTE=0;BYSECOND=0`

Do not point new automations at stale `target_thread_id` values unless explicitly recovering that exact thread.

## Common Failures

- `LINE stopped responding`: quick tunnel or local proxy is not running. Run the ensure script before changing OpenClaw settings.
- `LINE webhook test fails but manual LINE account auto-reply appears`: LINE is not reaching OpenClaw; update the webhook endpoint to the current tunnel URL.
- `Invoke-RestMethod` fails with TLS/receive errors on Windows: use Node `fetch`; the bundled script does this.
- PowerShell script execution is disabled: call with `-ExecutionPolicy Bypass` for this run only.
- `openclaw.cmd` has `Access denied`: inspect `~\.openclaw\openclaw.json` and local HTTP endpoints directly; do not assume OpenClaw itself is down.
- Model probe rejects `openai/gpt-5.5` with schema or `format`: switch default model to a known working model such as `openai/gpt-4.1-mini` and probe again.

## Files

- `scripts/line-webhook-proxy.mjs`: minimal local proxy. `GET /line/webhook` returns `OK`; `POST /line/webhook` forwards to OpenClaw Gateway.
- `scripts/ensure-openclaw-line.ps1`: starts/restarts proxy and tunnel, updates LINE webhook endpoint, validates LINE official webhook test, and can register startup recovery.
- `scripts/run-openclaw-line-ensure.cmd`: stable scheduled-task wrapper for Windows quoting issues.
