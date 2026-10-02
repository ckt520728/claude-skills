"""離線完整示範：high 規劃、stub Jev 分配、low 寫入、獨立讀回驗收。"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jev import (Model, Registry, PlannerResult, WorkerResult, TaskSpec,
                 register_provider, plan_phase, execute_phase)


@register_provider("two_phase_demo")
def demo_decisions(state, questions, model, timeout):
    answers = {}
    for key, spec in questions.items():
        if key.startswith("tier_"):
            choice = "low"
        elif key.startswith("data_"):
            choice = "public"
        elif key == "capability":
            choice = "local_write"
        else:
            answers[key] = {"type": "noul", "noul": 1.0}
            continue
        answers[key] = {"type": "choice", "choice": choice, "confidence": 1.0,
                        "probabilities": {k: float(k == choice) for k in spec.criteria}}
    return {"model": "SYNTHETIC-stub", "answers": answers,
            "usage": {"input_tokens": 0, "output_tokens": 0}}


def main():
    registry = Registry(
        models=[Model(key=tier, display="SYNTHETIC " + tier, platform="demo", tier=tier,
                      api_id="stub-" + tier, api_id_verified=True, notes="僅供離線測試")
                for tier in ("high", "medium", "low")],
        platforms={"demo": {"data_classes_allowed": ["public"]}},
    )
    with tempfile.TemporaryDirectory(prefix="jev-two-phase-") as directory:
        artifact = Path(directory) / "result.txt"

        def planner(request):
            assert request.model.tier == "high"
            return PlannerResult(request.model.key, (TaskSpec(
                task_id="write", objective="撰寫一句繁體中文完成訊息", inputs=(),
                outputs=(str(artifact),), acceptance=("存在且包含第二階段",),
                capabilities=("local_write",)),), 0, 0)

        plan = plan_phase("建立一份示範文件", planner, registry=registry,
                          data_class="public", provider="two_phase_demo")
        assert plan.status == "ready" and not artifact.exists()
        print("Phase 1：high 只回傳規格；成品尚不存在。")

        def tool_runner(tool, arguments):
            assert tool == "Write" and arguments["file_path"] == str(artifact)
            artifact.write_text(arguments["content"], encoding="utf-8")

        def executor(request, context):
            assert request.model.tier == "low"
            context.call("Write", {"file_path": str(artifact), "content": "第二階段已完成。"})
            return WorkerResult(request.model.key, (str(artifact),), 0, 0)

        report = execute_phase(
            plan, executor, registry=registry, tool_runner=tool_runner,
            verifier=lambda request, result: artifact.read_text(encoding="utf-8") == "第二階段已完成。",
            provider="two_phase_demo", cwd=directory,
        )
        assert report.status == "completed"
        print("Phase 2：low 實際寫入檔案，獨立讀回驗收通過。")
        print(json.dumps({"status": report.status, "completion_rate": report.completion_rate,
                          "measurement": "SYNTHETIC：未呼叫真實模型，零用量不可用來推估節省率"},
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
