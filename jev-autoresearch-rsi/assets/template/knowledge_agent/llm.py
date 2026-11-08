"""
Model providers. The pipeline only needs one operation: send a turn in a conversation and get back
text plus real usage. Add a provider by implementing Conversation; nothing else changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import requests

from .config import CONFIG


class ProviderError(Exception):
    """The model could not answer. Never replaced by placeholder text."""


@dataclass
class Reply:
    text: str
    cost_usd: float = 0.0
    tokens: int = 0


class Conversation:
    """One conversation. A repair turn must be able to see the answer it is repairing."""

    async def __aenter__(self) -> "Conversation":
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    async def send(self, prompt: str) -> Reply:
        raise NotImplementedError


class ClaudeConversation(Conversation):
    """Claude Agent SDK: uses the Claude Code login, or ANTHROPIC_API_KEY when it is set."""

    def __init__(self, system: str, model: str, budget_usd: float):
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

        self._client = ClaudeSDKClient(options=ClaudeAgentOptions(
            model=model, system_prompt=system, tools=[], allowed_tools=[], max_turns=1,
            max_budget_usd=budget_usd,
            # Do not load the user's own settings, MCP servers or skills: results stay reproducible.
            setting_sources=[], strict_mcp_config=True, skills=[],
        ))
        self._seen_cost = 0.0

    async def __aenter__(self) -> "ClaudeConversation":
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *exc) -> bool:
        await self._client.__aexit__(*exc)
        return False

    async def send(self, prompt: str) -> Reply:
        from claude_agent_sdk import AssistantMessage, ClaudeSDKError, ResultMessage, TextBlock

        last_text, result = "", None
        try:
            await self._client.query(prompt)
            async for message in self._client.receive_response():
                if isinstance(message, AssistantMessage):
                    last_text = "".join(b.text for b in message.content if isinstance(b, TextBlock)) or last_text
                elif isinstance(message, ResultMessage):
                    result = message
        except ClaudeSDKError as e:
            raise ProviderError(str(e)) from e
        if result is None:
            raise ProviderError("No result from Claude.")
        # total_cost_usd accumulates within a session, so charge only the increase.
        total = result.total_cost_usd or 0.0
        cost = max(0.0, total - self._seen_cost)
        self._seen_cost = max(self._seen_cost, total)
        if result.is_error:
            raise ProviderError(result.result or "; ".join(result.errors or []) or result.subtype)
        usage = result.usage or {}
        tokens = sum(usage.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "output_tokens"))
        return Reply(result.result or last_text, cost, tokens)


class OpenAICompatibleConversation(Conversation):
    """Any /chat/completions endpoint: OpenAI, Gemini's OpenAI endpoint, OpenRouter, Ollama, LM Studio."""

    def __init__(self, system: str, model: str, settings: dict):
        # "gpt-6.1-sol@high" means model gpt-6.1-sol with reasoning_effort "high"; the price is the base model's.
        model, self._effort = split_effort(model)
        self._model = model
        self._url = settings["base_url"].rstrip("/") + "/chat/completions"
        key_env = settings.get("api_key_env") or ""
        self._key = os.environ.get(key_env, "") if key_env else ""
        if key_env and not self._key:
            raise ProviderError(f"Set {key_env} in .env to use this provider.")
        prices = settings.get("price_per_mtok") or {}
        # Either one {"input","output"} pair for the endpoint, or one pair per model id.
        self._prices = prices.get(model, {}) if isinstance(prices.get(model), dict) else prices
        self._messages: List[dict] = [{"role": "system", "content": system}]

    def _post(self) -> dict:
        headers = {"Authorization": f"Bearer {self._key}"} if self._key else {}
        try:
            body = {"model": self._model, "messages": self._messages}
            if self._effort:
                body["reasoning_effort"] = self._effort
            resp = requests.post(self._url, json=body, headers=headers, timeout=600)
        except requests.RequestException as e:
            raise ProviderError(str(e)) from e
        if resp.status_code != 200:
            # The key is in a header, so the response body is safe to show.
            raise ProviderError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    async def send(self, prompt: str) -> Reply:
        import anyio

        self._messages.append({"role": "user", "content": prompt})
        data = await anyio.to_thread.run_sync(self._post)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError(f"Unexpected response: {str(data)[:300]}") from e
        self._messages.append({"role": "assistant", "content": text})
        usage = data.get("usage") or {}
        given, made = usage.get("prompt_tokens") or 0, usage.get("completion_tokens") or 0
        cost = (given * self._prices.get("input", 0) + made * self._prices.get("output", 0)) / 1_000_000
        return Reply(text or "", cost, given + made)


# Tests replace this with a function(system, model, budget) -> Conversation.
conversation_factory: Optional[Callable[[str, str, float], Conversation]] = None


def resolve(model: str) -> Tuple[str, dict, str]:
    """
    A model reference is "provider:model" (for example "claude:claude-opus-5-5" or "openai:<id>").
    A bare model id uses the single legacy "provider" block. Returns (provider name, settings, model id).
    """
    providers = CONFIG.get("providers") or {}
    if ":" in model:
        name, model_id = model.split(":", 1)
        if name in providers:
            return name, providers[name], model_id
    return CONFIG["provider"]["type"], CONFIG["provider"], model


def tier_models(tier: str) -> List[str]:
    return list((CONFIG.get("tiers") or {}).get(tier) or [])


def all_model_refs() -> List[str]:
    refs = [m for tier in (CONFIG.get("tiers") or {}).values() for m in tier]
    return list(dict.fromkeys(refs + list(CONFIG["provider"].get("models", []))))


EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh")


def split_effort(model_id: str) -> Tuple[str, str]:
    """'gpt-6.1-sol@high' -> ('gpt-6.1-sol', 'high'). An unknown suffix is a config error, not silently dropped."""
    if "@" not in model_id:
        return model_id, ""
    base, effort = model_id.rsplit("@", 1)
    if effort not in EFFORTS:
        raise ProviderError(f'Unknown reasoning effort "{effort}" in "{model_id}". Use one of: {", ".join(EFFORTS)}.')
    return base, effort


def _price_known(settings: dict, model_id: str) -> bool:
    if settings.get("type") != "openai_compatible" or settings.get("free"):
        return True
    model_id = model_id.split("@", 1)[0]
    prices = settings.get("price_per_mtok") or {}
    if isinstance(prices.get(model_id), dict):
        return bool(prices[model_id])
    return "input" in prices or "output" in prices


def budget_problem(models: Optional[List[str]] = None) -> Optional[str]:
    """A spending limit is only real if cost is known. Refuse to run a paid endpoint blind."""
    if models is None:
        settings = CONFIG["provider"]
        if settings["type"] == "openai_compatible" and not settings.get("free") and not settings.get("price_per_mtok"):
            return 'Set provider.price_per_mtok in project.json, or "free": true for a local model, so the budget can be enforced.'
        return None
    for ref in models:
        name, settings, model_id = resolve(ref)
        if not _price_known(settings, model_id):
            return f'Set providers.{name}.price_per_mtok for "{model_id}" in project.json so the budget can be enforced.'
    return None


def provider_status() -> List[dict]:
    """What each configured provider can do right now. Nothing here calls a paid endpoint."""
    rows = []
    for name, settings in (CONFIG.get("providers") or {"default": CONFIG["provider"]}).items():
        models = [r for r in all_model_refs() if r.startswith(name + ":")]
        if settings.get("type") == "claude":
            try:
                import claude_agent_sdk  # noqa: F401
                ok, detail = True, "Claude Agent SDK installed (uses the Claude Code login or ANTHROPIC_API_KEY)"
            except ImportError:
                ok, detail = False, "claude-agent-sdk is not installed"
        else:
            key_env = settings.get("api_key_env") or ""
            if key_env and not os.environ.get(key_env):
                ok, detail = False, f"Set {key_env} in .env"
            elif not models:
                ok, detail = False, "No models in tiers; run run_agent.py --models " + name + " and add ids to project.json tiers"
            elif not all(_price_known(settings, resolve(m)[2]) for m in models):
                ok, detail = False, "Add price_per_mtok for each model so the budget can be enforced"
            else:
                ok, detail = True, f"Key present; {len(models)} model(s) configured (not yet called)"
        rows.append({"name": name, "type": settings.get("type", ""), "available": ok, "detail": detail, "models": models})
    return rows


def available(model: str) -> bool:
    name = resolve(model)[0]
    return any(r["name"] == name and r["available"] for r in provider_status()) or not CONFIG.get("providers")


def list_models(name: str) -> List[str]:
    """Read model ids from the provider itself (GET /models). Used instead of guessing ids."""
    settings = (CONFIG.get("providers") or {}).get(name)
    if not settings or settings.get("type") != "openai_compatible":
        raise ProviderError(f"{name} is not an OpenAI-compatible provider in project.json")
    key = os.environ.get(settings.get("api_key_env") or "", "")
    if settings.get("api_key_env") and not key:
        raise ProviderError(f"Set {settings['api_key_env']} in .env first.")
    try:
        resp = requests.get(settings["base_url"].rstrip("/") + "/models", headers={"Authorization": f"Bearer {key}"} if key else {}, timeout=30)
    except requests.RequestException as e:
        raise ProviderError(str(e)) from e
    if resp.status_code != 200:
        raise ProviderError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json().get("data") or resp.json().get("models") or []
    return sorted(str(m.get("id") or m.get("name", "")).removeprefix("models/") for m in data)


def open_conversation(system: str, model: str, budget_usd: float) -> Conversation:
    if conversation_factory is not None:
        return conversation_factory(system, model, budget_usd)
    _, settings, model_id = resolve(model)
    if settings["type"] == "claude":
        return ClaudeConversation(system, model_id, budget_usd)
    if settings["type"] == "openai_compatible":
        return OpenAICompatibleConversation(system, model_id, settings)
    raise ProviderError(f"Unknown provider type: {settings['type']}")
