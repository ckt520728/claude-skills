"""Life OS — stdlib-only decision and metrics layer for the Obsidian vault.

Python 3.9+ (verified 3.9.12). No third-party imports anywhere in this package:
it runs inside hooks, where a dependency is a real cost (invariant 1).

The decision layer is the jev-engineering skill, vendored verbatim in `lifeos/jev/`
(see scripts/sync_jev.py). `layer.py` and `gtd.py` are the only Life OS code on top of it.
"""

from . import (clinical, config, gtd, layer, metrics, triage,  # noqa: F401
               unlock, vault)

__version__ = "0.2.0"

__all__ = ["clinical", "config", "gtd", "layer", "metrics", "triage",
           "unlock", "vault", "__version__"]
