"""v1.3 寬度執行測試：交接清單、扇出前審查、canary、並行上限、失敗隔離與斷路。stub，無網路。"""
import json
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "assets"))

from jev import Model, Registry, register_provider
from jev.workflow import Limits, TaskSpec, PlannerResult, WorkerResult, WorkflowStop, plan_phase
from jev.swarm import (
    SPEC_CLEAR_THRESHOLD, SwarmPolicy, execute_swarm, load_manifest, preflight,
    template_groups, to_manifest, waves, write_manifest,
)

SCRIPT = {}
DECIDE_CALLS = []


@register_provider("swarm_stub")
def stub(state, questions, model, timeout):
    DECIDE_CALLS.append(sorted(questions))
    if SCRIPT.get("error") and any(k.startswith("clear_") for k in questions):
        raise RuntimeError("模擬決策服務中斷")
    answers = {}
    for key, spec in questions.items():
        if key.startswith("tier_"):
            pick, confidence = ("low", 0.99)
        elif key.startswith("data_"):
            pick, confidence = ("public", 0.99)
        elif key == "capability":
            pick, confidence = SCRIPT.get("capability", ("local_write", 0.99))
        else:
            default = SCRIPT.get("clear", 0.95) if key.startswith("clear_") else 1.0
            answers[key] = {"type": "noul", "noul": SCRIPT.get(key, default)}
            continue
        answers[key] = {"type": "choice", "choice": pick, "confidence": confidence,
                        "probabilities": {k: float(k == pick) for k in spec.criteria}}
    return {"model": "stub", "answers": answers,
            "usage": {"input_tokens": 3, "output_tokens": SCRIPT.get("out", 0)}}


def registry():
    return Registry(models=[Model(key=t, display=t, platform="test", tier=t,
                                  api_id="stub-" + t, api_id_verified=True)
                            for t in ("high", "medium", "low")],
                    platforms={"test": {"data_classes_allowed": ["public", "internal"]}})


def company(i, **kw):
    values = dict(task_id="co_%02d" % i, objective="整理公司 %d 的年度營收，輸出 markdown 表格" % i,
                  inputs=("filings/%d.json" % i,), outputs=("out/co_%02d.md" % i,),
                  acceptance=("表格含 年度、營收、幣別 三欄", "數字可回溯到 inputs"),
                  capabilities=("local_write",), max_output_tokens=256)
    values.update(kw)
    return TaskSpec(**values)


def fleet(n, summary=True):
    tasks = [company(i) for i in range(n)]
    if summary:
        tasks.append(TaskSpec(task_id="summary", objective="彙整所有公司表格成比較表",
                              inputs=(), outputs=("out/summary.md",),
                              acceptance=("每家公司一列",), capabilities=("local_write",),
                              depends_on=tuple(t.task_id for t in tasks), max_output_tokens=512))
    return tasks


LIMITS = Limits(max_tasks=64, max_total_output_tokens=60000)


class SwarmTests(unittest.TestCase):
    def setUp(self):
        SCRIPT.clear()
        DECIDE_CALLS.clear()
        self.reg = registry()
        self.calls = []
        self.lock = threading.Lock()
        self.active = 0
        self.peak = 0
        self.events = []

    def plan(self, tasks):
        def planner(request):
            return PlannerResult(request.model.key, tuple(tasks), 10, 20)
        p = plan_phase("分析一批公司", planner, registry=self.reg, data_class="public",
                       provider="swarm_stub", limits=LIMITS)
        self.assertEqual(p.status, "ready", p.reason)
        return p

    def worker(self, fail=(), delay=0.02):
        def run(request, context):
            tid = request.task.task_id
            with self.lock:
                self.calls.append(tid)
                self.events.append(("start", tid))
                self.active += 1
                self.peak = max(self.peak, self.active)
            time.sleep(delay)
            with self.lock:
                self.active -= 1
                self.events.append(("end", tid))
            if tid in fail:
                raise RuntimeError("模擬 worker 失敗")
            return WorkerResult(request.model.key, request.task.outputs, 5, 7)
        return run

    def swarm(self, plan, worker=None, policy=SwarmPolicy(concurrency=4, requests_per_minute=60000),
              **kw):
        return execute_swarm(plan, worker or self.worker(),
                             verifier=kw.pop("verifier", lambda req, res: True),
                             tool_runner=kw.pop("tool_runner", lambda name, args: None),
                             registry=self.reg, provider="swarm_stub", policy=policy, **kw)

    # -- 結構 ----------------------------------------------------------------

    def test_waves_layer_by_dependencies(self):
        layers = waves(fleet(3))
        self.assertEqual(layers, (("co_00", "co_01", "co_02"), ("summary",)))

    def test_template_groups_share_capabilities_and_acceptance(self):
        groups = template_groups(fleet(5))
        sizes = sorted(len(g.task_ids) for g in groups)
        self.assertEqual(sizes, [1, 5])

    # -- Handoff Wire ---------------------------------------------------------

    def test_manifest_round_trip_restores_types_and_allocations(self):
        p = self.plan(fleet(4))
        loaded, policy = load_manifest(to_manifest(p, "EV", SwarmPolicy(concurrency=3)), self.reg)
        self.assertEqual(policy.concurrency, 3)
        self.assertEqual([a.task for a in loaded.allocations], [a.task for a in p.allocations])
        self.assertIsInstance(loaded.allocations[-1].task.depends_on, tuple)
        self.assertEqual([a.model for a in loaded.allocations], [a.model for a in p.allocations])
        self.assertEqual((loaded.input_tokens, loaded.output_tokens),
                         (p.input_tokens, p.output_tokens))

    def test_manifest_file_written_and_tamper_detected(self):
        import tempfile
        p = self.plan(fleet(2))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "task_manifest.json"
            digest = write_manifest(p, path, "EV")
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["sha256"], digest)
            data["tasks"][0]["objective"] = "改成別的工作"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(WorkflowStop):
                load_manifest(path, self.reg)

    def test_manifest_rejects_unknown_model_and_malformed_fields(self):
        p = self.plan(fleet(2))
        m = to_manifest(p, "EV")
        other = Registry(models=[mm for mm in self.reg.models if mm.tier != "low"],
                         platforms={"test": {"data_classes_allowed": ["public"]}})
        with self.assertRaises(WorkflowStop):
            load_manifest(m, other)
        broken = dict(m)
        del broken["limits"]
        with self.assertRaises(WorkflowStop):     # 不能漏成 KeyError
            load_manifest(broken, self.reg)
        with self.assertRaises(WorkflowStop):
            to_manifest(p, "EV", SwarmPolicy(concurrency=0))

    # -- 扇出前審查 -----------------------------------------------------------

    def test_preflight_skips_decision_when_nothing_fans_out(self):
        p = self.plan([company(0)])
        DECIDE_CALLS.clear()
        self.assertEqual(preflight(p, provider="swarm_stub").status, "ready")
        self.assertEqual(DECIDE_CALLS, [])

    def test_ambiguous_template_returns_to_planning_before_any_worker(self):
        SCRIPT["clear"] = 0.40
        report = self.swarm(self.plan(fleet(6)))
        self.assertEqual(report.status, "replan")
        self.assertEqual(self.calls, [])
        self.assertIn("6", report.reason)

    def test_spec_clear_threshold_boundary(self):
        SCRIPT["clear"] = SPEC_CLEAR_THRESHOLD
        self.assertEqual(preflight(self.plan(fleet(3)), provider="swarm_stub").status, "ready")
        SCRIPT["clear"] = SPEC_CLEAR_THRESHOLD - 0.001
        self.assertEqual(preflight(self.plan(fleet(3)), provider="swarm_stub").status, "replan")

    def test_preflight_failure_asks_and_never_executes(self):
        p = self.plan(fleet(3))
        SCRIPT["error"] = True
        report = self.swarm(p)
        self.assertEqual(report.status, "ask")
        self.assertEqual(self.calls, [])

    # -- 並行執行 -------------------------------------------------------------

    def test_happy_path_bounded_parallel_with_canary_first(self):
        report = self.swarm(self.plan(fleet(10)))
        self.assertEqual(report.status, "completed", report.reason)
        self.assertEqual(report.completion_rate, 1.0)
        self.assertTrue(1 < self.peak <= 4, self.peak)
        self.assertLessEqual(report.peak_concurrency, 4)
        canary = report.canaries[0]
        canary_end = self.events.index(("end", canary))
        others = [i for i, (kind, tid) in enumerate(self.events)
                  if kind == "start" and tid.startswith("co_") and tid != canary]
        self.assertTrue(all(i > canary_end for i in others), "canary 通過前不得放行同組任務")
        self.assertEqual(self.calls[-1], "summary")
        self.assertEqual(report.waves[-1], ("summary",))

    def test_dependencies_receive_only_their_artifacts(self):
        seen = {}

        def worker(request, context):
            seen[request.task.task_id] = dict(request.dependency_artifacts)
            return WorkerResult(request.model.key, request.task.outputs, 1, 1)
        self.assertEqual(self.swarm(self.plan(fleet(3)), worker).status, "completed")
        self.assertEqual(set(seen["summary"]), {"co_00", "co_01", "co_02"})
        self.assertEqual(seen["co_01"], {})

    def test_failed_canary_holds_its_group(self):
        p = self.plan(fleet(8))
        canary = template_groups([a.task for a in p.allocations])[0].task_ids[0]
        report = self.swarm(p, verifier=lambda req, res: req.task.task_id != canary)
        self.assertEqual(report.status, "replan")
        self.assertEqual(self.calls, [canary])
        self.assertEqual(len(report.held), 7)          # 同組其餘 7 份未派發
        self.assertEqual(report.blocked, ("summary",))  # 依賴 canary，屬於阻擋而非保留
        self.assertIn("canary", report.reason)

    def test_failure_isolated_to_dependents(self):
        tasks = [company(0), company(1, acceptance=("另一種驗收",)),
                 TaskSpec(task_id="after_0", objective="接續 co_00", inputs=(),
                          outputs=("out/after_0.md",), acceptance=("第三種",),
                          capabilities=("local_write",), depends_on=("co_00",), max_output_tokens=64)]
        policy = SwarmPolicy(concurrency=2, requests_per_minute=60000, breaker_failure_ratio=1.0,
                             breaker_min_failures=5)
        report = self.swarm(self.plan(tasks), self.worker(fail=("co_00",)), policy=policy)
        self.assertEqual(report.status, "replan")
        self.assertEqual(set(report.completed), {"co_01"})
        self.assertEqual(report.blocked, ("after_0",))
        self.assertNotIn("after_0", self.calls)

    def test_breaker_trips_and_stops_dispatch(self):
        tasks = fleet(10, summary=False)
        policy = SwarmPolicy(concurrency=1, requests_per_minute=60000, canary_min_group=100,
                             breaker_failure_ratio=0.25, breaker_min_failures=2)
        report = self.swarm(self.plan(tasks), self.worker(fail={t.task_id for t in tasks}),
                            policy=policy)
        self.assertTrue(report.breaker_tripped)
        self.assertEqual(report.status, "replan")
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(len(report.held), 8)

    def test_tool_gate_ask_stops_new_dispatch(self):
        SCRIPT["capability"] = ("network_egress", 1.0)
        tasks = [company(i, capabilities=("network_egress",)) for i in range(4)]

        def worker(request, context):
            self.calls.append(request.task.task_id)
            context.call("Fetch", {"url": "https://example.com"})
            return WorkerResult(request.model.key, request.task.outputs, 1, 1)
        policy = SwarmPolicy(concurrency=1, requests_per_minute=60000, canary_min_group=100)
        report = self.swarm(self.plan(tasks), worker, policy=policy)
        self.assertEqual(report.status, "ask")
        self.assertEqual(len(self.calls), 1)

    def test_wrong_model_is_a_task_failure_not_a_completion(self):
        def worker(request, context):
            return WorkerResult("high", request.task.outputs, 1, 1)
        report = self.swarm(self.plan(fleet(2, summary=False)), worker,
                            policy=SwarmPolicy(concurrency=2, requests_per_minute=60000,
                                               breaker_min_failures=5))
        self.assertEqual(report.completed, {})
        self.assertNotEqual(report.status, "completed")

    def test_preflight_tokens_count_against_budget(self):
        p = self.plan(fleet(3))
        SCRIPT["out"] = 59000                           # 只讓扇出前審查的用量爆表
        report = self.swarm(p)
        self.assertEqual(report.status, "ask")
        self.assertEqual(self.calls, [])

    def test_invalid_preflight_usage_fails_closed(self):
        p = self.plan(fleet(3))
        SCRIPT["out"] = -5                              # 損壞的用量回報
        self.assertEqual(preflight(p, provider="swarm_stub").status, "ask")
        self.assertEqual(self.swarm(p).status, "ask")
        self.assertEqual(self.calls, [])

    def test_usage_totals_include_planner_preflight_and_workers(self):
        p = self.plan(fleet(2, summary=False))
        report = self.swarm(p)
        self.assertEqual(report.status, "completed")
        self.assertEqual(report.output_tokens, p.output_tokens + 0 + 2 * 7)


if __name__ == "__main__":
    unittest.main()
