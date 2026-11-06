#!/usr/bin/env python3
"""Connect Claude Code or Cursor to the remote Gemini Notebook MCP server.

Works on Windows, macOS and Linux with only the Python 3.8+ standard library.
Run with no arguments for guided setup, or see --help for the other commands.

This file never prints or stores your OAuth client secret. Only the path to the
client file is saved, in ~/.gemini-notebook-mcp/config.json.
"""
import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

MCP_URL = "https://notebook.googleapis.com/mcp"
SERVER_NAME = "gemini-notebook-api"
API_NAME = "notebook.googleapis.com"
PROTOCOL_VERSION = "2026-07-28"
SCOPES = (
    "https://www.googleapis.com/auth/cloud-platform,"
    "https://www.googleapis.com/auth/notebook"
)
HOME_DIR = Path.home() / ".gemini-notebook-mcp"
CONFIG_FILE = HOME_DIR / "config.json"
CURSOR_CONFIG = Path.home() / ".cursor" / "mcp.json"
DOWNLOADS = Path.home() / "Downloads"
SYNCED_FOLDER_HINTS = ("google drive", "我的雲端硬碟", "onedrive", "dropbox", "icloud")
GCLOUD_DOCS = "https://cloud.google.com/sdk/docs/install"


class SetupError(Exception):
    """A problem the user can act on. Shown without a traceback."""


def say(message=""):
    print(message, flush=True)


def step(number, title):
    say(f"\n[{number}] {title}")


def ask(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        raise SetupError("Input is needed here, but this terminal is not interactive.")


def confirm(prompt):
    return ask(f"{prompt} [y/N] ").lower() in ("y", "yes")


def self_command(command):
    """The exact command to run this script again, for messages to the user."""
    installed = HOME_DIR / Path(__file__).name
    script = installed if installed.exists() else Path(__file__).resolve()
    return f'"{sys.executable}" "{script}" {command}'


# --- saved settings ---------------------------------------------------------

def load_config():
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(**changes):
    config = load_config()
    config.update(changes)
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def set_private(path):
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


# --- gcloud -----------------------------------------------------------------

def gcloud_candidates():
    home = Path.home()
    local = os.environ.get("LOCALAPPDATA", "")
    program_files = [os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")]
    paths = [Path(p) / "Google" / "Cloud SDK" / "google-cloud-sdk" / "bin" / "gcloud.cmd"
             for p in [local] + program_files if p]
    paths += [
        home / "google-cloud-sdk" / "bin" / "gcloud.cmd",
        home / "google-cloud-sdk" / "bin" / "gcloud",
        Path("/opt/homebrew/share/google-cloud-sdk/bin/gcloud"),
        Path("/usr/local/share/google-cloud-sdk/bin/gcloud"),
        Path("/snap/bin/gcloud"),
        Path("/usr/bin/gcloud"),
    ]
    return paths


def find_gcloud():
    found = shutil.which("gcloud")
    if found:
        return found
    for path in gcloud_candidates():
        if path.exists():
            return str(path)
    return None


def run_gcloud(gcloud, args, capture=True):
    return subprocess.run(
        [gcloud] + args,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        encoding="utf-8",
        errors="replace",
    )


def gcloud_value(gcloud, args):
    result = run_gcloud(gcloud, args)
    value = (result.stdout or "").strip()
    return "" if result.returncode != 0 or value == "(unset)" else value


def require_gcloud():
    gcloud = find_gcloud()
    if not gcloud:
        raise SetupError(f"gcloud was not found. Install it from {GCLOUD_DOCS}")
    return gcloud


def ensure_gcloud():
    gcloud = find_gcloud()
    if gcloud:
        say(f"    Found gcloud: {gcloud}")
        return gcloud
    if sys.platform == "win32" and shutil.which("winget"):
        command = ["winget", "install", "--id", "Google.CloudSDK", "--exact"]
    elif sys.platform == "darwin" and shutil.which("brew"):
        command = ["brew", "install", "--cask", "google-cloud-sdk"]
    else:
        raise SetupError(f"gcloud was not found. Install it from {GCLOUD_DOCS}, then run this again.")
    say("    gcloud (the Google Cloud SDK) is not installed.")
    if not confirm(f"    Install it now with: {' '.join(command)} ?"):
        raise SetupError(f"gcloud is required. Install it from {GCLOUD_DOCS}, then run this again.")
    if subprocess.run(command).returncode != 0:
        raise SetupError(f"The install failed. Install gcloud from {GCLOUD_DOCS}, then run this again.")
    gcloud = find_gcloud()
    if not gcloud:
        raise SetupError("gcloud was installed but not found yet. Open a new terminal and run this again.")
    return gcloud


def mint_token(gcloud):
    result = run_gcloud(gcloud, ["auth", "application-default", "print-access-token"])
    token = (result.stdout or "").strip()
    if result.returncode != 0 or not token:
        raise SetupError(
            "Could not get an access token. The sign-in may be missing or expired "
            "(about every 7 days while your OAuth app is in Testing).\n"
            f"Run: {self_command('login')}"
        )
    return token


# --- project ----------------------------------------------------------------

def valid_project(project):
    return bool(re.fullmatch(r"[a-z][a-z0-9:.\-]{4,}", project or ""))


def choose_project(gcloud, requested):
    if requested:
        if not valid_project(requested):
            raise SetupError(f"That does not look like a project ID: {requested}")
        return requested
    default = load_config().get("project") or gcloud_value(gcloud, ["config", "get-value", "project"])
    listing = run_gcloud(gcloud, ["projects", "list", "--limit=20", "--format=value(projectId)"])
    if listing.returncode == 0 and listing.stdout.strip():
        say("    Your projects:")
        for line in listing.stdout.splitlines():
            say(f"      {line}")
    suffix = f" [{default}]" if default else ""
    project = ask(f"    Project ID to use{suffix}: ") or default
    if not valid_project(project):
        raise SetupError("A valid project ID is required.")
    return project


# --- OAuth client file ------------------------------------------------------

def read_client_file(path):
    """Return the client's project ID. Reads the file but never returns the secret."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise SetupError(f"Could not read this as a JSON file: {path}")
    if "web" in data:
        raise SetupError("This is a Web application client. Create a 'Desktop app' client instead.")
    if "installed" not in data:
        raise SetupError(f"This is not an OAuth Desktop client file: {path}")
    return data["installed"].get("project_id", "")


def warn_if_synced(path):
    lowered = str(path).lower()
    if any(hint in lowered for hint in SYNCED_FOLDER_HINTS):
        say("    WARNING: this secret file is in a cloud-synced folder. Consider moving it.")


def scan_downloads(project):
    """Newest client_secret*.json in Downloads that belongs to this project."""
    files = sorted(DOWNLOADS.glob("client_secret*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files:
        try:
            if read_client_file(path) == project:
                return path
        except SetupError:
            continue
    return None


def console_steps(project):
    base = "https://console.cloud.google.com/auth"
    say(f"""
    No OAuth client file was found for {project}. Create one in your browser:

    1. Consent screen: {base}/overview?project={project}
       App name: anything. Audience: External.
    2. Test user:      {base}/audience?project={project}
       Add your own Google account and leave the app in Testing.
    3. Scope:          {base}/scopes?project={project}
       Add or remove scopes > Manually add scopes. Do not open this address, paste it:
       https://www.googleapis.com/auth/notebook
    4. Client:         {base}/clients?project={project}
       Create client > Desktop app > download the JSON to your Downloads folder.
""")


def find_client_file(project, requested):
    if requested:
        path = Path(requested).expanduser().resolve()
        owner = read_client_file(path)
        if owner and owner != project:
            say(f"    WARNING: this client belongs to {owner}, not {project}.")
        return path
    saved = load_config().get("client_file")
    if saved and Path(saved).exists():
        try:
            if read_client_file(saved) == project:
                return Path(saved)
        except SetupError:
            pass
    found = scan_downloads(project)
    if found:
        return found
    console_steps(project)
    while True:
        answer = ask("    Press Enter once it has downloaded, or paste the file's full path: ")
        if answer:
            return find_client_file(project, answer.strip('"\''))
        found = scan_downloads(project)
        if found:
            return found
        say(f"    Still no client_secret*.json for {project} in {DOWNLOADS}")


def adc_login(gcloud, project, client_file):
    say("    Your browser will open. Sign in with a personal Google account (not Workspace).")
    say("    'Google hasn't verified this app' is expected for your own client:")
    say("    choose Advanced, then continue. Allow every permission requested.")
    login = run_gcloud(gcloud, [
        "auth", "application-default", "login",
        f"--client-id-file={client_file}",
        f"--scopes={SCOPES}",
    ], capture=False)
    if login.returncode != 0:
        raise SetupError(
            "Sign-in did not finish. If Google says 'This app is blocked', check that your account "
            "is a test user and the notebook scope was added on the Data Access page."
        )
    quota = run_gcloud(gcloud, ["auth", "application-default", "set-quota-project", project])
    if quota.returncode != 0:
        say("    Note: could not set the quota project. Requests still send it as a header.")


# --- MCP check --------------------------------------------------------------

def parse_rpc_response(text):
    """Accept either a JSON body or a server-sent-events stream."""
    stripped = text.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)
    for line in stripped.splitlines():
        if line.startswith("data:"):
            try:
                message = json.loads(line[5:].strip())
            except ValueError:
                continue
            if "result" in message or "error" in message:
                return message
    raise ValueError("no JSON-RPC message in the response")


def http_error_hint(status, body):
    if "WORKSPACE_ACCOUNT_NOT_SUPPORTED" in body:
        return "Google Workspace accounts are not supported yet. Sign in with a personal account."
    if "Account not found" in body:
        return "Sign in once at https://notebook.google.com with this account, then try again."
    if status == 401:
        return "The token was rejected. Run the login command to sign in again."
    if status == 403:
        return "Access denied. Check that the API is enabled on this project and the notebook scope was granted."
    return "The server returned an unexpected response."


def list_tools(token, project):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {"_meta": {"io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION}},
    }
    request = urllib.request.Request(
        MCP_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "x-goog-user-project": project,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
            "Mcp-Method": "tools/list",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        raise SetupError(f"HTTP {error.code}: {http_error_hint(error.code, body)}")
    except urllib.error.URLError as error:
        raise SetupError(f"Could not reach {MCP_URL}: {error.reason}")
    try:
        message = parse_rpc_response(text)
    except ValueError as error:
        raise SetupError(f"Unexpected response from the server: {error}")
    if "error" in message:
        raise SetupError(f"The server returned an error: {message['error'].get('message', 'unknown')}")
    return [tool.get("name", "?") for tool in message.get("result", {}).get("tools", [])]


# --- client configuration ---------------------------------------------------

def install_self():
    """Keep a stable copy so the pack folder can be moved or deleted later."""
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    target = HOME_DIR / Path(__file__).name
    if Path(__file__).resolve() != target.resolve():
        shutil.copy2(__file__, target)
    return target


def headers_helper_command(script):
    # Forward slashes work in cmd.exe, Git Bash and POSIX shells alike.
    python = Path(sys.executable).as_posix()
    return f'"{python}" "{script.as_posix()}" headers'


def configure_claude_code(script):
    claude = shutil.which("claude")
    if not claude:
        raise SetupError("Claude Code was not found on PATH.")
    config = {"type": "http", "url": MCP_URL, "headersHelper": headers_helper_command(script)}
    subprocess.run([claude, "mcp", "remove", SERVER_NAME, "-s", "user"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    result = subprocess.run(
        [claude, "mcp", "add-json", SERVER_NAME, json.dumps(config), "--scope", "user"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise SetupError(f"Claude Code rejected the configuration: {result.stdout.strip()}")
    say("    Claude Code: registered. It fetches a fresh token each time it connects.")


def read_cursor_config():
    if not CURSOR_CONFIG.exists():
        return {}
    try:
        data = json.loads(CURSOR_CONFIG.read_text(encoding="utf-8"))
    except ValueError:
        raise SetupError(f"{CURSOR_CONFIG} is not valid JSON, so it was left unchanged.")
    if not isinstance(data, dict):
        raise SetupError(f"{CURSOR_CONFIG} has an unexpected format, so it was left unchanged.")
    return data


def write_cursor_config(data):
    CURSOR_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if CURSOR_CONFIG.exists():
        backup = CURSOR_CONFIG.with_name(f"mcp.json.backup-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(CURSOR_CONFIG, backup)
        set_private(backup)
    temporary = CURSOR_CONFIG.with_name("mcp.json.tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    set_private(temporary)
    os.replace(temporary, CURSOR_CONFIG)


def configure_cursor(token, project):
    data = read_cursor_config()
    data.setdefault("mcpServers", {})[SERVER_NAME] = {
        "url": MCP_URL,
        "headers": {"Authorization": f"Bearer {token}", "x-goog-user-project": project},
    }
    write_cursor_config(data)
    say(f"    Cursor: registered in {CURSOR_CONFIG}")
    say("    Cursor uses a fixed token that lasts about an hour and is stored as plain text.")
    say(f"    To renew it, run: {self_command('refresh')}")


def resolve_clients(choice):
    if choice == "both":
        return ["claude-code", "cursor"]
    if choice != "auto":
        return [] if choice == "none" else [choice]
    if shutil.which("claude"):
        return ["claude-code"]
    if CURSOR_CONFIG.parent.exists():
        return ["cursor"]
    return []


# --- commands ---------------------------------------------------------------

def cmd_setup(args):
    step(1, "Checking gcloud")
    gcloud = ensure_gcloud()

    step(2, "Checking your Google sign-in")
    account = gcloud_value(gcloud, ["config", "get-value", "account"])
    if not account:
        if run_gcloud(gcloud, ["auth", "login", "--brief"], capture=False).returncode != 0:
            raise SetupError("gcloud sign-in did not finish.")
        account = gcloud_value(gcloud, ["config", "get-value", "account"])
    say(f"    Signed in as: {account}")

    step(3, "Choosing a Google Cloud project")
    project = choose_project(gcloud, args.project)
    save_config(project=project)
    say(f"    Using: {project}")

    step(4, "Enabling the Gemini Notebook API")
    enabled = run_gcloud(gcloud, ["services", "enable", API_NAME, f"--project={project}"])
    if enabled.returncode != 0:
        raise SetupError(f"Could not enable the API:\n{(enabled.stderr or '').strip()}")
    say("    Enabled.")

    step(5, "Signing in with the notebook permission")
    tools = None
    if not args.force_login:
        try:
            tools = list_tools(mint_token(gcloud), project)
            say("    An existing sign-in already works, so this step is skipped.")
        except SetupError:
            tools = None
    if tools is None:
        client_file = find_client_file(project, args.client_file)
        warn_if_synced(client_file)
        save_config(client_file=str(client_file))
        adc_login(gcloud, project, client_file)

    step(6, "Testing the connection")
    token = mint_token(gcloud)
    tools = list_tools(token, project)
    say(f"    Connected. {len(tools)} tools available: {', '.join(tools)}")

    step(7, "Configuring your MCP client")
    script = install_self()
    clients = resolve_clients(args.client)
    if not clients:
        say("    No client was configured. Run again with --client claude-code or --client cursor.")
    if "claude-code" in clients:
        configure_claude_code(script)
    if "cursor" in clients:
        configure_cursor(token, project)
    save_config(clients=clients)

    say("\nDone. Restart your MCP client to load the new server.")
    return 0


def cmd_login(args):
    gcloud = require_gcloud()
    project = args.project or load_config().get("project")
    if not valid_project(project):
        raise SetupError("No project saved. Run the setup first, or pass --project.")
    client_file = find_client_file(project, args.client_file)
    warn_if_synced(client_file)
    save_config(project=project, client_file=str(client_file))
    adc_login(gcloud, project, client_file)
    token = mint_token(gcloud)
    say(f"Connected. {len(list_tools(token, project))} tools available.")
    if "cursor" in load_config().get("clients", []):
        configure_cursor(token, project)
    return 0


def cmd_headers(_args):
    """Called by Claude Code. stdout must contain only the JSON headers."""
    project = load_config().get("project")
    if not valid_project(project):
        raise SetupError("No project saved. Run the setup first.")
    token = mint_token(require_gcloud())
    print(json.dumps({"Authorization": f"Bearer {token}", "x-goog-user-project": project}))
    return 0


def cmd_refresh(_args):
    project = load_config().get("project")
    if not valid_project(project):
        raise SetupError("No project saved. Run the setup first.")
    if SERVER_NAME not in read_cursor_config().get("mcpServers", {}):
        raise SetupError("Cursor is not configured, so there is nothing to refresh.")
    configure_cursor(mint_token(require_gcloud()), project)
    return 0


def cmd_verify(args):
    project = args.project or load_config().get("project")
    if not valid_project(project):
        raise SetupError("No project saved. Run the setup first, or pass --project.")
    tools = list_tools(mint_token(require_gcloud()), project)
    say(f"Connected to {MCP_URL} using {project}.")
    say(f"{len(tools)} tools available: {', '.join(tools)}")
    return 0


def cmd_uninstall(_args):
    if not confirm(f"Remove '{SERVER_NAME}' from Claude Code and Cursor, and delete {HOME_DIR}?"):
        say("Nothing was changed.")
        return 0
    claude = shutil.which("claude")
    if claude:
        subprocess.run([claude, "mcp", "remove", SERVER_NAME, "-s", "user"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cursor = read_cursor_config()
    if SERVER_NAME in cursor.get("mcpServers", {}):
        del cursor["mcpServers"][SERVER_NAME]
        write_cursor_config(cursor)
    if HOME_DIR.exists():
        # On Windows a running script can usually still delete itself only after exit,
        # so ignore errors and report what is left.
        shutil.rmtree(HOME_DIR, ignore_errors=True)
    say("Removed the client entries and saved settings.")
    if HOME_DIR.exists():
        say(f"Could not fully delete {HOME_DIR}. You can delete it by hand.")
    say("Not changed: your OAuth client file, the Google Cloud project and the API setting.")
    say("To also remove the Google sign-in: gcloud auth application-default revoke")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Connect an MCP client to the Gemini Notebook MCP server.")
    parser.add_argument("command", nargs="?", default="setup",
                        choices=["setup", "login", "verify", "refresh", "headers", "uninstall"],
                        help="default: setup")
    parser.add_argument("--project", help="Google Cloud project ID")
    parser.add_argument("--client-file", help="path to your OAuth Desktop client JSON")
    parser.add_argument("--client", default="auto",
                        choices=["auto", "claude-code", "cursor", "both", "none"],
                        help="MCP client to configure (default: auto)")
    parser.add_argument("--force-login", action="store_true", help="sign in again even if a sign-in works")
    return parser


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    args = build_parser().parse_args()
    commands = {
        "setup": cmd_setup,
        "login": cmd_login,
        "verify": cmd_verify,
        "refresh": cmd_refresh,
        "headers": cmd_headers,
        "uninstall": cmd_uninstall,
    }
    try:
        return commands[args.command](args)
    except SetupError as error:
        print(f"\nERROR: {error}", file=sys.stderr, flush=True)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr, flush=True)
        return 130


if __name__ == "__main__":
    sys.exit(main())
