"""Command line:  python -m kgengine <command> ...   (alias `kg` after `pip install -e .`)

  ingest  PATH... [--library] [--include RE] [--limit N]   load documents into the store
  ingest-url URL                                         load a web page
  extract [--max-chunks N] [--workers N]                 NER + relation extraction (cached)
  resolve [--no-llm]                                     entity resolution
  summarize [--top N]                                    hub entity profiles
  build   (= extract + resolve + summarize)
  stats | search Q | entity NAME | neighbors NAME | paths A B | match PATTERN
  matrix [SRC_TYPE TGT_TYPE] | contradictions | communities
  ask "QUESTION"                                         Graph-RAG answer
  viz [--center NAME] [--out FILE]                       interactive HTML
  export [--format graphml|json|cypher] [--out FILE]
  serve [--port 8765]                                    REST API
  mcp                                                    MCP server (stdio)
"""
from __future__ import annotations

import argparse
import json
import sys

from . import config, pipeline, qa


def _p(x):
    print(json.dumps(x, ensure_ascii=False, indent=1, default=list))


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="kg", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=None)
    ap.add_argument("--provider", default=None, help="claude-cli | anthropic | ollama | openai")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("ingest"); s.add_argument("paths", nargs="*"); s.add_argument("--library", action="store_true")
    s.add_argument("--include"); s.add_argument("--exclude"); s.add_argument("--limit", type=int)
    s.add_argument("--topic", action="store_true", help="use the topic filename filter from config")
    s.add_argument("--chunk-size", type=int, default=6000); s.add_argument("--max-pages", type=int)
    s = sub.add_parser("ingest-url"); s.add_argument("url")
    s = sub.add_parser("dedup"); s.add_argument("--threshold", type=float, default=0.5)
    for name in ("extract", "build"):
        s = sub.add_parser(name); s.add_argument("--max-chunks", type=int, default=None)
        s.add_argument("--workers", type=int, default=4)
        s.add_argument("--title", help="regex: only documents whose title matches")
        s.add_argument("--exclude-title", help="regex: skip documents whose title matches")
        if name == "build":
            s.add_argument("--top", type=int, default=15); s.add_argument("--no-llm", action="store_true")
    s = sub.add_parser("resolve"); s.add_argument("--no-llm", action="store_true")
    s = sub.add_parser("summarize"); s.add_argument("--top", type=int, default=15); s.add_argument("names", nargs="*")
    sub.add_parser("stats")
    s = sub.add_parser("search"); s.add_argument("q"); s.add_argument("--type")
    s = sub.add_parser("entity"); s.add_argument("name")
    s = sub.add_parser("neighbors"); s.add_argument("name"); s.add_argument("--depth", type=int, default=1)
    s.add_argument("--predicates"); s.add_argument("--types"); s.add_argument("--min-weight", type=int, default=1)
    s = sub.add_parser("paths"); s.add_argument("a"); s.add_argument("b"); s.add_argument("--max-len", type=int, default=4)
    s = sub.add_parser("match"); s.add_argument("pattern"); s.add_argument("--limit", type=int, default=30)
    s.add_argument("--min-weight", type=int, default=1)
    s = sub.add_parser("matrix"); s.add_argument("src", nargs="?", default="INTERVENTION"); s.add_argument("tgt", nargs="?", default="BIOMARKER")
    sub.add_parser("contradictions"); sub.add_parser("communities")
    s = sub.add_parser("ask"); s.add_argument("question"); s.add_argument("--hops", type=int, default=2)
    s = sub.add_parser("viz"); s.add_argument("--center"); s.add_argument("--depth", type=int, default=2)
    s.add_argument("--max-nodes", type=int, default=600); s.add_argument("--out", default=str(config.OUT_DIR / "graph.html"))
    s = sub.add_parser("export"); s.add_argument("--format", default="graphml", choices=["graphml", "json", "cypher"])
    s.add_argument("--out")
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8765); s.add_argument("--host", default="127.0.0.1")
    sub.add_parser("mcp")
    a = ap.parse_args(argv)

    if a.cmd == "mcp":
        from .mcp_server import mcp
        return mcp.run()
    if a.cmd == "serve":
        import uvicorn
        return uvicorn.run("kgengine.api:app", host=a.host, port=a.port)

    store, kg = config.open_kg(a.db)
    prov = lambda: config.provider(a.provider)

    if a.cmd == "ingest":
        roots = list(a.paths) + (config.LIBRARY_ROOTS if a.library else [])
        inc = a.include or (config.TOPIC_INCLUDE if a.topic else None)
        _p(pipeline.ingest_paths(store, roots, inc, a.exclude, a.limit, a.chunk_size, a.max_pages))
        from .dedup import mark_duplicates
        _p(mark_duplicates(store))
    elif a.cmd == "dedup":
        from .dedup import mark_duplicates
        _p(mark_duplicates(store, a.threshold))
    elif a.cmd == "ingest-url":
        _p(pipeline.ingest_url(store, a.url))
    elif a.cmd in ("extract", "build"):
        p = prov()
        ids = None
        if a.title or a.exclude_title:
            import re
            inc = re.compile(a.title or ".", re.I)
            exc = re.compile(a.exclude_title, re.I) if a.exclude_title else None
            ids = [r["id"] for r in store.q("SELECT id, title FROM documents")
                   if inc.search(r["title"]) and not (exc and exc.search(r["title"]))]
            print(f"selected {len(ids)} documents", flush=True)
        _p(pipeline.extract(store, p, a.max_chunks, a.workers, doc_ids=None if ids is None else (ids or [-1])))
        if a.cmd == "build":
            _p(pipeline.resolve(store, p, use_llm=not a.no_llm))
            kg.reload()
            pipeline.summarize(store, p, kg, top=a.top)
            kg.reload()
            _p({"llm_calls": p.calls, "cost_usd": round(p.cost_usd, 4)})
    elif a.cmd == "resolve":
        _p(pipeline.resolve(store, None if a.no_llm else prov(), use_llm=not a.no_llm))
    elif a.cmd == "summarize":
        pipeline.summarize(store, prov(), kg, top=a.top, names=a.names or None)
    elif a.cmd == "stats":
        _p(kg.stats())
    elif a.cmd == "search":
        _p(kg.search(a.q, type=a.type))
    elif a.cmd == "entity":
        _p(kg.entity(a.name))
    elif a.cmd == "neighbors":
        _p(kg.neighbors(a.name, a.depth, a.predicates.split(",") if a.predicates else None,
                        a.types.split(",") if a.types else None, a.min_weight))
    elif a.cmd == "paths":
        _p(kg.paths(a.a, a.b, a.max_len))
    elif a.cmd == "match":
        _p(kg.match(a.pattern, a.limit, a.min_weight))
    elif a.cmd == "matrix":
        _p(kg.evidence_matrix(a.src, a.tgt))
    elif a.cmd == "contradictions":
        _p(kg.contradictions())
    elif a.cmd == "communities":
        _p(kg.communities())
    elif a.cmd == "ask":
        _p(qa.ask(kg, prov(), a.question, a.hops))
    elif a.cmd == "viz":
        from .viz import export_html
        print(export_html(kg, a.out, "Physical Activity × Neurocognitive Aging KG",
                          max_nodes=a.max_nodes, center=a.center, depth=a.depth))
    elif a.cmd == "export":
        from .export import export
        print(export(kg, a.format, a.out))


if __name__ == "__main__":
    main()
