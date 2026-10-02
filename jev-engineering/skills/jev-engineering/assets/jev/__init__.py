"""A portable decision layer for agent loops.

    [G] generation  -> 第二階段 medium/low executor
    [D] decision    -> this package
    [C] exact rule  -> your code

Quick start:

    from jev import decide, Choice, gate

    r = decide(
        state={"command": cmd, "cwd": cwd},
        questions={"risk": Choice(
            instructions="What happens if `command` runs inside `cwd`?",
            criteria={
                "read_only":   "Only reads, lists, searches files or runs tests",
                "local_edit":  "Changes files inside the project that git can restore",
                "destructive": "Deletes data, rewrites git history or touches files outside the project",
                "external":    "Sends data out, pushes, deploys, installs or spends money",
                "other":       "None of the above fits",
            },
        )},
    )
    decision = gate(r.answers["risk"], tau_act=0.90)

Standard library only. Set TYPESAFE_API_KEY, or JEV_PROVIDER=llm to run against
a chat model instead.
"""

from .bulk import RowResult, estimate, label_rows, split_tail, summarise
from .client import (
    DEFAULT_MODEL,
    JevError,
    available_providers,
    decide,
    register_provider,
)
from .compose import (
    EnsembleVerdict,
    PlanResult,
    Round,
    debiased_pairwise,
    ensemble,
    run_plan,
    shortlist_then_choose,
    speculative,
    two_stage_choice,
)
from .control import (
    REGIMES,
    ControlLoop,
    RiskLimits,
    Tick,
    classify_regime,
)
from .economics import (
    BreakEven,
    CascadeEconomics,
    PolicyCost,
    TierProfile,
    cascade_economics,
    compare_policies,
    expected_task_cost,
    loop_overhead,
    router_breakeven_accuracy,
    tier_cost_table,
)
from .gate import Decision, Exit, aligned_pairwise, cascade, gate, thresholds_for_actions
from .routing import (
    DATA_CLASSES,
    TIER_ORDER,
    Model,
    Registry,
    RegistryError,
    RouteDecision,
    SwitchVerdict,
    route_task,
    self_route,
    switch_cost,
    worth_switching,
)
from .toolgate import CAPABILITIES, GateVerdict, ToolGate, normalise_call
from .types import (
    EXIT_OPTION,
    USD_PER_INPUT_TOKEN,
    Answer,
    Choice,
    Noul,
    QuestionSpecError,
    Result,
    Score,
)
from .workflow import (
    Allocation, ExecutionContext, ExecutionPlan, ExecutionReport, Limits,
    PlannerRequest, PlannerResult, TaskSpec, WorkerRequest, WorkerResult,
    WorkflowStop, plan_phase, execute_phase,
)

__all__ = [
    # 兩階段規劃與執行
    "Allocation", "ExecutionContext", "ExecutionPlan", "ExecutionReport", "Limits",
    "PlannerRequest", "PlannerResult", "TaskSpec", "WorkerRequest", "WorkerResult",
    "WorkflowStop", "plan_phase", "execute_phase",
    # primitives
    "Choice",
    "Score",
    "Noul",
    "Answer",
    "Result",
    "QuestionSpecError",
    "EXIT_OPTION",
    "USD_PER_INPUT_TOKEN",
    # the call
    "decide",
    "register_provider",
    "available_providers",
    "JevError",
    "DEFAULT_MODEL",
    # the gate
    "gate",
    "cascade",
    "Decision",
    "Exit",
    "thresholds_for_actions",
    "aligned_pairwise",
    # bulk
    "label_rows",
    "estimate",
    "split_tail",
    "summarise",
    "RowResult",
    # routing and self-switching
    "Registry",
    "Model",
    "RegistryError",
    "RouteDecision",
    "SwitchVerdict",
    "route_task",
    "self_route",
    "switch_cost",
    "worth_switching",
    "TIER_ORDER",
    "DATA_CLASSES",
    # economics
    "TierProfile",
    "PolicyCost",
    "CascadeEconomics",
    "BreakEven",
    "compare_policies",
    "expected_task_cost",
    "router_breakeven_accuracy",
    "cascade_economics",
    "loop_overhead",
    "tier_cost_table",
    # tool gating
    "ToolGate",
    "GateVerdict",
    "CAPABILITIES",
    "normalise_call",
    # real-time control
    "ControlLoop",
    "Tick",
    "RiskLimits",
    "classify_regime",
    "REGIMES",
    # composite decisions
    "Round",
    "PlanResult",
    "run_plan",
    "speculative",
    "two_stage_choice",
    "shortlist_then_choose",
    "ensemble",
    "EnsembleVerdict",
    "debiased_pairwise",
]

__version__ = "1.2.0"
