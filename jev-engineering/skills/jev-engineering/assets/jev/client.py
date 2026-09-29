"""decide(): one call, pluggable provider, no third-party dependencies.

    from jev import decide, Choice
    r = decide(state={...}, questions={"risk": Choice(...)})
    r.answers["risk"].choice / .confidence / .probabilities

Provider selection, in order: the `provider=` argument, then $JEV_PROVIDER,
then "jev". A provider is one callable with the signature

    provider(state, questions, model, timeout) -> wire dict

returning the documented shape {"model", "answers", "usage"}.
"""

from __future__ import annotations

import os
import random
import time
from typing import Any, Callable, Mapping

from .types import Question, Result

DEFAULT_MODEL = os.environ.get("JEV_MODEL", "jev-1.13.0")
DEFAULT_TIMEOUT = float(os.environ.get("JEV_TIMEOUT", "10"))
DEFAULT_RETRIES = int(os.environ.get("JEV_RETRIES", "3"))

# Retry these; everything else is a caller problem and fails fast.
RETRY_STATUSES = (429, 500, 502, 503, 529)

Provider = Callable[[Mapping[str, Any], Mapping[str, Question], str, float], Mapping[str, Any]]

_PROVIDERS: dict[str, Provider] = {}


class JevError(RuntimeError):
    """A decision call failed. `.status` is the HTTP status when there was one.

    The right fallback is fork-specific, so this is raised rather than swallowed:
    a tool gate should fall back to `ask`, a control loop to the null action,
    triage to `needs-human`, an eval to the frontier path.
    """

    def __init__(self, message: str, *, status: int | None = None, body: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.body = body


def register_provider(name: str) -> Callable[[Provider], Provider]:
    """Decorator registering a backend under `name`."""

    def _register(fn: Provider) -> Provider:
        _PROVIDERS[name] = fn
        return fn

    return _register


def available_providers() -> list[str]:
    _load_builtins()
    return sorted(_PROVIDERS)


_loaded = False


def _load_builtins() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    from .providers import jev_api, llm  # noqa: F401  (registers on import)


def decide(
    state: Mapping[str, Any] | str,
    questions: Mapping[str, Question],
    *,
    model: str | None = None,
    provider: str | None = None,
    timeout: float | None = None,
    retries: int | None = None,
) -> Result:
    """Send one state and a map of questions; get typed answers back.

    Every question in a single call is evaluated in parallel against the same
    state, so batching is nearly free (rule 5). Questions cannot read each
    other's answers -- if a decision needs a fresh lookup, do the lookup and
    make a second call.
    """
    _load_builtins()

    if not questions:
        raise ValueError("decide() needs at least one question.")

    name = provider or os.environ.get("JEV_PROVIDER") or "jev"
    if name not in _PROVIDERS:
        raise JevError(
            f"Unknown provider {name!r}. Available: {', '.join(sorted(_PROVIDERS))}. "
            f"Register your own with @register_provider."
        )

    fn = _PROVIDERS[name]
    mdl = model or DEFAULT_MODEL
    tmo = DEFAULT_TIMEOUT if timeout is None else timeout
    attempts = DEFAULT_RETRIES if retries is None else retries

    last: JevError | None = None
    for attempt in range(attempts):
        started = time.perf_counter()
        try:
            wire = fn(state, questions, mdl, tmo)
        except JevError as exc:
            last = exc
            if exc.status not in RETRY_STATUSES or attempt == attempts - 1:
                raise
            # Exponential backoff with jitter. A sustained 429 means lower your
            # concurrency, not retry harder.
            time.sleep(min(8.0, 0.5 * (2**attempt)) * (0.5 + random.random()))
            continue

        latency_ms = (time.perf_counter() - started) * 1000.0
        result = Result.from_wire(wire, latency_ms=latency_ms, provider=name)

        missing = set(questions) - set(result.answers)
        if missing:
            raise JevError(
                f"Provider {name!r} returned no answer for: {', '.join(sorted(missing))}. "
                f"An invalid or absent answer counts as an error, not as an abstention."
            )
        return result

    raise last or JevError("decide() exhausted retries without a result.")
