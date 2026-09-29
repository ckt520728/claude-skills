"""Backends. Importing a module registers it with the client.

    jev  -> POST api.typesafe.ai/v1/systemone            (default, production)
    llm  -> any OpenAI-compatible or Anthropic endpoint  (baseline, shadow, fallback)

Register your own with @register_provider("name") -- see 13-portability.md for
the one-callable contract.
"""

from . import jev_api, llm  # noqa: F401

__all__ = ["jev_api", "llm"]
