"""
Local web server: serves dashboard.html and runs the RSI pipeline in the background.
Runs can spend money, so they are accepted only from the dashboard's own origin on this machine.
"""

from __future__ import annotations

import re
import threading
from urllib.parse import urlparse

import anyio
from flask import Flask, abort, jsonify, request, send_from_directory

from .checks import phi_hits
from .config import BASE_DIR, CONFIG, OUTPUT_DIR, RUNS_DIR
from .pipeline import ResearchRequest, ResearchRun, list_runs

LOCAL_HOSTS = {"127.0.0.1", "localhost"}
RUN_ID = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")
MAX_BUDGET = 30


def _parse_request(data):
    """Validate the form. Returns (ResearchRequest, None) or (None, error message)."""
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
        passes = int(data.get("passes", 2))
        budget = float(data.get("budget_usd", 5))
    except (TypeError, ValueError):
        return None, "Passes and budget must be numbers."
    if not 1 <= passes <= 3:
        return None, "RSI passes must be 1, 2 or 3."
    if not 0.1 <= budget <= MAX_BUDGET:
        return None, f"The budget must be between $0.10 and ${MAX_BUDGET}."
    provider = CONFIG["provider"]
    model = data.get("model", provider["default_model"])
    if model not in provider["models"]:
        return None, "Unknown model."
    return ResearchRequest(topic, passes, model, budget, feedback), None


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
        return jsonify({
            "title": CONFIG.get("title", "RSI Knowledge Dashboard"), "owner": CONFIG.get("owner", ""), "language": CONFIG.get("language", "en"),
            "default_topic": CONFIG.get("default_topic", ""), "models": provider["models"], "default_model": provider["default_model"],
            "max_budget": MAX_BUDGET, "default_budget": CONFIG.get("default_budget_usd", 5),
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
            run = ResearchRun(parsed)
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

    return app
