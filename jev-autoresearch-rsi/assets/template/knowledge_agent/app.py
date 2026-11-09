"""
Local web server: serves dashboard.html and runs the RSI pipeline in the background.
Runs can spend money, so they are accepted only from the dashboard's own origin on this machine.
"""

from __future__ import annotations

import re
import threading
from pathlib import Path
from urllib.parse import urlparse

import anyio
from flask import Flask, abort, jsonify, request, send_from_directory

from .checks import phi_hits
from .config import BASE_DIR, CONFIG, OUTPUT_DIR, RUNS_DIR
from . import llm
from .jev import JevRequest, JevRun, default_roles
from .pipeline import list_runs

LOCAL_HOSTS = {"127.0.0.1", "localhost"}
RUN_ID = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")
MAX_BUDGET = 30


def _parse_request(data):
    """Validate the form. Returns (JevRequest, None) or (None, error message)."""
    if not isinstance(data, dict):
        return None, "Expected a JSON object."
    topic = str(data.get("topic", "")).strip()
    feedback = str(data.get("feedback", "")).strip()
    if not 3 <= len(topic) <= 300:
        return None, "The research topic must be 3 to 300 characters."
    if len(feedback) > 4000:
        return None, "Feedback must be 4000 characters or fewer."
    if phi_hits(f"{topic} {feedback}"):
        return None, "The topic or feedback contains a known identifier. Remove it and try again."
    try:
        loops = int(data.get("loops", data.get("passes", CONFIG.get("default_loops", 2))))
        budget = float(data.get("budget_usd", 5))
    except (TypeError, ValueError):
        return None, "Loops and budget must be numbers."
    if not 1 <= loops <= 3:
        return None, "Loops must be 1, 2 or 3."
    if not 0.1 <= budget <= MAX_BUDGET:
        return None, f"The budget must be between $0.10 and ${MAX_BUDGET}."
    known = set(llm.all_model_refs())
    roles = default_roles()
    chosen = {}
    for role in ("planner", "executor", "auditor"):
        value = str(data.get(role) or (data.get("model") if role == "executor" else "") or roles[role])
        if value not in known:
            return None, f"Unknown {role} model."
        chosen[role] = value
    settings, problem = robin_settings(data)
    if problem:
        return None, problem
    return JevRequest(topic, loops, chosen["executor"], budget, feedback, chosen["planner"], chosen["executor"], chosen["auditor"], **settings), None


def robin_defaults():
    cfg = CONFIG.get("robin", {})
    return {"robin": bool(cfg.get("enabled", True)), "candidates": int(cfg.get("candidates", 6)),
            "trajectories": int(cfg.get("trajectories", 1)), "consensus": float(cfg.get("consensus", 0.5))}


def robin_settings(data):
    """Robin layer settings (ADR 0002). Each one changes the graph; out-of-range values are refused, not clamped."""
    from . import robin
    d = robin_defaults()
    try:
        on = data.get("robin", d["robin"])
        if not isinstance(on, bool):
            return None, "Robin must be true or false."
        candidates = int(data.get("candidates", d["candidates"]))
        trajectories = int(data.get("trajectories", d["trajectories"]))
        consensus = float(data.get("consensus", d["consensus"]))
    except (TypeError, ValueError):
        return None, "Robin settings must be numbers."
    if not robin.MIN_CANDIDATES <= candidates <= 10:
        return None, f"Hypothesis candidates must be {robin.MIN_CANDIDATES} to 10."
    if trajectories not in robin.TRAJECTORY_CHOICES:
        return None, f"Trajectories must be one of {', '.join(map(str, robin.TRAJECTORY_CHOICES))}."
    low, high = robin.CONSENSUS_RANGE
    if not low <= consensus <= high:
        return None, f"The consensus threshold must be between {low} and {high}."
    return {"robin": on, "candidates": candidates, "trajectories": trajectories, "consensus": consensus}, None


def create_app() -> Flask:
    app = Flask(__name__)
    state = {"run": None, "thread": None}
    lock = threading.Lock()

    def active_run():
        thread = state["thread"]
        return state["run"] if thread is not None and thread.is_alive() else None

    @app.before_request
    def require_local_host():
        # Blocks DNS rebinding: a remote page cannot reach this server under another name.
        if urlparse(f"//{request.host}").hostname not in LOCAL_HOSTS:
            abort(403)

    def require_same_origin():
        # Blocks other websites from starting paid runs through the user's browser.
        origin = request.headers.get("Origin", "")
        if not origin or urlparse(origin).netloc != request.host:
            abort(403)
        if not request.is_json:
            abort(415)

    @app.route("/")
    def index():
        return send_from_directory(BASE_DIR, "dashboard.html", max_age=0)

    @app.route("/outputs/<path:filename>")
    def outputs(filename):
        return send_from_directory(OUTPUT_DIR, filename, max_age=0)

    @app.route("/api/health")
    def health():
        response = jsonify({"status": "ok", "port": request.host.rsplit(":", 1)[-1]})
        # Read-only, so a dashboard opened as a local file (origin "null") can detect the server.
        response.headers["Access-Control-Allow-Origin"] = "null"
        return response

    @app.route("/api/config")
    def config():
        provider = CONFIG["provider"]
        roles = default_roles()
        return jsonify({
            "title": CONFIG.get("title", "RSI Knowledge Dashboard"), "owner": CONFIG.get("owner", ""), "language": CONFIG.get("language", "en"),
            "default_topic": CONFIG.get("default_topic", ""), "models": [m for m in llm.all_model_refs() if ":" in m] or llm.all_model_refs(), "default_model": roles["executor"],
            "max_budget": MAX_BUDGET, "default_budget": CONFIG.get("default_budget_usd", 5), "default_loops": CONFIG.get("default_loops", 2),
            "tiers": {"high": llm.tier_models("high"), "medium": llm.tier_models("medium")}, "roles": roles,
            "default_planner": roles["planner"], "default_executor": roles["executor"], "default_auditor": roles["auditor"],
            "providers": [{k: v for k, v in row.items() if k != "models"} for row in llm.provider_status()],
            "kb_root": str(_kb().kb_root()),
            "robin": {**robin_defaults(), "trajectory_choices": list(_robin().TRAJECTORY_CHOICES), "consensus_range": list(_robin().CONSENSUS_RANGE),
                      "min_candidates": _robin().MIN_CANDIDATES},
        })

    @app.route("/api/research", methods=["POST"])
    def start_research():
        require_same_origin()
        parsed, problem = _parse_request(request.get_json(silent=True))
        if problem:
            return jsonify({"status": "error", "message": problem}), 400
        with lock:
            if active_run():
                return jsonify({"status": "error", "message": "A run is already in progress.", "run_id": active_run().run_id}), 409
            run = JevRun(parsed)
            thread = threading.Thread(target=lambda: anyio.run(run.execute), daemon=True, name=f"rsi-{run.run_id}")
            state.update(run=run, thread=thread)
            thread.start()
        return jsonify({"status": "started", "run_id": run.run_id}), 202

    @app.route("/api/runs")
    def runs():
        return jsonify({"runs": list_runs(), "active": active_run().run_id if active_run() else None})

    @app.route("/api/runs/<run_id>")
    def run_detail(run_id):
        if not RUN_ID.match(run_id):
            abort(404)
        run = state["run"]
        if run is not None and run.run_id == run_id:
            return jsonify(run.report())
        report = RUNS_DIR / run_id / "run_report.json"
        if not report.exists():
            abort(404)
        return app.response_class(report.read_text(encoding="utf-8"), mimetype="application/json")

    @app.route("/api/runs/<run_id>/cancel", methods=["POST"])
    def cancel(run_id):
        require_same_origin()
        run = active_run()
        if run is None or run.run_id != run_id:
            return jsonify({"status": "error", "message": "That run is not in progress."}), 409
        run.cancel_event.set()
        return jsonify({"status": "cancelling"})

    # ------------------------------------------------------------ knowledge base

    @app.route("/api/kb/graph")
    def kb_graph():
        root = _kb().kb_root()
        return jsonify(_kb().build_graph(root) if root.exists() else {"nodes": [], "edges": []})

    @app.route("/api/kb/pages")
    def kb_pages():
        root = _kb().kb_root()
        query = str(request.args.get("q", ""))[:200]
        return jsonify({"pages": _kb().list_pages(root, query) if root.exists() else []})

    @app.route("/api/kb/page")
    def kb_page():
        try:
            return jsonify(_kb().read_page(_kb().kb_root(), str(request.args.get("path", ""))))
        except (ValueError, FileNotFoundError) as e:
            return jsonify({"status": "error", "message": str(e)[:200]}), 400

    @app.route("/api/kb/fitness")
    def kb_fitness():
        root = _kb().kb_root()
        return jsonify(_rsi().fitness(root) if root.exists() else {"pages": 0, "score": 0, "details": {}})

    @app.route("/api/kb/gaps")
    def kb_gaps():
        root = _kb().kb_root()
        return jsonify({"gaps": _kb().open_gaps(root) if root.exists() else []})

    @app.route("/api/kb/ledger")
    def kb_ledger():
        path = KB_LEDGER
        return jsonify({"entries": _rsi().ledger_entries(path) if path.exists() else [], "chain_ok": _rsi().verify_ledger(path) if path.exists() else True})

    @app.route("/api/kb/improve", methods=["POST"])
    def kb_improve():
        require_same_origin()
        if not lock.acquire(blocking=False):
            return jsonify({"status": "error", "message": "Busy; try again."}), 409
        try:
            if active_run():
                return jsonify({"status": "error", "message": "Wait for the current run to finish."}), 409
            return _improve()
        finally:
            lock.release()

    def _improve():
        root = _kb().kb_root()
        if not root.exists():
            return jsonify({"status": "error", "message": "The knowledge base folder does not exist yet. Run research first."}), 409
        KB_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        queue = CONFIG.get("knowledge_base", {}).get("queue_md")
        decisions = _rsi().improve(root, KB_LEDGER, Path(queue) if queue else None)
        _kb().write_graph(root, OUTPUT_DIR / "kb_graph.json")
        return jsonify({"decisions": decisions, "fitness": _rsi().fitness(root)})

    return app


KB_LEDGER = BASE_DIR / ".rsi" / "kb_ledger.jsonl"


def _kb():
    from . import kb
    return kb


def _rsi():
    from . import kb_rsi
    return kb_rsi


def _robin():
    from . import robin
    return robin
