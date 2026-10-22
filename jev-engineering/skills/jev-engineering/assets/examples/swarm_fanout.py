"""離線示範（v1.3）：雙大腦 → Handoff Wire 清單 → 扇出前審查 → canary → 有界並行。

情境模仿「分析 N 家公司」：high planner 拆成 N 份同模板任務加一份彙整，清單寫到磁碟，
執行端從清單讀回後並行執行。第二輪示範放大保護：規格含糊時 canary 失敗，同模板其餘
任務一份都不派發。全部使用 SYNTHETIC stub，沒有真實模型、費用或並行配額。
"""
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jev import (Limits, Model, PlannerResult, Registry, SwarmPolicy, TaskSpec, WorkerResult,
                 execute_swarm, load_manifest, plan_phase, register_provider, write_manifest)

N = 12


@register_provider("swarm_demo")
def demo_decisions(state, questions, model, timeout):
    answers = {}
    choices = {"tier": "low", "data": "public", "capability": "local_write"}
    for key, spec in questions.items():
        choice = choices.get(key.split("_")[0])
        if choice is None:                      # Noul：扇出前審查 clear_* 與 ToolGate 的 reversible
            answers[key] = {"type": "noul", "noul": 0.95 if key.startswith("clear_") else 1.0}
            continue
        answers[key] = {"type": "choice", "choice": choice, "confidence": 1.0,
                        "probabilities": {k: float(k == choice) for k in spec.criteria}}
    return {"model": "SYNTHETIC-stub", "answers": answers,
            "usage": {"input_tokens": 0, "output_tokens": 0}}


def main():
    registry = Registry(
        models=[Model(key=t, display="SYNTHETIC " + t, platform="demo", tier=t,
                      api_id="stub-" + t, api_id_verified=True, notes="僅供離線測試")
                for t in ("high", "medium", "low")],
        platforms={"demo": {"data_classes_allowed": ["public"]}},
    )
    limits = Limits(max_tasks=32, max_total_output_tokens=40000)

    with tempfile.TemporaryDirectory(prefix="jev-swarm-") as directory:
        root = Path(directory)

        def planner(request):
            tasks = [TaskSpec(task_id="co_%02d" % i, objective="整理公司 %d 的營收成 markdown 表格" % i,
                              inputs=(), outputs=(str(root / ("co_%02d.md" % i)),),
                              acceptance=("首列為 | 年度 | 營收 |",), capabilities=("local_write",),
                              max_output_tokens=256) for i in range(N)]
            tasks.append(TaskSpec(task_id="summary", objective="彙整所有表格", inputs=(),
                                  outputs=(str(root / "summary.md"),), acceptance=("每家公司一列",),
                                  capabilities=("local_write",),
                                  depends_on=tuple(t.task_id for t in tasks), max_output_tokens=512))
            return PlannerResult(request.model.key, tuple(tasks), 0, 0)

        plan = plan_phase("分析 %d 家公司" % N, planner, registry=registry, data_class="public",
                          provider="swarm_demo", limits=limits)
        assert plan.status == "ready", plan.reason
        manifest = root / "task_manifest.json"
        digest = write_manifest(plan, manifest, "demo-companies",
                                SwarmPolicy(concurrency=4, requests_per_minute=6000))
        print("Phase 1：high 只輸出交接清單 %s（sha256 %s…），尚無任何成品。"
              % (manifest.name, digest[:12]))

        # ---- Phase 2：執行端只看得到清單，不看 planner 對話 ----
        loaded, policy = load_manifest(manifest, registry)
        lock, active, peak, calls = threading.Lock(), [0], [0], []

        def tool_runner(tool, arguments):
            Path(arguments["file_path"]).write_text(arguments["content"], encoding="utf-8")

        def make_executor(header):
            def executor(request, context):
                with lock:
                    calls.append(request.task.task_id)
                    active[0] += 1
                    peak[0] = max(peak[0], active[0])
                time.sleep(0.02)
                rows = "\n".join("| %s | 1 |" % d for d in request.dependency_artifacts)
                context.call("Write", {"file_path": request.task.outputs[0],
                                       "content": header + "\n" + rows + "\n"})
                with lock:
                    active[0] -= 1
                return WorkerResult(request.model.key, request.task.outputs, 0, 0)
            return executor

        def verifier(request, result):
            text = Path(result.artifacts[0]).read_text(encoding="utf-8")
            if request.task.task_id == "summary":
                return text.count("\n") == N + 1
            return text.startswith("| 年度 | 營收 |")

        report = execute_swarm(loaded, make_executor("| 年度 | 營收 |"), verifier=verifier,
                               tool_runner=tool_runner, registry=registry, provider="swarm_demo",
                               policy=policy, cwd=directory)
        assert report.status == "completed", report.reason
        print("Phase 2：%d 份任務完成；canary=%s；同時執行峰值 %d（上限 %d）；分層 %d 層。"
              % (len(report.completed), ",".join(report.canaries), peak[0], policy.concurrency,
                 len(report.waves)))

        # ---- 放大保護：worker 對含糊格式各自猜測（這裡模擬為輸出錯的表頭） ----
        for f in root.glob("*.md"):
            f.unlink()
        calls.clear()
        bad = execute_swarm(loaded, make_executor("| Year | Revenue |"), verifier=verifier,
                            tool_runner=tool_runner, registry=registry, provider="swarm_demo",
                            policy=policy, cwd=directory)
        assert bad.status == "replan" and len(calls) == 1, (bad.status, calls)
        print("放大保護：canary 未通過驗收 → 只花了 1 份 worker，保留 %d 份、阻擋 %d 份，退回 Phase 1。"
              % (len(bad.held), len(bad.blocked)))
        print(json.dumps({"measurement": "SYNTHETIC：未呼叫真實模型；並行峰值與耗時不代表任何供應商的實際配額"},
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
