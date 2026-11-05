"""
Model providers. The pipeline only needs one operation: send a turn in a conversation and get back
text plus real usage. Add a provider by implementing Conversation; nothing else changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, List, Optional

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
        self._model = model
        self._url = settings["base_url"].rstrip("/") + "/chat/completions"
        key_env = settings.get("api_key_env") or ""
        self._key = os.environ.get(key_env, "") if key_env else ""
        if key_env and not self._key:
            raise ProviderError(f"Set {key_env} in .env to use this provider.")
        self._prices = settings.get("price_per_mtok") or {}
        self._messages: List[dict] = [{"role": "system", "content": system}]

    def _post(self) -> dict:
        headers = {"Authorization": f"Bearer {self._key}"} if self._key else {}
        try:
            resp = requests.post(self._url, json={"model": self._model, "messages": self._messages}, headers=headers, timeout=600)
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


def budget_problem() -> Optional[str]:
    """A spending limit is only real if cost is known. Refuse to run a paid endpoint blind."""
    settings = CONFIG["provider"]
    if settings["type"] == "openai_compatible" and not settings.get("free") and not settings.get("price_per_mtok"):
        return 'Set provider.price_per_mtok in project.json, or "free": true for a local model, so the budget can be enforced.'
    return None


def open_conversation(system: str, model: str, budget_usd: float) -> Conversation:
    if conversation_factory is not None:
        return conversation_factory(system, model, budget_usd)
    settings = CONFIG["provider"]
    if settings["type"] == "claude":
        return ClaudeConversation(system, model, budget_usd)
    if settings["type"] == "openai_compatible":
        return OpenAICompatibleConversation(system, model, settings)
    raise ProviderError(f"Unknown provider type: {settings['type']}")
