"""The `jev` provider: POST https://api.typesafe.ai/v1/systemone.

Standard library only. If `typesafe-sdk` is installed you may prefer it; this
exists so the skill has no install step and works in a hook where adding a
dependency is a nuisance.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Mapping

from ..client import JevError, register_provider
from ..types import Question

DEFAULT_ENDPOINT = os.environ.get(
    "TYPESAFE_ENDPOINT", "https://api.typesafe.ai/v1/systemone"
)


def _api_key() -> str:
    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if not key:
        raise JevError(
            "TYPESAFE_API_KEY is not set. Export it, or run with "
            "JEV_PROVIDER=llm to use a chat model as a fallback backend."
        )
    return key


@register_provider("jev")
def call(
    state: Mapping[str, Any] | str,
    questions: Mapping[str, Question],
    model: str,
    timeout: float,
) -> Mapping[str, Any]:
    payload = {
        "model": model,
        "state": state,
        "questions": {qid: q.to_wire() for qid, q in questions.items()},
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        DEFAULT_ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:2000]
        raise JevError(
            f"{_explain(exc.code)} (HTTP {exc.code}): {detail}",
            status=exc.code,
            body=detail,
        ) from exc
    except urllib.error.URLError as exc:
        raise JevError(f"Transport failure calling {DEFAULT_ENDPOINT}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise JevError(f"Timed out after {timeout}s calling {DEFAULT_ENDPOINT}") from exc
    except json.JSONDecodeError as exc:
        raise JevError(f"Response was not valid JSON: {exc}") from exc


def _explain(status: int) -> str:
    return {
        401: "Invalid API key -- replace TYPESAFE_API_KEY",
        422: "Validation failure -- check a named request field against your question spec",
        429: "Rate limited -- back off, and lower concurrency if this is sustained",
        529: "Service overloaded -- back off and retry later",
    }.get(status, "Request failed")
