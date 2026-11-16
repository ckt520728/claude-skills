"""stdio ↔ streamable-HTTP bridge for desktop MCP clients (e.g. Claude Desktop).

Claude Desktop launches local MCP servers as stdio subprocesses. This bridge
forwards each JSON-RPC message from stdin to the hospital MCP endpoint with the
bearer token, and writes the JSON response to stdout. The server runs with
``json_response=True``, so every request gets a plain JSON reply.

Environment:
    SMARTDM_MCP_URL   default http://127.0.0.1:8000/mcp/
    MCP_TOKEN         bearer token (required outside the demo)

If the server restarts (session id unknown → 404), the bridge replays the
cached ``initialize`` handshake once and retries the request.
Logs go to stderr only; stdout carries protocol messages exclusively.
"""

from __future__ import annotations

import json
import os
import sys

import httpx

URL = os.getenv("SMARTDM_MCP_URL", "http://127.0.0.1:8000/mcp/")
TOKEN = os.getenv("MCP_TOKEN", "demo-mcp-token")

session_id: str | None = None
init_message: dict | None = None
client = httpx.Client(timeout=httpx.Timeout(120.0, connect=10.0))


def log(*parts: object) -> None:
    print("[smartdm-bridge]", *parts, file=sys.stderr, flush=True)


def emit(message: dict) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def post(message: dict) -> httpx.Response:
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if session_id:
        headers["mcp-session-id"] = session_id
    return client.post(URL, headers=headers, content=json.dumps(message, ensure_ascii=False).encode("utf-8"))


def reinitialize() -> bool:
    global session_id
    if not init_message:
        return False
    session_id = None
    resp = post(init_message)
    if resp.status_code != 200:
        return False
    session_id = resp.headers.get("mcp-session-id")
    post({"jsonrpc": "2.0", "method": "notifications/initialized"})
    log("session re-established after server restart")
    return True


def handle(message: dict) -> None:
    global session_id, init_message
    if message.get("method") == "initialize":
        init_message = message
        session_id = None
    try:
        resp = post(message)
        if resp.status_code == 404 and session_id and reinitialize():
            resp = post(message)
    except httpx.HTTPError as exc:
        log("HTTP error:", type(exc).__name__, exc)
        if "id" in message:
            emit({"jsonrpc": "2.0", "id": message["id"],
                  "error": {"code": -32000, "message": f"Smart DM Care server unreachable at {URL} ({type(exc).__name__}). Is uvicorn running?"}})
        return

    if message.get("method") == "initialize" and resp.status_code == 200:
        session_id = resp.headers.get("mcp-session-id")

    if resp.status_code == 202 or not resp.content:
        return
    if resp.status_code == 401:
        log("401 unauthorized: check MCP_TOKEN")
    try:
        data = resp.json()
    except ValueError:
        log("non-JSON response", resp.status_code, resp.text[:200])
        if "id" in message:
            emit({"jsonrpc": "2.0", "id": message["id"],
                  "error": {"code": -32000, "message": f"HTTP {resp.status_code} from MCP server"}})
        return
    for item in data if isinstance(data, list) else [data]:
        if isinstance(item, dict) and item.get("jsonrpc"):
            emit(item)
        elif "id" in message:
            emit({"jsonrpc": "2.0", "id": message["id"],
                  "error": {"code": -32000, "message": f"HTTP {resp.status_code}: {str(item)[:300]}"}})


def main() -> None:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    log("forwarding stdio →", URL)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            log("dropping non-JSON line")
            continue
        for m in message if isinstance(message, list) else [message]:
            handle(m)


if __name__ == "__main__":
    main()
