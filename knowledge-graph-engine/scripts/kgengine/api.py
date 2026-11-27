"""REST API (FastAPI). Run:  kg serve  ->  http://127.0.0.1:8765/docs  (OpenAPI UI)"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import pipeline, qa
from .config import open_kg, provider
from .viz import TEMPLATE, graph_payload

app = FastAPI(title="kgengine", version="0.1.0",
              description="Knowledge-graph engine: ingest, extract, resolve, query, visualize.")
_state: dict = {}


def kg():
    if "kg" not in _state:
        _state["store"], _state["kg"] = open_kg()
    return _state["kg"]


class IngestReq(BaseModel):
    paths: list[str] = []
    urls: list[str] = []
    include: str | None = None
    limit: int | None = None


class TextReq(BaseModel):
    title: str
    text: str


class BuildReq(BaseModel):
    max_chunks_per_doc: int | None = 2
    workers: int = 4
    resolve: bool = True


class AskReq(BaseModel):
    question: str
    hops: int = 2
    seeds: list[str] | None = None


@app.get("/stats")
def stats():
    return kg().stats()


@app.get("/search")
def search(q: str, limit: int = 10, type: str | None = None):
    return kg().search(q, limit, type)


@app.get("/entity/{name}")
def entity(name: str):
    e = kg().entity(name)
    if e is None:
        raise HTTPException(404, f"entity {name!r} not found")
    return e


@app.get("/neighbors/{name}")
def neighbors(name: str, depth: int = 1, predicates: str | None = None, types: str | None = None, min_weight: int = 1):
    return kg().neighbors(name, depth, predicates.split(",") if predicates else None,
                          types.split(",") if types else None, min_weight)


@app.get("/paths")
def paths(source: str, target: str, max_len: int = 4, limit: int = 20):
    return kg().paths(source, target, max_len, limit)


@app.get("/match")
def match(pattern: str, limit: int = 100, min_weight: int = 1):
    try:
        return kg().match(pattern, limit, min_weight)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/matrix")
def matrix(src_type: str = "INTERVENTION", tgt_type: str = "BIOMARKER", top: int = 40):
    return kg().evidence_matrix(src_type, tgt_type, top)


@app.get("/contradictions")
def contradictions():
    return kg().contradictions()


@app.get("/communities")
def communities(top: int = 12):
    return kg().communities(top)


@app.post("/ask")
def ask(req: AskReq):
    return qa.ask(kg(), provider(), req.question, req.hops, seeds=req.seeds)


@app.post("/ingest")
def ingest(req: IngestReq):
    store = kg().store
    rep = pipeline.ingest_paths(store, req.paths, req.include, limit=req.limit) if req.paths else {}
    for u in req.urls:
        pipeline.ingest_url(store, u)
    return rep


@app.post("/ingest/text")
def ingest_text(req: TextReq):
    doc_id, new = pipeline.ingest_text(kg().store, req.title, req.text)
    return {"doc_id": doc_id, "new": new}


@app.post("/build")
def build(req: BuildReq):
    k, p = kg(), provider()
    rep = {"extract": pipeline.extract(k.store, p, req.max_chunks_per_doc, req.workers, progress=lambda *_: None)}
    if req.resolve:
        rep["resolve"] = pipeline.resolve(k.store, p, progress=lambda *_: None)
    k.reload()
    return rep


@app.get("/viz", response_class=HTMLResponse)
def viz(center: str | None = None, depth: int = 2, max_nodes: int = 600):
    import json
    data = json.dumps(graph_payload(kg(), max_nodes=max_nodes, center=center, depth=depth), ensure_ascii=False)
    return TEMPLATE.replace("__TITLE__", "Knowledge Graph").replace("__DATA__", data.replace("</", "<\\/"))
