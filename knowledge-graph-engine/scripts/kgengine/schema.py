"""Pydantic contracts for every LLM call (structured outputs)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .ontology import ENTITY_TYPES, PREDICATES, TIMESCALES

EntityType = Literal[tuple(ENTITY_TYPES)]  # type: ignore[valid-type]
Predicate = Literal[tuple(PREDICATES)]  # type: ignore[valid-type]
Timescale = Literal[tuple(TIMESCALES)]  # type: ignore[valid-type]


def _require_timescale(schema: dict, _cls) -> None:
    # default keeps old rows/fixtures valid, but the LLM must always state it
    if "timescale" not in schema.setdefault("required", []):
        schema["required"].append("timescale")


class Entity(BaseModel):
    name: str = Field(description="Most complete name used in the text; expand acronyms as 'Full Name (ACRONYM)' when the text defines them")
    type: EntityType
    description: str = Field(description="One sentence grounded in this text; used later for disambiguation")


class Relation(BaseModel):
    source: str = Field(description="Exact name of an extracted entity")
    predicate: Predicate
    target: str = Field(description="Exact name of an extracted entity")
    evidence: str = Field(description="Short verbatim or near-verbatim supporting phrase from the text (<=30 words)")
    confidence: float = Field(ge=0, le=1, description="1.0 = explicitly reported finding; 0.5 = hypothesis/speculation")
    timescale: Timescale = Field(default="unspecified", description="acute = single bout/session effect; chronic = repeated training (weeks+) or long-term habitual activity/fitness; unspecified = not an intervention effect or not stated")

    model_config = ConfigDict(json_schema_extra=_require_timescale)


class ExtractedGraph(BaseModel):
    entities: list[Entity]
    relations: list[Relation]


class Cluster(BaseModel):
    canonical: str
    aliases: list[str]


class ResolvedClusters(BaseModel):
    clusters: list[Cluster]


class EntityProfile(BaseModel):
    summary: str
    key_facts: list[str]


class Answer(BaseModel):
    answer: str
    cited_edges: list[str] = Field(description="Edges used, as '(source) -[PREDICATE]-> (target)'")
    confidence: Literal["high", "medium", "low"]
    gaps: list[str] = Field(description="What the graph does not cover that would be needed")
