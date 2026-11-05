"""Run the same pipeline as the dashboard button from a terminal, a scheduler or another agent."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    from knowledge_agent.config import CONFIG

    parser = argparse.ArgumentParser(description="RSI research loop and deliverables")
    parser.add_argument("--topic", default=CONFIG.get("default_topic", ""))
    parser.add_argument("--passes", type=int, default=2, choices=[1, 2, 3])
    parser.add_argument("--model", default=CONFIG["provider"]["default_model"], choices=CONFIG["provider"]["models"])
    parser.add_argument("--budget", type=float, default=CONFIG.get("default_budget_usd", 5), help="Hard spending limit in USD")
    parser.add_argument("--feedback", default="")
    parser.add_argument("--check", action="store_true", help="Check dependencies and exit, spending nothing")
    args = parser.parse_args()

    if args.check:
        import anyio, flask, markdown, pptx, pypdf, requests  # noqa: F401,E401

        print("Dependencies OK.")
        return 0
    if len(args.topic.strip()) < 3:
        parser.error("--topic is required")

    import anyio

    from knowledge_agent.pipeline import ResearchRequest, ResearchRun

    run = ResearchRun(ResearchRequest(args.topic, args.passes, args.model, args.budget, args.feedback), on_log=print)
    report = anyio.run(run.execute)
    print(json.dumps({k: report[k] for k in ("run_id", "status", "spent_usd", "evidence_count", "citation_problems")}, ensure_ascii=False, indent=1))
    print(f"Files: {run.dir}")
    return 0 if report["status"] == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())
