"""Paths and defaults (override with env vars)."""
from __future__ import annotations

import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("KG_DB", PROJECT / "data" / "kg.sqlite"))
OUT_DIR = Path(os.environ.get("KG_OUT", PROJECT / "out"))

# The research library. Used by `kg ingest --library`.
# Override with KG_LIBRARY="dir1;dir2".
LIBRARY_ROOTS = [p for p in os.environ.get("KG_LIBRARY", "").split(";") if p]
# Filename/path filter for the topic-focused first pass.
TOPIC_INCLUDE = (r"exercis|physical|activit|fitness|aerobic|resistance|tai.?chi|walk|sport|"
                 r"alpha|IAPF|PAF|EEG|MEG|ERP|P300|oscillat|theta|gamma|"
                 r"hippocamp|MRI|imaging|white.matter|brain.age|aging|ageing|reserve|MCI|cogniti")


def open_kg(db: str | Path | None = None):
    from .graph import KnowledgeGraph
    from .store import Store
    store = Store(db or DB_PATH)
    return store, KnowledgeGraph(store)


def provider(name: str | None = None):
    from .providers import get_provider
    return get_provider(name)
