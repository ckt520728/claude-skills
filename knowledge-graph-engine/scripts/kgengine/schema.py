"""Pydantic contracts for every LLM call (structured outputs)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .ontology import ENTITY_TYPES, PREDICATES

EntityType = Literal[tuple(ENTITY_TYPES)]  # type: ignore[valid-type]
Predicate = Literal[tuple(PREDICATES)]  # type: ignore[valid-type]


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
