"""Model-agnostic LLM providers.

Every provider implements two calls:
    structured(prompt, schema, role, system) -> pydantic instance
    text(prompt, role, system) -> str
`role` is "fast" (high-volume extraction) or "smart" (resolution, summaries, QA),
mirroring the cookbook's Haiku/Sonnet split.

Providers:
    claude-cli : headless Claude Code (`claude -p --json-schema`) -> uses your Claude login, no API key
    anthropic  : Anthropic Messages API (ANTHROPIC_API_KEY), tool-forced structured output
    ollama     : local models via Ollama's /api/chat with `format=<json schema>`
    openai     : any OpenAI-compatible /chat/completions endpoint (OpenAI, vLLM, LM Studio, OpenRouter...)
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import time
from typing import Type, TypeVar

import httpx
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODELS = {
    "claude-cli": {"fast": "haiku", "smart": "sonnet"},
    "anthropic": {"fast": "claude-haiku-5-5", "smart": "claude-sonnet-5-5"},
    "ollama": {"fast": "gemma4:latest", "smart": "gemma4:26b"},
    "openai": {"fast": "gpt-4o-mini", "smart": "gpt-4o"},
}


def inline_schema(model: Type[BaseModel]) -> dict:
    """Pydantic JSON schema with $refs inlined (some backends reject $defs)."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(copy.deepcopy(defs[node["$ref"].split("/")[-1]]))
            return {k: walk(v) for k, v in node.items() if k != "title"}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)


class Provider:
    name = "base"

    def __init__(self, fast: str | None = None, smart: str | None = None):
        d = DEFAULT_MODELS.get(self.name, {})
        self.models = {"fast": fast or d.get("fast"), "smart": smart or d.get("smart")}
        self.cost_usd = 0.0
        self.calls = 0

    def model_id(self, role: str) -> str:
        return self.models[role]

    def structured(self, prompt: str, schema: Type[T], role: str = "fast", system: str = "") -> T:
        raise NotImplementedError

    def text(self, prompt: str, role: str = "smart", system: str = "") -> str:
        raise NotImplementedError


def _claude_exe() -> str:
    """Prefer the native claude.exe over npm's claude.CMD shim: cmd.exe mangles quoting of the long
    --json-schema / --system-prompt arguments (and caps the command line at 8,191 chars)."""
    if os.environ.get("KG_CLAUDE_EXE"):
        return os.environ["KG_CLAUDE_EXE"]
    # A self-update can leave bin/claude.exe as a ~500-byte stub ("native binary not installed") while the
    # real binary sits in the platform package, so skip files under 1 MB.
    pkg = os.path.join(os.environ.get("APPDATA", ""), "npm", "node_modules", "@anthropic-ai", "claude-code")
    cands = [os.path.join(pkg, "bin", "claude.exe"),
             os.path.join(pkg, "node_modules", "@anthropic-ai", "claude-code-win32-x64", "claude.exe"),
             os.path.join(os.path.expanduser("~"), ".local", "bin", "claude.exe")]
    found = shutil.which("claude")
    if found and not found.lower().endswith((".cmd", ".bat")):
        cands.insert(0, found)
    for c in cands:
        if os.path.isfile(c) and os.path.getsize(c) > 1_000_000:
            return c
    return found or "claude"


class ClaudeCLIProvider(Provider):
    name = "claude-cli"

    def __init__(self, *a, timeout: int = 600, **kw):
        super().__init__(*a, **kw)
        self.exe = _claude_exe()
        self.timeout = timeout

    def _run(self, prompt: str, role: str, system: str, schema: dict | None) -> dict:
        cmd = [self.exe, "-p", "--model", self.model_id(role), "--output-format", "json",
               "--strict-mcp-config", "--tools", "", "--no-session-persistence",
               "--system-prompt", system or "You are a precise information-extraction engine."]
        if schema is not None:
            cmd += ["--json-schema", json.dumps(schema)]
        env = {**os.environ, "CLAUDE_CODE_ENTRYPOINT": "kgengine"}
        for attempt in range(6):
            try:
                proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                                      encoding="utf-8", errors="replace", timeout=self.timeout, env=env)
                break
            except OSError:
                # A Claude Code self-update can move/replace the binary mid-run (WinError 2/193/216):
                # wait, re-resolve, retry.
                if attempt == 5:
                    raise
                time.sleep(30 * (attempt + 1))
                self.exe = cmd[0] = _claude_exe()
        if proc.returncode != 0 and not proc.stdout.strip():
            raise RuntimeError(f"claude CLI failed: {proc.stderr[:500]}")
        out = json.loads(proc.stdout)
        if out.get("is_error"):
            raise RuntimeError(f"claude CLI error: {str(out.get('result'))[:500]}")
        self.calls += 1
        self.cost_usd += float(out.get("total_cost_usd") or 0)
        return out

    def structured(self, prompt, schema, role="fast", system=""):
        out = self._run(prompt, role, system, inline_schema(schema))
        data = out.get("structured_output")
        if data is None:
            data = json.loads(out.get("result", "{}"))
        return schema.model_validate(data)

    def text(self, prompt, role="smart", system=""):
        return self._run(prompt, role, system, None).get("result", "")


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        import anthropic
        self.client = anthropic.Anthropic()

    def structured(self, prompt, schema, role="fast", system=""):
        tool = {"name": "emit", "description": "Return the result.", "input_schema": inline_schema(schema)}
        kwargs = dict(model=self.model_id(role), max_tokens=8192, tools=[tool],
                      tool_choice={"type": "tool", "name": "emit"},
                      messages=[{"role": "user", "content": prompt}])
        if system:
            kwargs["system"] = system
        resp = self.client.messages.create(**kwargs)
        self.calls += 1
        block = next(b for b in resp.content if b.type == "tool_use")
        return schema.model_validate(block.input)

    def text(self, prompt, role="smart", system=""):
        kwargs = dict(model=self.model_id(role), max_tokens=4096,
                      messages=[{"role": "user", "content": prompt}])
        if system:
            kwargs["system"] = system
        resp = self.client.messages.create(**kwargs)
        self.calls += 1
        return "".join(b.text for b in resp.content if b.type == "text")


class OllamaProvider(Provider):
    name = "ollama"

    def __init__(self, *a, host: str | None = None, **kw):
        super().__init__(*a, **kw)
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    def _chat(self, prompt, role, system, fmt):
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        body = {"model": self.model_id(role), "messages": msgs, "stream": False, "options": {"temperature": 0}}
        if fmt is not None:
            body["format"] = fmt
        r = httpx.post(f"{self.host}/api/chat", json=body, timeout=900)
        r.raise_for_status()
        self.calls += 1
        return r.json()["message"]["content"]

    def structured(self, prompt, schema, role="fast", system=""):
        return schema.model_validate_json(self._chat(prompt, role, system, inline_schema(schema)))

    def text(self, prompt, role="smart", system=""):
        return self._chat(prompt, role, system, None)


class OpenAICompatProvider(Provider):
    name = "openai"

    def __init__(self, *a, base_url: str | None = None, api_key: str | None = None, **kw):
        super().__init__(*a, **kw)
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def _chat(self, prompt, role, system, schema):
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        body = {"model": self.model_id(role), "messages": msgs, "temperature": 0}
        if schema is not None:
            body["response_format"] = {"type": "json_schema",
                                       "json_schema": {"name": "out", "schema": schema}}
        r = httpx.post(f"{self.base_url}/chat/completions", json=body, timeout=600,
                       headers={"Authorization": f"Bearer {self.api_key}"})
        r.raise_for_status()
        self.calls += 1
        return r.json()["choices"][0]["message"]["content"]

    def structured(self, prompt, schema, role="fast", system=""):
        return schema.model_validate_json(self._chat(prompt, role, system, inline_schema(schema)))

    def text(self, prompt, role="smart", system=""):
        return self._chat(prompt, role, system, None)


PROVIDERS = {p.name: p for p in (ClaudeCLIProvider, AnthropicProvider, OllamaProvider, OpenAICompatProvider)}


def get_provider(name: str | None = None, fast: str | None = None, smart: str | None = None) -> Provider:
    name = name or os.environ.get("KG_PROVIDER") or ("anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "claude-cli")
    if name not in PROVIDERS:
        raise ValueError(f"Unknown provider {name!r}; choose from {sorted(PROVIDERS)}")
    return PROVIDERS[name](fast=fast or os.environ.get("KG_FAST_MODEL"), smart=smart or os.environ.get("KG_SMART_MODEL"))
