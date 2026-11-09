#!/usr/bin/env python3
"""
cli_bridge.py - call Claude, ChatGPT (Codex CLI) and Gemini (Gemini CLI) through their own logins.

No API key is read. Each vendor CLI holds its login; this script only runs it as a subprocess.
Cost is flat (subscription), so cost is reported as 0 and the plan's own usage limit is the only cap.

    python cli_bridge.py --status
    python cli_bridge.py --provider chatgpt --model gpt-6-astra --effort high --prompt "Reply: PONG"
    echo "long prompt" | python cli_bridge.py --provider gemini --model gemini-4-argon

Use it from code:  from cli_bridge import ask;  ask("chatgpt", "gpt-6-astra", "prompt", system="...")
Stdlib only. Python 3.9+. Windows, macOS, Linux.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

EXECUTABLES = {"chatgpt": "codex", "gemini": "gemini", "claude": "claude"}
EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh")
INSTALL_HINT = {
    "chatgpt": "npm install -g @openai/codex, then: codex login",
    "gemini": "npm install -g @google/gemini-cli, then run `gemini` once and choose Login with Google",
    "claude": "install Claude Code, then run `claude` once to log in",
}


class BridgeError(Exception):
    """The CLI could not answer. Never replaced by placeholder text."""


def _exe(provider: str) -> Optional[str]:
    if provider not in EXECUTABLES:
        raise BridgeError(f'Unknown provider "{provider}". Use one of: {", ".join(EXECUTABLES)}.')
    # shutil.which resolves the npm .cmd shim on Windows.
    return shutil.which(EXECUTABLES[provider])


def split_effort(model: str) -> Tuple[str, str]:
    """'gpt-6.1-sol@high' -> ('gpt-6.1-sol', 'high'). An unknown suffix is an error, not silently dropped."""
    if "@" not in model:
        return model, ""
    base, effort = model.rsplit("@", 1)
    if effort not in EFFORTS:
        raise BridgeError(f'Unknown reasoning effort "{effort}" in "{model}". Use one of: {", ".join(EFFORTS)}.')
    return base, effort


def status(provider: str) -> Tuple[bool, str]:
    """Installed and logged in? Reads local state only; nothing is sent to a model."""
    exe = _exe(provider)
    if not exe:
        return False, f"{EXECUTABLES[provider]} not found. {INSTALL_HINT[provider]}"
    if provider == "chatgpt":
        proc = subprocess.run([exe, "login", "status"], capture_output=True, text=True, encoding="utf-8", timeout=30)
        said = (proc.stdout + proc.stderr).strip()
        return proc.returncode == 0 and "logged in" in said.lower(), said or "not logged in; run: codex login"
    if provider == "gemini":
        # Measured: a call authenticated with no oauth_creds.json present, so this file is NOT a reliable signal.
        # A False here can be a false alarm; the real test is one call.
        ok = (Path.home() / ".gemini" / "oauth_creds.json").exists()
        return ok, "Google login file found" if ok else "login state not readable; run one call to verify, else run `gemini`"
    return True, "Claude Code login is used by the claude CLI"


def _command(provider: str, exe: str, model: str, effort: str, out_file: str) -> List[str]:
    if provider == "chatgpt":
        cmd = [exe, "exec", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config",
               "--sandbox", "read-only", "-m", model, "-o", out_file]
        if effort:
            cmd += ["-c", f"model_reasoning_effort={effort}"]  # unquoted: Codex falls back to a literal string
        return cmd + ["-"]  # "-" = read the prompt from stdin
    if provider == "gemini":
        # --skip-trust: a fresh temp dir is never "trusted", and headless mode exits 55 without it.
        return [exe, "-m", model, "-o", "text", "--approval-mode", "plan", "--skip-trust",
                "-p", "Answer the message provided on stdin."]
    return [exe, "-p", "--model", model, "--output-format", "text"]


def ask(provider: str, model: str, prompt: str, system: str = "", effort: str = "", timeout: int = 900) -> str:
    """One stateless turn. For a multi-turn exchange, resend the transcript in `prompt`."""
    exe = _exe(provider)
    if not exe:
        raise BridgeError(f"{EXECUTABLES[provider]} CLI is not installed. {INSTALL_HINT[provider]}")
    model, suffix = split_effort(model)
    text_in = f"{system}\n\n{prompt}" if system else prompt
    with tempfile.TemporaryDirectory(prefix="bridge-") as work:  # empty cwd: the agent has nothing to read
        out_file = os.path.join(work, "last_message.txt")
        try:
            proc = subprocess.run(_command(provider, exe, model, suffix or effort, out_file), input=text_in,
                                  cwd=work, text=True, encoding="utf-8", capture_output=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise BridgeError(f"{provider} CLI failed: {e}") from e
        if proc.returncode != 0:
            raise BridgeError(f"{provider} CLI exit {proc.returncode}: {(proc.stderr or proc.stdout)[-400:]}")
        if provider == "chatgpt":
            text = Path(out_file).read_text(encoding="utf-8") if os.path.exists(out_file) else ""
        else:
            text = proc.stdout
    if not text.strip():
        raise BridgeError(f"{provider} CLI returned no text.")
    return text.strip()


def tokens_used(codex_output: str) -> int:
    """Codex prints 'tokens used\\n7,620' in its log."""
    m = re.search(r"tokens used\s*([\d,]+)", codex_output)
    return int(m.group(1).replace(",", "")) if m else 0


def main() -> int:
    # Windows consoles default to a legacy code page (cp950, cp1252) and crash on other scripts.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--status", action="store_true", help="check install and login for every provider; spends nothing")
    parser.add_argument("--provider", choices=list(EXECUTABLES))
    parser.add_argument("--model")
    parser.add_argument("--effort", default="", choices=("",) + EFFORTS)
    parser.add_argument("--system", default="")
    parser.add_argument("--prompt", default="", help="omit to read the prompt from stdin")
    args = parser.parse_args()
    if args.status:
        for name in EXECUTABLES:
            ok, detail = status(name)
            print(f"{name:8} {'available  ' if ok else 'UNAVAILABLE'} {detail}")
        return 0
    if not (args.provider and args.model):
        parser.error("--provider and --model are required unless --status is given")
    prompt = args.prompt or sys.stdin.read()
    try:
        print(ask(args.provider, args.model, prompt, args.system, args.effort))
    except BridgeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
