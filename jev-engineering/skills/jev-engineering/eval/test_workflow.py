"""兩階段行為測試：stub 決策、隔離成品、不呼叫付費模型。"""
import dataclasses
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "assets"))

from jev import Model, Registry, register_provider
from jev.workflow import (
    Limits, TaskSpec, PlannerResult, WorkerResult, WorkflowStop,
    plan_phase, execute_phase, ROUTE_CONFIDENCE,
)

SCRIPT = {}
CALLS = []


@register_provider("workflow_stub")
def stub(state, questions, model, timeout):
    CALLS.append(state)
    if SCRIPT.get("error"):
        raise RuntimeError("模擬決策服務中斷")
    answers = {}
    for key, spec in questions.items():
        if key.startswith("tier_"):
            pick, confidence = SCRIPT.get(key, ("low", 0.99))
        elif key.startswith("data_"):
            pick, confidence = SCRIPT.get(key, ("public", 0.99))
        elif key == "capability":
            pick, confidence = SCRIPT.get(key, ("local_write", 0.99))
        else:
            answers[key] = {"type": "noul", "noul": SCRIPT.get(key, 1.0)}
            continue
        answers[key] = {"type": "choice", "choice": pick, "confidence": confidence,
                        "probabilities": {k: float(k == pick) for k in spec.criteria}}
    return {"model": "stub", "answers": answers, "usage": {"input_tokens": 5, "output_tokens": 0}}


def registry():
    return Registry(models=[Model(key=t, display=t, platform="test", tier=t,
                                  api_id="stub-" + t, api_id_verified=True)
                            for t in ("high", "medium", "low")],
                    platforms={"test": {"data_classes_allowed": ["public", "internal"]}})


def task(key="a", **kw):
    values = dict(task_id=key, objective="依規格產生一份文字成品", inputs=("source.txt",),
                  outputs=(key + ".txt",), acceptance=("檔案存在且內容符合來源",),
                  capabilities=("local_write",), depends_on=())
    values.update(kw)
    return TaskSpec(**values)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        SCRIPT.clear()
        CALLS.clear()
        self.reg = registry()
        self.planner_calls = []
        self.worker_calls = []

    def plan(self, tasks=None, **kw):
        def planner(request):
            self.planner_calls.append(request)
            return PlannerResult(request.model.key, tuple(tasks or [task()]), 10, 20)
        return plan_phase("建立文件", planner, registry=self.reg, data_class="public",
                          provider="workflow_stub", **kw)

    def execute(self, plan, worker=None, **kw):
        def default_worker(request, context):
            self.worker_calls.append(request)
            return WorkerResult(request.model.key, request.task.outputs, 12, 22)
        return execute_phase(plan, worker or default_worker,
                             verifier=kw.pop("verifier", lambda req, result: True),
                             tool_runner=kw.pop("tool_runner", lambda name, args: None),
                             registry=self.reg, provider="workflow_stub", **kw)

    def test_phase_one_only_calls_high_planner_then_batched_decisions(self):
        p = self.plan([task(), task("b")])
        self.assertEqual(p.status, "ready")
        self.assertEqual(self.planner_calls[0].model.tier, "high")
        self.assertEqual(len(CALLS), 1)
        self.assertEqual(self.worker_calls, [])
        self.assertEqual([a.model.tier for a in p.allocations], ["low", "low"])

    def test_medium_allocation_and_minimal_dependency_handoff(self):
        SCRIPT["tier_1"] = ("medium", 0.99)
        p = self.plan([task(), task("b", depends_on=("a",)), task("c")])
        report = self.execute(p)
        self.assertEqual(report.status, "completed")
        self.assertEqual([r.model.tier for r in self.worker_calls], ["low", "medium", "low"])
        self.assertEqual(self.worker_calls[1].dependency_artifacts, {"a": ("a.txt",)})
        self.assertEqual(self.worker_calls[2].dependency_artifacts, {})
        self.assertFalse(hasattr(self.worker_calls[0], "plan"))
        self.assertEqual(report.completion_rate, 1.0)
        self.assertEqual(report.input_tokens, 51)  # planner 10 + Jev 5 + workers 36
        self.assertEqual(report.output_tokens, 86)

    def test_boundary_uncertainty_and_high_return_to_planning(self):
        for pick, confidence, expected in [("low", ROUTE_CONFIDENCE, "ready"),
                                           ("low", ROUTE_CONFIDENCE - .001, "replan"),
                                           ("high", .99, "replan"), ("other", 1.0, "replan")]:
            with self.subTest(pick=pick, confidence=confidence):
                SCRIPT["tier_0"] = (pick, confidence)
                p = self.plan()
                self.assertEqual(p.status, expected)
                if expected != "ready":
                    self.assertEqual(self.execute(p).status, expected)
                    self.assertFalse(self.worker_calls)

    def test_invalid_graph_and_budget_stop_before_decision_call(self):
        cases = [([task(), task()], Limits()),
                 ([task(depends_on=("missing",))], Limits()),
                 ([task(depends_on=("b",)), task("b", depends_on=("a",))], Limits()),
                 ([task(capabilities=("invalid",))], Limits()),
                 ([task()], Limits(max_tasks=0)),
                 ([task(max_output_tokens=99999)], Limits()),
                 ([task()], Limits(max_total_output_tokens=10))]
        for tasks, limits in cases:
            CALLS.clear()
            with self.subTest(tasks=tasks, limits=limits):
                self.assertEqual(self.plan(tasks, limits=limits).status, "ask")
                self.assertEqual(CALLS, [])

    def test_decision_failure_and_bad_data_never_execute(self):
        for key, value in [("error", True), ("data_0", ("secrets", 1.0)),
                           ("data_0", ("other", 1.0)), ("data_0", ("public", .2)),
                           ("data_0", ("customer_data", 1.0))]:
            SCRIPT.clear()
            SCRIPT[key] = value
            p = self.plan()
            self.assertEqual(p.status, "ask")
            self.assertEqual(self.execute(p).status, "ask")
        self.assertEqual(self.worker_calls, [])

    def test_secret_and_unavailable_planner_stop_before_any_model(self):
        for request, data in [("api_key=example", "public"), ("建立文件", "secrets")]:
            p = plan_phase(request, lambda req: self.fail("不應呼叫 planner"),
                           registry=self.reg, data_class=data, provider="workflow_stub")
            self.assertEqual(p.status, "ask")
        self.reg.models = [m for m in self.reg.models if m.tier != "high"]
        self.assertEqual(self.plan().status, "ask")
        self.assertEqual(CALLS, [])

    def test_missing_verified_worker_never_falls_back_to_high(self):
        self.reg.models = [dataclasses.replace(m, api_id=None) if m.tier == "low" else m
                           for m in self.reg.models]
        self.assertEqual(self.plan().status, "ask")
        self.assertEqual(self.worker_calls, [])

    def test_actual_execution_writes_only_during_phase_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "result.txt"
            p = self.plan([task(outputs=(str(output),))])
            self.assertFalse(output.exists())
            def run_tool(name, args):
                output.write_text(args["content"], encoding="utf-8")
            def worker(req, context):
                context.call("Write", {"file_path": str(output), "content": "第二階段的成品"})
                return WorkerResult(req.model.key, (str(output),), 10, 10)
            report = self.execute(p, worker, tool_runner=run_tool,
                                  verifier=lambda req, result: output.read_text(encoding="utf-8") == "第二階段的成品")
            self.assertEqual(report.status, "completed")

    def test_all_eight_capabilities_remain_gated(self):
        from jev import CAPABILITIES
        self.assertEqual(len(CAPABILITIES), 8)
        for cap in CAPABILITIES:
            SCRIPT["capability"] = (cap, 1.0)
            p = self.plan([task(capabilities=(cap,))])
            tools_called = []
            def worker(req, context):
                context.call("TestTool", {"action": "test"})
                return WorkerResult(req.model.key, req.task.outputs, 1, 1)
            report = self.execute(p, worker, tool_runner=lambda *args: tools_called.append(args))
            self.assertEqual(bool(tools_called), cap in {"read", "local_write", "process_spawn"}, cap)
            self.assertEqual(report.status, "completed" if tools_called else "ask", cap)

    def test_approval_is_bound_to_real_call_and_cannot_override_hard_deny(self):
        approvals, effects = [], []
        SCRIPT["capability"] = ("network_egress", 1.0)
        p = self.plan([task(capabilities=("network_egress",))])
        def worker(req, context):
            context.call("Fetch", {"url": "https://example.com"})
            return WorkerResult(req.model.key, req.task.outputs, 1, 1)
        report = self.execute(p, worker, approve=lambda *args: approvals.append(args) or True,
                              tool_runner=lambda *args: effects.append(args))
        self.assertEqual(report.status, "completed")
        self.assertEqual(len(approvals), 1)
        self.assertEqual(len(effects), 1)
        self.assertEqual(approvals[0][2], {"url": "https://example.com"})
        def blocked(req, context):
            context.call("Bash", {"command": "git push --force"})
            self.fail("硬規則不可覆寫")
        self.assertEqual(self.execute(p, blocked, approve=lambda *args: self.fail("不可詢問覆寫")).status, "ask")

    def test_tool_scope_and_limits_before_model_call(self):
        p = self.plan([task(capabilities=("read",))])
        def worker(req, context):
            context.call("Write", {"file_path": "unexpected.txt"})
        self.assertEqual(self.execute(p, worker).status, "ask")
        self.assertEqual(len(CALLS), 2)
        p = self.plan(limits=Limits(max_tool_calls=0))
        CALLS.clear()
        self.assertEqual(self.execute(p, worker).status, "ask")
        self.assertEqual(CALLS, [])

    def test_failure_stops_dependents_without_high_generation(self):
        p = self.plan([task(), task("b", depends_on=("a",))])
        report = self.execute(p, verifier=lambda *args: False)
        self.assertEqual(report.status, "replan")
        self.assertEqual(len(self.worker_calls), 1)
        self.assertEqual(report.completion_rate, 0)
        self.assertEqual(len(self.planner_calls), 1)

    def test_registry_drift_model_mismatch_and_invalid_usage_fail_closed(self):
        p = self.plan()
        self.reg.models[2] = dataclasses.replace(self.reg.models[2], tier="high")
        self.assertEqual(self.execute(p).status, "ask")
        self.assertEqual(self.worker_calls, [])
        self.reg = registry()
        for key, output_tokens in [("high", 1), ("low", -1), ("low", 99999)]:
            result = self.execute(p, lambda req, ctx: WorkerResult(key, req.task.outputs, 1, output_tokens))
            self.assertEqual(result.status, "ask")

    def test_verifier_error_and_missing_artifact_do_not_claim_completion(self):
        p = self.plan()
        self.assertEqual(self.execute(p, lambda req, ctx: WorkerResult(req.model.key, (), 1, 1)).status, "replan")
        def broken(*args):
            raise RuntimeError("驗收中斷")
        self.assertEqual(self.execute(p, verifier=broken).status, "replan")

    def test_failed_or_wrong_planner_never_calls_decision_layer(self):
        for planner in (lambda req: "預寫成品", lambda req: PlannerResult("low", (task(),), 1, 1),
                        lambda req: PlannerResult("high", (task(),), 1, 99999)):
            p = plan_phase("建立文件", planner, registry=self.reg,
                           data_class="public", provider="workflow_stub")
            self.assertEqual(p.status, "ask")
            self.assertEqual(CALLS, [])
            self.assertFalse(p.usage_complete)

    def test_host_data_class_is_not_downgraded(self):
        self.reg.platforms["test"]["data_classes_allowed"] = ["public", "internal"]
        def planner(req):
            return PlannerResult(req.model.key, (task(),), 1, 1)
        p = plan_phase("建立文件", planner, registry=self.reg,
                       data_class="internal", provider="workflow_stub")
        self.assertEqual(p.status, "ready")
        self.assertEqual(p.allocations[0].data_class, "internal")

    def test_malformed_or_unavailable_tool_gate_does_not_run_tool(self):
        p = self.plan()
        SCRIPT["error"] = True
        def worker(req, ctx):
            ctx.call("Write", {"file_path": "a.txt"})
        report = self.execute(p, worker, tool_runner=lambda *args: self.fail("gate 失敗不可執行"))
        self.assertEqual(report.status, "ask")
        self.assertFalse(report.usage_complete)

    def test_worker_cannot_swallow_gate_stop_and_claim_completion(self):
        p = self.plan(limits=Limits(max_tool_calls=0))
        def worker(req, ctx):
            try:
                ctx.call("Write", {"file_path": "a.txt"})
            except WorkflowStop:
                pass
            return WorkerResult(req.model.key, req.task.outputs, 1, 1)
        self.assertEqual(self.execute(p, worker).status, "ask")

    def test_callback_failure_is_one_attempt_and_no_high_fallback(self):
        p = self.plan()
        def broken(req, ctx):
            self.worker_calls.append(req)
            raise RuntimeError("模型服務中斷")
        report = self.execute(p, broken)
        self.assertEqual(report.status, "replan")
        self.assertEqual(len(self.worker_calls), 1)
        self.assertFalse(report.usage_complete)

    def test_unpriced_models_do_not_acquire_invented_prices(self):
        p = self.plan()
        self.assertEqual(p.status, "ready")
        self.assertFalse(p.allocations[0].model.priced)
        self.assertEqual(p.allocations[0].model.price_source, "unset")

    def test_missing_host_interfaces_stop_before_worker(self):
        p = self.plan()
        for arguments in ({"verifier": None}, {"tool_runner": None}, {"approve": "auto"}):
            self.assertEqual(self.execute(p, **arguments).status, "ask")
        self.assertEqual(self.worker_calls, [])

    def test_zero_intent_probability_cannot_allow_a_tool(self):
        p = self.plan()
        SCRIPT["matches_stated_intent"] = 0.0
        effects = []
        def worker(req, ctx):
            ctx.call("Write", {"file_path": "a.txt"})
            return WorkerResult(req.model.key, req.task.outputs, 1, 1)
        self.assertEqual(self.execute(p, worker, tool_runner=lambda *args: effects.append(args)).status, "ask")
        self.assertEqual(effects, [])

    def test_invalid_gate_confidence_cannot_allow_a_tool(self):
        p = self.plan()
        SCRIPT["capability"] = ("local_write", float("inf"))
        effects = []
        def worker(req, ctx):
            ctx.call("Write", {"file_path": "a.txt"})
            return WorkerResult(req.model.key, req.task.outputs, 1, 1)
        self.assertEqual(self.execute(p, worker, tool_runner=lambda *args: effects.append(args)).status, "ask")
        self.assertEqual(effects, [])


if __name__ == "__main__":
    unittest.main()
