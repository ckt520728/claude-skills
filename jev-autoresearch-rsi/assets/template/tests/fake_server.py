"""
TEST FIXTURE ONLY. Never used by the real app.

Serves app/dashboard.html and returns canned, contract-shaped JSON (docs/contracts.md section D) on
127.0.0.1:8091 so the dashboard UI can be tested without models, spending or a real knowledge base.
Nothing here is real research data.

    python tests/fake_server.py
"""

import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOST, PORT = "127.0.0.1", 8091
DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard.html"
OLD_RUN, NEW_RUN = "20261101-090000-aaaaaa", "20261108-120000-feed01"

PAGES = {
    "主題/rsi-overview.md": {
        "path": "主題/rsi-overview.md", "title": "RSI overview", "type": "topic", "updated": "2026-11-08",
        "frontmatter": {"title": "RSI overview", "date": "2026-11-08", "tags": ["rsi", "fixture"], "confidence": "medium"},
        "body": "# RSI overview\n\nSummary of the fixture topic <script>alert(1)</script>.\n\n## Key concepts\n\n- [[概念/recursive-self-improvement]]\n- [[概念/missing-page|a broken link]]\n\nSee [docs](https://example.org/docs).\n\n```\ncode <b>block</b>\n```\n",
    },
    "概念/recursive-self-improvement.md": {
        "path": "概念/recursive-self-improvement.md", "title": "Recursive self-improvement", "type": "concept", "updated": "2026-11-08",
        "frontmatter": {"title": "Recursive self-improvement", "run_ids": ["20261101-090000-aaaaaa"]},
        "body": "# Recursive self-improvement\n\nA system that improves its own improver. **Claim**: gated promotion keeps it honest ([[來源/doi-10-1000-xyz]]).\n",
    },
    "來源/doi-10-1000-xyz.md": {
        "path": "來源/doi-10-1000-xyz.md", "title": "Lee et al. 2024", "type": "source", "updated": "2026-11-01",
        "frontmatter": {"title": "Lee et al. 2024"}, "body": "# Lee et al. 2024\n\nFixture citation.\n",
    },
}
GRAPH = {
    "nodes": [
        {"id": "主題/rsi-overview", "label": "RSI overview", "type": "topic", "degree": 2},
        {"id": "概念/recursive-self-improvement", "label": "Recursive self-improvement", "type": "concept", "degree": 2},
        {"id": "來源/doi-10-1000-xyz", "label": "Lee et al. 2024", "type": "source", "degree": 1},
        {"id": "缺口/gaps", "label": "Open gaps", "type": "gap", "degree": 0},
    ],
    "edges": [
        {"source": "主題/rsi-overview", "target": "概念/recursive-self-improvement"},
        {"source": "概念/recursive-self-improvement", "target": "來源/doi-10-1000-xyz"},
    ],
}
STATE = {"active": None, "cancelled": False, "ledger": [], "score": 0.82, "posts": []}
LOCK = threading.Lock()


def graph(statuses):
    ids = ["plan", "research", "write", "audit"]
    labels = ["Plan", "Research sources", "Write deliverables", "Audit loop 1"]
    tiers = ["high", "medium", "medium", "high"]
    return {
        "nodes": [{"id": i, "label": l, "tier": t, "status": s, "attempts": 0 if s == "pending" else 1, "detail": f"{l} fixture"} for i, l, t, s in zip(ids, labels, tiers, statuses)],
        "edges": [{"source": "plan", "target": "research"}, {"source": "plan", "target": "write"}, {"source": "research", "target": "write"}, {"source": "write", "target": "audit"}],
    }


def fitness():
    return {"pages": 3, "broken_links": 1, "orphans": 0, "unsourced_claims": 0, "open_gaps": 2, "concepts": 1, "single_source_concepts": 1, "score": round(STATE["score"], 3), "details": {}}


def old_report():
    return {
        "run_id": OLD_RUN, "status": "COMPLETED", "stage": "done", "request": {"topic": "Fixture topic: past run", "loops": 2, "budget_usd": 5, "planner": "opus", "executor": "sonnet", "auditor": "opus"},
        "spent_usd": 1.2345, "elapsed_seconds": 321, "sources": [{"name": "PubMed", "state": "LIVE", "items": 12, "detail": ""}, {"name": "arXiv", "state": "FALLBACK", "items": 3, "detail": "fixture fallback"}, {"name": "NotebookLM", "state": "UNAVAILABLE", "items": 0, "detail": "not signed in"}],
        "evidence_count": 15, "dropped_for_privacy": 0, "passes": [1, 2], "citation_problems": [], "promotions": [], "error": "", "log": ["fixture: started", "fixture: finished"],
        "deliverables": [{"kind": "paper", "files": {"html": "paper.html", "md": "paper.md"}, "verified": True}, {"kind": "deck", "files": {"pptx": "deck.pptx"}, "verified": False}],
        "graph": graph(["passed", "passed", "failed", "skipped"]),
        "audits": [{"loop": 1, "verdict": "REVISE", "score": 0.61, "findings": ["Claim 3 lacks a citation", "Figure 2 value mismatch"]}, {"loop": 2, "verdict": "PASS", "score": 0.91, "findings": []}],
        "kb": {"created": ["主題/rsi-overview.md"], "updated": ["概念/recursive-self-improvement.md"], "fitness_before": {"score": 0.7, "pages": 2}, "fitness_after": {"score": 0.82, "pages": 3}, "decisions": ["PROMOTE repair_link x"]},
    }


def new_report():
    cancelled = STATE["cancelled"]
    report = old_report()
    report.update(run_id=NEW_RUN, status="CANCELLED" if cancelled else "RUNNING", stage="cancelled" if cancelled else "research", deliverables=[], audits=[], kb=None, spent_usd=0.1, elapsed_seconds=4, log=["fixture: new run started"] + (["fixture: cancelled"] if cancelled else []))
    report["request"] = dict(STATE["posts"][-1]) if STATE["posts"] else report["request"]
    report["graph"] = graph(["passed", "skipped" if cancelled else "running", "skipped" if cancelled else "pending", "skipped" if cancelled else "pending"])
    return report


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, code, payload, ctype="application/json; charset=utf-8"):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return None

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        p = url.path
        with LOCK:
            if p == "/":
                return self.send(200, DASHBOARD.read_bytes(), "text/html; charset=utf-8")
            if p.startswith("/outputs/"):
                return self.send(200, b"fixture file", "text/plain")
            if p == "/api/health":
                return self.send(200, {"status": "ok", "port": str(PORT)})
            if p == "/api/config":
                return self.send(200, {
                    "title": "Autoresearch RSI Knowledge Dashboard (fixture)", "owner": "test fixture", "language": "en", "default_topic": "Recursive self-improvement in research agents",
                    "models": ["opus", "sonnet"], "default_model": "sonnet", "max_budget": 30, "default_budget": 5, "default_loops": 2,
                    "tiers": {"high": ["claude-opus-fixture", "gpt-high-fixture"], "medium": ["claude-sonnet-fixture", "gpt-medium-fixture"]},
                    "providers": [{"name": "claude-sdk", "type": "claude", "available": True, "detail": "fixture ok"}, {"name": "openai-compat", "type": "openai", "available": False, "detail": "no key (fixture)"}],
                    "kb_root": "fixture-kb",
                })
            if p == "/api/runs":
                runs = ([new_report()] if STATE["active"] or STATE["posts"] else []) + [old_report()]
                return self.send(200, {"runs": runs, "active": NEW_RUN if STATE["active"] else None})
            m = re.match(r"^/api/runs/([\w-]+)$", p)
            if m:
                if m.group(1) == OLD_RUN:
                    return self.send(200, old_report())
                if m.group(1) == NEW_RUN and STATE["posts"]:
                    return self.send(200, new_report())
                return self.send(404, {"message": "not found"})
            if p == "/api/kb/graph":
                return self.send(200, GRAPH)
            if p == "/api/kb/pages":
                needle = (q.get("q") or [""])[0].casefold()
                rows = [{k: v[k] for k in ("path", "title", "type", "updated")} for v in PAGES.values() if needle in (v["title"] + v["body"]).casefold()]
                return self.send(200, rows)
            if p == "/api/kb/page":
                page = PAGES.get((q.get("path") or [""])[0])
                return self.send(200, page) if page else self.send(400, {"message": "bad path"})
            if p == "/api/kb/fitness":
                return self.send(200, fitness())
            if p == "/api/kb/gaps":
                return self.send(200, {"gaps": ["What is the failure rate of gated promotion?", "No registry trials found"]})
            if p == "/api/kb/ledger":
                return self.send(200, {"entries": list(reversed(STATE["ledger"])), "chain_ok": True})
        self.send(404, {"message": "not found"})

    def do_POST(self):
        p = urlparse(self.path).path
        data = self.body()
        with LOCK:
            if p == "/api/research":
                if not isinstance(data, dict):
                    return self.send(400, {"status": "error", "message": "Expected a JSON object."})
                if STATE["active"]:
                    return self.send(409, {"status": "error", "message": "A run is already in progress.", "run_id": NEW_RUN})
                STATE.update(active=True, cancelled=False)
                STATE["posts"].append(data)
                return self.send(202, {"status": "started", "run_id": NEW_RUN})
            if p == f"/api/runs/{NEW_RUN}/cancel":
                if not STATE["active"]:
                    return self.send(409, {"status": "error", "message": "That run is not in progress."})
                STATE.update(active=None, cancelled=True)
                return self.send(200, {"status": "cancelling"})
            if p == "/api/kb/improve":
                STATE["score"] = min(1.0, STATE["score"] + 0.05)
                decision = {"kind": "repair_link", "target": "主題/rsi-overview", "decision": "PROMOTE", "metric": "broken_links", "before": 1, "after": 0, "delta_score": 0.05, "reason": "fixture repair", "time": f"2026-11-08T12:00:{len(STATE['ledger']):02d}"}
                STATE["ledger"].append(decision)
                return self.send(200, {"decisions": [decision], "fitness": fitness()})
        self.send(404, {"message": "not found"})


def make_server():
    return ThreadingHTTPServer((HOST, PORT), Handler)


if __name__ == "__main__":
    print(f"TEST FIXTURE server (canned data) on http://{HOST}:{PORT}/", file=sys.stderr)
    make_server().serve_forever()
