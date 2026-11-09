"""Run the same Jev research graph as the dashboard button from a terminal, a scheduler or another agent."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    from knowledge_agent import llm
    from knowledge_agent.config import BASE_DIR, CONFIG

    refs = llm.all_model_refs()
    parser = argparse.ArgumentParser(description="Autoresearch RSI: Jev planner -> executor swarm -> auditor, deliverables, knowledge base")
    parser.add_argument("--topic", default=CONFIG.get("default_topic", ""))
    parser.add_argument("--loops", "--passes", dest="loops", type=int, default=CONFIG.get("default_loops", 2), choices=[1, 2, 3])
    parser.add_argument("--planner", default="", choices=[""] + refs)
    parser.add_argument("--executor", default="", choices=[""] + refs)
    parser.add_argument("--auditor", default="", choices=[""] + refs)
    parser.add_argument("--budget", type=float, default=CONFIG.get("default_budget_usd", 5), help="Hard spending limit in USD")
    parser.add_argument("--feedback", default="")
    parser.add_argument("--no-robin", action="store_true", help="Turn the Robin layer off (reproduces the plain Jev graph)")
    parser.add_argument("--candidates", type=int, default=None, help="Hypotheses entering the BTL tournament (3-10)")
    parser.add_argument("--trajectories", type=int, default=None, help="Parallel Falcon trajectories: 1 (off), 3, 5 or 8")
    parser.add_argument("--consensus", type=float, default=None, help="Share of trajectories that must agree (0.5-0.75)")
    parser.add_argument("--check", action="store_true", help="Check dependencies, providers and the knowledge base folder; spends nothing")
    parser.add_argument("--models", metavar="PROVIDER", help="List model ids reported by an OpenAI-compatible provider (openai, gemini)")
    parser.add_argument("--kb-fitness", action="store_true", help="Measure the knowledge base and exit")
    parser.add_argument("--kb-improve", action="store_true", help="Propose, test and promote/reject knowledge-base improvements")
    args = parser.parse_args()

    if args.check:
        import anyio, flask, markdown, pptx, pypdf, requests  # noqa: F401,E401
        from knowledge_agent import kb
        from knowledge_agent.jev import default_roles

        print("Dependencies OK.")
        for row in llm.provider_status():
            print(f"  provider {row['name']:<8} {'available' if row['available'] else 'UNAVAILABLE':<12} {row['detail']}")
        print(f"  default roles: {json.dumps(default_roles())}")
        root = kb.kb_root()
        print(f"  knowledge base: {root} ({'exists' if root.exists() else 'will be created on the first run'}; parent {'exists' if root.parent.exists() else 'MISSING'})")
        return 0
    if args.models:
        try:
            for model_id in llm.list_models(args.models):
                print(model_id)
        except llm.ProviderError as e:
            print(f"Cannot list models: {e}")
            return 1
        return 0
    if args.kb_fitness or args.kb_improve:
        from knowledge_agent import kb, kb_rsi
        from knowledge_agent.config import OUTPUT_DIR

        root = kb.kb_root()
        if not root.exists():
            print(f"No knowledge base yet at {root}. Run research first.")
            return 1
        if args.kb_improve:
            ledger = BASE_DIR / ".rsi" / "kb_ledger.jsonl"
            ledger.parent.mkdir(exist_ok=True)
            queue = CONFIG.get("knowledge_base", {}).get("queue_md")
            for d in kb_rsi.improve(root, ledger, Path(queue) if queue else None):
                print(f"{d['decision']:<8} {d['kind']:<15} {d['target']}  Δscore={d['delta_score']:+.4f}  {d['reason']}")
            kb.write_graph(root, OUTPUT_DIR / "kb_graph.json")
        print(json.dumps({k: v for k, v in kb_rsi.fitness(root).items() if k != "details"}, ensure_ascii=False, indent=1))
        return 0
    if len(args.topic.strip()) < 3:
        parser.error("--topic is required")

    import anyio

    from knowledge_agent.app import robin_settings
    from knowledge_agent.jev import JevRequest, JevRun

    wanted = {k: v for k, v in (("candidates", args.candidates), ("trajectories", args.trajectories), ("consensus", args.consensus)) if v is not None}
    if args.no_robin:
        wanted["robin"] = False
    settings, problem = robin_settings(wanted)
    if problem:
        parser.error(problem)
    request = JevRequest(args.topic, args.loops, args.executor, args.budget, args.feedback, args.planner, args.executor, args.auditor, **settings)
    run = JevRun(request, on_log=print)
    report = anyio.run(run.execute)
    print(json.dumps({k: report[k] for k in ("run_id", "status", "spent_usd", "evidence_count", "citation_problems", "roles")}, ensure_ascii=False, indent=1))
    print(f"Files: {run.dir}")
    return 0 if report["status"] == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())
