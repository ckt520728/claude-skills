"""
Jev-Engineering research graph: plan (high tier) -> collect (code) -> notes swarm (medium, parallel)
-> draft + code checks + repair (medium) -> audit (high, preferably another provider) -> replan loop,
then deliverables in parallel, citation lookup, knowledge-base merge and knowledge-base RSI.

The model writes; code decides what counts as verified; the graph records what actually happened.
Graph files follow the Karpathy agent-graph format: graph.md, checks.md, progress.md.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

import anyio

from . import llm, render
from .checks import Check, check_numbers, cited_keys, extract_json
from .config import CONFIG, LANGUAGE_NAME, OUTPUT_DIR
from .pipeline import AskResult, BudgetError, ResearchRequest, ResearchRun, RunCancelled, _specs
from .sources import Evidence

NOTE_BATCH = 6
MAX_NOTE_WORKERS = 6
def _num(value) -> float:
    """Model-supplied numbers are parsed defensively: a malformed field must not kill a paid run."""
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


BLOG_LANGUAGE_NAME = {"zh-TW": "Traditional Chinese (Taiwan)", "en": "English"}


# ---------------------------------------------------------------- the graph record

@dataclass
class Node:
    id: str
    label: str
    tier: str = "code"
    status: str = "pending"  # pending | running | passed | failed | skipped
    attempts: int = 0
    detail: str = ""
    model: str = ""
    started: float = 0.0
    seconds: float = 0.0


@dataclass
class Graph:
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: List[Dict[str, str]] = field(default_factory=list)
    checks: List[Dict[str, str]] = field(default_factory=list)

    def add(self, node_id: str, label: str, tier: str = "code", after: Optional[List[str]] = None, model: str = "") -> Node:
        node = self.nodes.get(node_id) or Node(node_id, label, tier, model=model)
        self.nodes[node_id] = node
        for parent in after or []:
            if parent in self.nodes and {"source": parent, "target": node_id} not in self.edges:
                self.edges.append({"source": parent, "target": node_id})
        return node

    def start(self, node_id: str) -> None:
        node = self.nodes[node_id]
        node.status, node.attempts, node.started = "running", node.attempts + 1, time.time()

    def finish(self, node_id: str, ok: bool, detail: str = "", status: Optional[str] = None) -> None:
        node = self.nodes[node_id]
        node.status = status or ("passed" if ok else "failed")
        node.detail = detail[:300]
        node.seconds = round(time.time() - node.started, 1) if node.started else 0.0

    def gate(self, node_id: str, requirement: str, artifact: str, ok: bool, evidence: str) -> None:
        # Missing evidence is unresolved, never a pass.
        verdict = "PASS" if ok and evidence else ("UNRESOLVED" if ok else "FAIL")
        self.checks.append({"node": node_id, "requirement": requirement, "artifact": artifact, "verdict": verdict, "evidence": evidence[:300]})

    def to_dict(self) -> Dict:
        return {
            "nodes": [{"id": n.id, "label": n.label, "tier": n.tier, "status": n.status, "attempts": n.attempts, "detail": n.detail, "model": n.model, "seconds": n.seconds} for n in list(self.nodes.values())],
            "edges": list(self.edges),
        }

    def mermaid(self) -> str:
        style = {"passed": ":::ok", "failed": ":::bad", "running": ":::run", "skipped": ":::skip", "pending": ""}
        safe = lambda text: re.sub(r'["\[\](){}<>|]', " ", text)
        lines = ["flowchart LR"]
        for n in self.nodes.values():
            lines.append(f'  {n.id}["{safe(n.label)} · {n.tier}"]{style.get(n.status, "")}')
        lines += [f"  {e['source']} --> {e['target']}" for e in self.edges]
        lines += ["  classDef ok fill:#d1fae5,stroke:#059669", "  classDef bad fill:#fee2e2,stroke:#dc2626", "  classDef run fill:#dbeafe,stroke:#2563eb", "  classDef skip fill:#f3f4f6,stroke:#9ca3af"]
        return "\n".join(lines)


# ---------------------------------------------------------------- request

@dataclass
class JevRequest(ResearchRequest):
    planner: str = ""
    executor: str = ""
    auditor: str = ""


def default_roles() -> Dict[str, str]:
    """Planner and auditor from the high tier, executor from the medium tier. Prefer an auditor on another provider."""
    high, medium = llm.tier_models("high"), llm.tier_models("medium")
    usable = lambda refs: [r for r in refs if llm.available(r)] or refs
    high_ok, medium_ok = usable(high), usable(medium)
    planner = high_ok[0] if high_ok else CONFIG["provider"]["default_model"]
    executor = medium_ok[0] if medium_ok else planner
    writer_provider = llm.resolve(executor)[0]
    other = [r for r in high_ok if llm.resolve(r)[0] != writer_provider]
    return {"planner": planner, "executor": executor, "auditor": other[0] if other else planner}


# ---------------------------------------------------------------- prompts

PLANNER_SYSTEM = (
    "You are the Jev high-tier research planner. Phase 1 only: decide, gate and decompose. "
    "Never write the paper, slides, blog or any answer. Output one JSON object and nothing else."
)
AUDITOR_SYSTEM = (
    "You are an independent high-tier auditor. You did not write what you review. Check claims against the evidence, "
    "look for unsupported statements, figures not present in the cited source, mislabelled preprints or registry entries, "
    "missing coverage of the planned aspects, and leaked internal keys. Never rewrite the work. Output one JSON object only."
)
NOTES_SYSTEM = (
    "You are a medium-tier research executor building a wiki. From the evidence given, extract concepts and atomic claims. "
    "Every claim must cite the evidence keys it comes from, like [\"E3\"]; copy numbers exactly; never invent. Output one JSON object only."
)


def planner_prompt(topic: str, feedback: str, gaps: List[str], findings: List[str], loop: int) -> str:
    context = ""
    if gaps:
        context += "\nOpen gaps already recorded in the knowledge base for this topic:\n" + "\n".join(f"- {g}" for g in gaps[:12])
    if findings:
        context += f"\nThe auditor rejected loop {loop - 1}. Findings to address:\n" + "\n".join(f"- {f}" for f in findings[:12])
    if feedback:
        context += f"\nUser feedback: {feedback}"
    return (
        f"Research topic: {topic}{context}\n\n"
        "Return only JSON with these keys:\n"
        '"status": "ready" | "replan" | "ask"; "confidence": 0..1; "question": "" (only when status is ask);\n'
        '"queries": {"pubmed": [3-4 literature queries], "arxiv": [1-3 short phrases], "trials": [0-2 registry terms], '
        '"notebook": [2 questions for a curated notebook], "questions": [3 questions for an expert]};\n'
        '"aspects": [4-7 objects {"task_id": "A1", "objective": "what the review must answer", "acceptance": "how an auditor can tell it was answered"}].\n'
        "Aspects describe coverage, not content. Do not answer them."
    )


def notes_prompt(topic: str, pack: str) -> str:
    return (
        f"Topic: {topic}\n\nEVIDENCE:\n{pack}\n\n"
        'Return only JSON: {"notes": [{"concept": "short canonical name in English", "definition": "one sentence [E#]", '
        '"claims": [{"text": "atomic claim with any figure copied exactly", "keys": ["E#"]}], "related": ["other concept names"]}], '
        '"conflicts": [{"concept": "name", "detail": "how the sources disagree", "keys": ["E#", "E#"]}], '
        '"off_topic": ["E# keys whose content does not address the topic at all"]}. '
        "Use 2-6 concepts. Cite only keys shown above. Take no notes from off-topic keys."
    )


def audit_prompt(topic: str, aspects: List[Dict], paper: str, pack: str) -> str:
    plan = "\n".join(f"- {a.get('task_id', '')}: {a.get('objective', '')} (acceptance: {a.get('acceptance', '')})" for a in aspects) or "- (no aspects planned)"
    return (
        f"Topic: {topic}\n\nPLANNED ASPECTS:\n{plan}\n\nPAPER UNDER AUDIT:\n{paper}\n\nEVIDENCE:\n{pack}\n\n"
        'Return only JSON: {"verdict": "PASS" | "FAIL", "score": 0..1, "findings": [{"severity": "high|medium|low", "where": "section", '
        '"problem": "...", "evidence": "key or quote", "fix": "..."}], "new_queries": {"pubmed": [], "arxiv": [], "trials": []}, '
        '"gaps": ["what is still unknown or under-evidenced, phrased as a research question"]}. '
        "FAIL if any high-severity problem exists."
    )


# ---------------------------------------------------------------- the run

class JevRun(ResearchRun):
    """ResearchRun with the Jev graph, a parallel executor swarm, an independent auditor and the knowledge-base layer."""

    def __init__(self, request: JevRequest, on_log: Optional[Callable[[str], None]] = None):
        roles = default_roles()
        request.planner = request.planner or roles["planner"]
        request.executor = request.executor or request.model or roles["executor"]
        request.auditor = request.auditor or roles["auditor"]
        request.model = request.executor
        self.graph = Graph()
        self.audits: List[Dict] = []
        self.aspects: List[Dict] = []
        self.notes: List[Dict] = []
        self.conflicts: List[Dict] = []
        self.gaps: List[str] = []
        self.dropped_claims = 0
        self.kb_result: Dict = {}
        self.plan_status: List[Dict] = []
        self.off_topic: set = set()
        super().__init__(request, on_log)

    # ------------------------------------------------------------ records

    def report(self) -> Dict:
        data = super().report()
        data.update({
            "engine": "jev", "graph": self.graph.to_dict() if hasattr(self, "graph") else {"nodes": [], "edges": []},
            "audits": getattr(self, "audits", []), "aspects": getattr(self, "aspects", []), "kb": getattr(self, "kb_result", {}),
            "roles": {"planner": self.request.planner, "executor": self.request.executor, "auditor": self.request.auditor} if hasattr(self.request, "planner") else {},
            "notes_count": len(getattr(self, "notes", [])), "dropped_claims": getattr(self, "dropped_claims", 0), "gaps": getattr(self, "gaps", []),
            "plan_status": getattr(self, "plan_status", []), "off_topic": sorted(getattr(self, "off_topic", set())),
        })
        return data

    def _write_graph_files(self) -> None:
        g = self.graph
        rows = "\n".join(f"| {n.id} | {n.label} | {n.tier} | {n.model or '-'} | {n.status} | {n.attempts} | {n.detail.replace('|', '/')} |" for n in g.nodes.values())
        (self.dir / "graph.md").write_text(
            f"# Graph: {self.request.topic}\n\nRun `{self.run_id}`\n\n## Task contract\n\nTopic: {self.request.topic}. Loops ≤ {self.request.passes}. "
            f"Budget US${self.request.budget_usd:.2f}. Planner `{self.request.planner}`, executor `{self.request.executor}`, auditor `{self.request.auditor}`.\n\n"
            f"## Nodes\n\n| Node | Label | Tier | Model | Status | Attempts | Detail |\n|---|---|---|---|---|---|---|\n{rows}\n\n"
            f"## Dependency edges\n\n```mermaid\n{g.mermaid()}\n```\n\n## Aspects (planner acceptance)\n\n"
            + ("\n".join(f"- **{a.get('task_id', '')}** {a.get('objective', '')} — _{a.get('acceptance', '')}_" for a in self.aspects) or "- none") + "\n",
            encoding="utf-8")
        check_rows = "\n".join(f"| {c['node']} | {c['requirement'].replace('|', '/')} | {c['artifact']} | {c['verdict']} | {c['evidence'].replace('|', '/')} |" for c in g.checks)
        (self.dir / "checks.md").write_text(f"# Checks\n\n| Node | Requirement | Artifact version | Verdict | Evidence |\n|---|---|---|---|---|\n{check_rows}\n", encoding="utf-8")
        done = [n.id for n in g.nodes.values() if n.status == "passed"]
        failed = [n.id for n in g.nodes.values() if n.status == "failed"]
        pending = [n.id for n in g.nodes.values() if n.status in ("pending", "running")]
        (self.dir / "progress.md").write_text(
            f"# Progress\n\n- Status: {self.status}\n- Stage: {self.stage}\n- Spent: US${self.spent:.2f} of {self.request.budget_usd:.2f}\n"
            f"- Passed nodes: {', '.join(done) or 'none'}\n- Failed nodes: {', '.join(failed) or 'none'}\n- Pending: {', '.join(pending) or 'none'}\n"
            f"- Evidence: {len(self.evidence)}; notes: {len(self.notes)}; dropped claims: {self.dropped_claims}\n"
            f"- Open gaps: {len(self.gaps)}\n\n## Resume\n\nRe-run with the same topic; the planner reads open gaps from the knowledge base. "
            "Artifacts in this folder are not overwritten.\n", encoding="utf-8")

    def _save(self) -> None:
        super()._save()
        if hasattr(self, "graph") and self.graph.nodes:
            try:
                self._write_graph_files()
            except OSError:
                pass

    # ------------------------------------------------------------ helpers

    def _check_evidence(self) -> Dict[str, Evidence]:
        """Checks count only on-topic evidence, so citing an off-topic source is an error, not padding."""
        return {k: v for k, v in self.evidence.items() if k not in getattr(self, "off_topic", set())}

    def _pack(self, keys: Optional[List[str]] = None) -> str:
        """Evidence flagged off-topic by an executor is kept on record but not offered to the writer."""
        if keys is None and getattr(self, "off_topic", None):
            keys = [k for k in self.evidence if k not in self.off_topic] or None
        return super()._pack(keys)

    def _json(self, result: AskResult) -> Dict:
        if result.error:
            raise ValueError(result.error)
        data = json.loads(extract_json(result.output))
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")
        return data

    def _kb_gaps(self) -> List[str]:
        try:
            from . import kb
            return kb.open_gaps(kb.kb_root(), self.request.topic)
        except Exception as e:  # The KB is optional for planning; say so instead of hiding it.
            self.log(f"Knowledge base gaps unavailable: {str(e)[:120]}")
            return []

    # ------------------------------------------------------------ nodes

    async def _plan_node(self, loop: int, findings: List[str], after: List[str]) -> Dict:
        node = f"plan{loop}"
        self.graph.add(node, f"Plan (loop {loop})", "high", after, self.request.planner)
        self.graph.start(node)
        self.stage = f"loop {loop}: planning"
        self.log(f"Loop {loop}: planner {self.request.planner} is planning...")
        gaps = self._kb_gaps() if loop == 1 else []
        if gaps:
            self.log(f"  Planner sees {len(gaps)} open gap(s) from the knowledge base.")
        result = await self._ask(planner_prompt(self.request.topic, self.request.feedback, gaps, findings, loop),
                                 model=self.request.planner, system=PLANNER_SYSTEM, budget_share=0.15)
        try:
            plan = self._json(result)
            queries = plan.get("queries") or {}
            if not any(queries.get(k) for k in ("pubmed", "arxiv", "trials")):
                raise ValueError("no queries")
        except ValueError as e:
            self.graph.finish(node, False, f"Unusable plan: {str(e)[:120]}; searching the topic directly")
            self.graph.gate(node, "Plan JSON with queries", "plan.json", False, str(e)[:200])
            self.log(f"  Plan unusable ({str(e)[:100]}); searching the topic directly.")
            return {"pubmed": [self.request.topic], "arxiv": [self.request.topic], "trials": [self.request.topic], "questions": []}
        status, confidence = str(plan.get("status", "ready")), _num(plan.get("confidence"))
        self.plan_status.append({"loop": loop, "status": status, "confidence": confidence, "question": plan.get("question", "")})
        if loop == 1 or plan.get("aspects"):
            self.aspects = [a for a in plan.get("aspects") or [] if isinstance(a, dict)][:7]
        (self.dir / f"plan_loop{loop}.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        note = f"status {status}, confidence {confidence:.2f}, {len(self.aspects)} aspect(s)"
        if status == "ask" and plan.get("question"):
            note += f"; planner question (no human in the loop, proceeding): {plan['question'][:120]}"
        self.graph.finish(node, True, note)
        self.graph.gate(node, "Plan JSON with queries and aspects", f"plan_loop{loop}.json", True, note)
        self.log(f"  Plan: {note}.")
        return queries

    def _collect_node(self, loop: int, queries: Dict, after: List[str]) -> int:
        node = f"collect{loop}"
        self.graph.add(node, f"Collect evidence (loop {loop})", "code", after)
        self.graph.start(node)
        self.stage = f"loop {loop}: collecting"
        added = self._collect(queries, first=(loop == 1))
        live = [s.name for s in self.source_status.values() if s.state in ("LIVE", "FALLBACK", "SAVED")]
        self.graph.finish(node, bool(self.evidence), f"{added} new item(s); total {len(self.evidence)}; sources with data: {', '.join(live) or 'none'}")
        self.graph.gate(node, "At least one evidence item from a real source", "evidence pack", bool(self.evidence), f"{len(self.evidence)} items from {', '.join(live) or 'no source'}")
        return added

    def _valid_claims(self, notes: List[Dict], allowed: set) -> List[Dict]:
        """Code decides: a claim survives only if it cites keys from its batch and its numbers appear in those sources."""
        kept = []
        for note in notes:
            if not isinstance(note, dict) or not str(note.get("concept", "")).strip():
                continue
            claims = []
            for claim in note.get("claims") or []:
                if not isinstance(claim, dict):
                    continue
                keys = [k for k in claim.get("keys") or [] if k in allowed]
                text = str(claim.get("text", "")).strip()
                if not keys or not text:
                    self.dropped_claims += 1
                    continue
                grounded = check_numbers(f"{text} [{', '.join(keys)}]", self.evidence)
                if not grounded.passed:
                    self.dropped_claims += 1
                    continue
                claims.append({"text": re.sub(r"\[E\d+(?:\s*,\s*E\d+)*\]", "", text).strip(), "keys": keys})
            if claims:
                definition = re.sub(r"\[E\d+(?:\s*,\s*E\d+)*\]", "", str(note.get("definition", ""))).strip()
                kept.append({"concept": str(note["concept"]).strip()[:80], "definition": definition, "claims": claims,
                             "related": [str(r).strip()[:80] for r in note.get("related") or [] if str(r).strip()][:8]})
        return kept

    async def _notes_node(self, loop: int, new_keys: List[str], after: List[str]) -> None:
        node = f"notes{loop}"
        batches = [new_keys[i:i + NOTE_BATCH] for i in range(0, len(new_keys), NOTE_BATCH)][:MAX_NOTE_WORKERS]
        self.graph.add(node, f"Executor swarm: wiki notes ×{len(batches)} (loop {loop})", "medium", after, self.request.executor)
        if not batches:
            self.graph.finish(node, True, "No new evidence to take notes on", status="skipped")
            return
        self.graph.start(node)
        self.stage = f"loop {loop}: executor swarm ({len(batches)} workers)"
        self.log(f"Loop {loop}: {len(batches)} executor(s) taking wiki notes in parallel...")
        outcomes: List[Optional[Dict]] = [None] * len(batches)
        share = 0.2 / max(1, len(batches))

        async def worker(index: int, keys: List[str]) -> None:
            try:
                result = await self._ask(notes_prompt(self.request.topic, self._pack(keys)), model=self.request.executor, system=NOTES_SYSTEM, budget_share=share)
                outcomes[index] = {"keys": keys, "data": self._json(result)}
            except RunCancelled:
                outcomes[index] = {"keys": keys, "error": "cancelled"}
            except Exception as e:  # One worker failing must not cancel its siblings.
                outcomes[index] = {"keys": keys, "error": str(e)[:160]}

        async with anyio.create_task_group() as group:
            for i, keys in enumerate(batches):
                group.start_soon(worker, i, keys)
        if self.cancel_event.is_set():
            raise RunCancelled()
        ok, failed = 0, 0
        for outcome in outcomes:
            if not outcome or "error" in outcome:
                failed += 1
                continue
            flagged = {k for k in outcome["data"].get("off_topic") or [] if k in outcome["keys"]}
            self.off_topic |= flagged
            allowed = set(outcome["keys"]) - flagged
            kept = self._valid_claims(outcome["data"].get("notes") or [], allowed)
            self.notes.extend(kept)
            for c in outcome["data"].get("conflicts") or []:
                if isinstance(c, dict) and [k for k in c.get("keys") or [] if k in allowed]:
                    self.conflicts.append({"concept": str(c.get("concept", ""))[:80], "detail": str(c.get("detail", ""))[:300], "keys": [k for k in c["keys"] if k in allowed]})
            ok += 1
        detail = (f"{ok}/{len(batches)} worker(s) succeeded; {len(self.notes)} concept note(s) kept; {self.dropped_claims} claim(s) dropped by code checks; "
                  f"{len(self.off_topic)} off-topic source(s) excluded from the paper")
        self.graph.finish(node, ok > 0, detail)
        self.graph.gate(node, "Claims cite batch keys and grounded numbers", "notes", ok > 0, detail)
        self.log(f"  {detail}.")

    async def _draft_node(self, loop: int, best: AskResult, findings: List[Dict], after: List[str]) -> AskResult:
        node = f"draft{loop}"
        self.graph.add(node, f"Draft + code checks (loop {loop})", "medium", after, self.request.executor)
        self.graph.start(node)
        self.stage = f"loop {loop}: drafting"
        spec = _specs()["paper"].format(topic=self.request.topic)
        if self.aspects:
            spec += "\nThe review must cover these planned aspects:\n" + "\n".join(f"- {a.get('objective', '')}" for a in self.aspects)
        feedback = f"\n\nAct on this feedback: {self.request.feedback}" if self.request.feedback else ""
        if loop == 1 or not best.output:
            prompt = f"{spec}{feedback}\n\nEVIDENCE:\n{self._pack()}"
        else:
            fixes = "\n".join(f"- [{f.get('severity', '')}] {f.get('where', '')}: {f.get('problem', '')} → {f.get('fix', '')}" for f in findings)
            prompt = (f"{spec}{feedback}\n\nRevise the draft below. Fix the auditor's findings and use any new evidence. "
                      f"Keep every supported statement.\nAuditor findings:\n{fixes}\n\nDRAFT:\n{best.output}\n\nEVIDENCE:\n{self._pack()}")
        self.log(f"Loop {loop}: executor {self.request.executor} is writing and checking the paper...")
        result = await self._ask(prompt, "paper", max_repairs=2, model=self.request.executor, budget_share=0.45)
        score = round(sum(c.score for c in result.checks) / max(1, len(result.checks)), 3)
        self.passes_done.append({
            "pass": loop, "new_sources": getattr(self, "_new_count", 0), "attempts": result.attempts, "failed_checks": sorted(result.failed_checks),
            "all_checks_passed": result.passed, "score": score, "checks": [c.to_dict() for c in result.checks],
            "spent_usd": round(self.spent, 4), "gaps_found": [], "error": result.error,
        })
        detail = f"{'all checks passed' if result.passed else 'checks failing'}; score {score}; {result.attempts} attempt(s)"
        self.graph.finish(node, result.passed, detail)
        for c in result.checks:
            self.graph.gate(node, c.name, f"paper loop {loop} attempt {result.attempts}", c.passed, c.message[:200])
        self.log(f"  {detail}; ${self.spent:.2f} spent.")
        return result if result.output else best

    async def _audit_node(self, loop: int, paper: AskResult, after: List[str]) -> Dict:
        node = f"audit{loop}"
        self.graph.add(node, f"Audit (loop {loop})", "high", after, self.request.auditor)
        self.graph.start(node)
        self.stage = f"loop {loop}: auditing"
        self.log(f"Loop {loop}: auditor {self.request.auditor} is reviewing...")
        keys = [k for k in cited_keys(paper.output) if k in self.evidence]
        result = await self._ask(audit_prompt(self.request.topic, self.aspects, paper.output, self._pack(keys or None)),
                                 model=self.request.auditor, system=AUDITOR_SYSTEM, budget_share=0.2)
        try:
            audit = self._json(result)
        except ValueError as e:
            audit = {"verdict": "FAIL", "score": 0.0, "findings": [{"severity": "high", "where": "audit", "problem": f"Audit output unusable: {str(e)[:120]}", "evidence": "", "fix": "Re-run the audit"}], "gaps": []}
        verdict = str(audit.get("verdict", "FAIL")).upper()
        # Code has the final word: a paper that fails its checks cannot pass audit.
        if verdict == "PASS" and not paper.passed:
            verdict = "FAIL"
            audit.setdefault("findings", []).append({"severity": "high", "where": "code checks", "problem": "Automated checks still fail", "evidence": ", ".join(sorted(paper.failed_checks)), "fix": "Fix the failing checks"})
        findings = [f for f in audit.get("findings") or [] if isinstance(f, dict)]
        if verdict == "PASS" and any(str(f.get("severity", "")).lower() == "high" for f in findings):
            verdict = "FAIL"  # The rule is "FAIL if any high-severity problem exists"; code enforces it.
        record = {"loop": loop, "verdict": verdict, "score": _num(audit.get("score")), "findings": findings[:20], "model": self.request.auditor}
        self.audits.append(record)
        self.gaps.extend(g for g in (str(x).strip() for x in audit.get("gaps") or []) if g and g not in self.gaps)
        (self.dir / f"audit_loop{loop}.json").write_text(json.dumps(audit, ensure_ascii=False, indent=1), encoding="utf-8")
        high = sum(1 for f in findings if str(f.get("severity", "")).lower() == "high")
        self.graph.finish(node, verdict == "PASS", f"{verdict}; {len(findings)} finding(s), {high} high")
        self.graph.gate(node, "Independent audit verdict", f"audit_loop{loop}.json", verdict == "PASS", f"{verdict}, score {record['score']}, {high} high finding(s)")
        self.log(f"  Audit {verdict}: {len(findings)} finding(s), {high} high.")
        if self.passes_done:
            self.passes_done[-1]["gaps_found"] = [f.get("problem", "") for f in findings][:10]
        audit["verdict"] = verdict
        return audit

    # ------------------------------------------------------------ loop

    async def _research_loop(self) -> AskResult:
        best, findings_text, findings = AskResult(""), [], []
        previous: List[str] = []
        for loop in range(1, self.request.passes + 1):
            if loop > 1 and self._remaining() < self.request.budget_usd * 0.35:
                self.log(f"Stopping before loop {loop}: keeping the rest of the budget for the deliverables.")
                break
            queries = await self._plan_node(loop, findings_text, previous)
            before = set(self.evidence)
            self._collect_node(loop, queries, [f"plan{loop}"])
            if not self.evidence:
                raise RuntimeError("No evidence could be collected from any source.")
            new_keys = [k for k in self.evidence if k not in before]
            self._new_count = len(new_keys)
            await self._notes_node(loop, new_keys, [f"collect{loop}"])
            best = await self._draft_node(loop, best, findings, [f"collect{loop}"] + ([f"audit{loop - 1}"] if loop > 1 else []))
            if not best.output:
                raise RuntimeError(best.error or "No draft was produced.")
            audit = await self._audit_node(loop, best, [f"draft{loop}", f"notes{loop}"])
            previous = [f"audit{loop}"]
            if audit["verdict"] == "PASS":
                self.log(f"Loop {loop}: audit passed; leaving the loop.")
                break
            findings = [f for f in audit.get("findings") or [] if isinstance(f, dict)]
            findings_text = [f"[{f.get('severity', '')}] {f.get('problem', '')}" for f in findings]
            extra = audit.get("new_queries") or {}
            if loop < self.request.passes and any(extra.get(k) for k in ("pubmed", "arxiv", "trials")):
                findings_text.append("Auditor-suggested queries: " + json.dumps(extra, ensure_ascii=False))
            for name in self.passes_done[-1]["failed_checks"]:
                from .pipeline import RULES
                if name in RULES:
                    self.candidate_rules[RULES[name][0]] = RULES[name][1]
        self._evolve()
        return best

    # ------------------------------------------------------------ deliverables

    def _spec(self, kind: str) -> str:
        from . import specs
        if kind == "deck":
            return specs.deck_spec(LANGUAGE_NAME)
        if kind == "blog":
            return specs.blog_spec(BLOG_LANGUAGE_NAME.get(CONFIG.get("blog_language", "zh-TW"), "Traditional Chinese (Taiwan)"))
        return _specs()[kind]

    async def _make_deliverables(self, paper: AskResult) -> None:
        ev, out = self.evidence, self.dir
        node = "deliver"
        last_audit = f"audit{len(self.audits)}" if self.audits else ""
        self.graph.add(node, "Executor swarm: deliverables", "medium", [last_audit] if last_audit else [], self.request.executor)
        self.graph.start(node)
        audit_ok = bool(self.audits) and self.audits[-1]["verdict"] == "PASS"
        note = self._note(paper) if audit_ok else (self._note(paper) + " The independent audit did not pass; see audit_loop files.")
        try:
            files = render.render_paper_apa(paper.output, ev, out, "Academic_Paper", paper.passed and audit_ok, note)
        except Exception as e:
            files, err = {}, f"Could not build the paper: {e}"
        else:
            err = ""
        self.deliverables.append({"kind": "paper", "verified": bool(files) and paper.passed and audit_ok and not err, "attempts": paper.attempts,
                                  "files": files, "checks": [c.to_dict() for c in paper.checks], "error": err or ("" if audit_ok else "Audit did not pass")})
        self.log(f"paper: {'verified' if self.deliverables[-1]['verified'] else 'NEEDS REVIEW'}.")
        wanted = CONFIG.get("deliverables", ["deck", "blog"])
        meta = self._blog_meta()
        jobs = []
        if "deck" in wanted:
            jobs.append(("deck", lambda r: {
                "html": render.render_deck_html(r.output, ev, out, "Interactive_Deck", r.passed, self._note(r)),
                "pptx": render.render_deck_pptx(r.output, ev, out, "Presentation", r.passed),
                "storyboard": render.render_storyboard(r.output, ev, out, "Storyboard"),
            }))
        if "blog" in wanted:
            jobs.append(("blog", lambda r: render.render_blog_house(r.output, ev, out, "Blog_Post", r.passed, self._note(r), meta)))
        self.log(f"Writing {len(jobs)} deliverable(s) in parallel...")
        share = 1.0 / max(1, len(jobs))  # Parallel jobs split what is left, so together they cannot overspend.

        async def job(kind: str, build) -> None:
            try:
                await self._make(kind, paper.output, build, budget_share=share)
            except RunCancelled:
                pass
            except Exception as e:
                self.deliverables.append({"kind": kind, "verified": False, "attempts": 0, "files": {}, "checks": [], "error": str(e)[:300]})

        async with anyio.create_task_group() as group:
            for kind, build in jobs:
                group.start_soon(job, kind, build)
        if self.cancel_event.is_set():
            raise RunCancelled()
        made = [d for d in self.deliverables if d["kind"] != "paper"]
        ok = all(d["verified"] for d in made) and len(made) == len(jobs)
        self.graph.finish(node, ok, ", ".join(f"{d['kind']}: {'verified' if d['verified'] else 'needs review'}" for d in made))
        for d in self.deliverables:
            self.graph.gate(node, f"{d['kind']} passes its checks", ", ".join(d["files"].values()) if isinstance(d.get("files"), dict) else "", d["verified"], d.get("error") or "all checks passed")

    def _blog_meta(self) -> Dict:
        kinds: Dict[str, int] = {}
        years: Dict[str, int] = {}
        for e in self.evidence.values():
            kinds[e.kind] = kinds.get(e.kind, 0) + 1
            if re.fullmatch(r"(19|20)\d\d", e.year or ""):
                years[e.year] = years.get(e.year, 0) + 1
        blog = CONFIG.get("blog", {})
        slug = re.sub(r"[^a-z0-9]+", "-", self.request.topic.lower()).strip("-")
        if len(slug) > 60:  # cut on a word boundary, never mid-word ("...-in-ai-re")
            slug = slug[:61].rsplit("-", 1)[0]
        slug = slug or "autoresearch"
        return {"slug": slug, "date": time.strftime("%Y-%m-%d"), "category": blog.get("category", "研究筆記"), "subtitle": "",
                "tags": blog.get("tags", []), "author": blog.get("author", ""), "evidence_kinds": kinds, "years": dict(sorted(years.items()))}

    # ------------------------------------------------------------ knowledge base

    def _kb_node(self, paper: AskResult) -> None:
        node = "kb"
        self.graph.add(node, "Merge into Second Brain + KB RSI", "code", ["deliver"])
        self.graph.start(node)
        self.stage = "updating the knowledge base"
        try:
            from . import kb, kb_rsi
            root = kb.kb_root()
            before = kb_rsi.fitness(root) if root.exists() else {}
            abstract = re.search(r"^#+\s*Abstract\s*\n(.+?)(?=^#)", paper.output, re.M | re.S)
            files = {f"{d['kind']}:{k}": str(self.dir / v) for d in self.deliverables for k, v in (d.get("files") or {}).items() if isinstance(v, str) and k != "publish_dir"}
            result = kb.integrate_run(root, {
                "run_id": self.run_id, "topic": self.request.topic, "date": time.strftime("%Y-%m-%d"),
                "summary": (abstract.group(1).strip() if abstract else "")[:3000],
                "evidence": [e.to_dict() for e in self.evidence.values() if e.key in set(cited_keys(paper.output)) | {k for n in self.notes for c in n["claims"] for k in c["keys"]}],
                "notes": self.notes, "gaps": self.gaps, "conflicts": self.conflicts, "deliverables": files,
            })
            queue = Path(CONFIG.get("knowledge_base", {}).get("queue_md", "")) if CONFIG.get("knowledge_base", {}).get("queue_md") else None
            decisions = kb_rsi.improve(root, OUTPUT_DIR.parent / ".rsi" / "kb_ledger.jsonl", queue)
            after = kb_rsi.fitness(root)
            kb.write_graph(root, OUTPUT_DIR / "kb_graph.json")
            self.kb_result = {"root": str(root), "created": result.get("created", []), "updated": result.get("updated", []),
                              "fitness_before": {k: v for k, v in before.items() if k != "details"}, "fitness_after": {k: v for k, v in after.items() if k != "details"},
                              "decisions": decisions}
            detail = f"{len(result.get('created', []))} created, {len(result.get('updated', []))} updated; fitness {before.get('score', 0):.3f} → {after.get('score', 0):.3f}; {sum(1 for d in decisions if d['decision'] == 'PROMOTE')} promoted"
            self.graph.finish(node, True, detail)
            self.graph.gate(node, "Pages merged; fitness measured by code", str(root), True, detail)
            self.log(f"Knowledge base: {detail}.")
        except Exception as e:
            self.kb_result = {"error": str(e)[:300]}
            self.graph.finish(node, False, f"Knowledge base update failed: {str(e)[:200]}")
            self.graph.gate(node, "Pages merged", "", False, str(e)[:200])
            self.log(f"Knowledge base update failed: {str(e)[:200]}")

    # ------------------------------------------------------------ entry point

    async def execute(self) -> Dict:
        try:
            self.log(f"Run {self.run_id}: planner {self.request.planner}, executor {self.request.executor}, auditor {self.request.auditor}; "
                     f"up to {self.request.passes} loop(s), budget ${self.request.budget_usd:.2f}.")
            problem = llm.budget_problem([self.request.planner, self.request.executor, self.request.auditor])
            if problem:
                raise RuntimeError(problem)
            paper = await self._research_loop()
            await self._make_deliverables(paper)
            (self.dir / "evidence.json").write_text(json.dumps([e.to_dict() for e in self.evidence.values()], ensure_ascii=False, indent=1), encoding="utf-8")
            self.graph.add("cite", "Online citation lookup", "code", ["deliver"])
            self.graph.start("cite")
            self._verify_citations([paper.output] + self._texts)
            self.graph.finish("cite", not self.citation_problems, f"{len(self.citation_problems)} problem(s)")
            self.graph.gate("cite", "Cited identifiers resolve with matching titles", "evidence.json", not self.citation_problems, "; ".join(self.citation_problems[:3]) or "all resolved")
            self._kb_node(paper)
            wanted = 1 + len(CONFIG.get("deliverables", ["deck", "blog"]))
            complete = len(self.deliverables) == wanted and all(d["verified"] for d in self.deliverables)
            self.status = "COMPLETED" if complete and not self.citation_problems and "error" not in self.kb_result else "NEEDS_REVIEW"
        except RunCancelled:
            self.status = "CANCELLED"
            self.log("Run cancelled.")
        except BaseExceptionGroup as group:
            cancelled = group.subgroup(RunCancelled)
            self.status = "CANCELLED" if cancelled or self.cancel_event.is_set() else "FAILED"
            first = group.exceptions[0] if group.exceptions else group
            self.error = "" if self.status == "CANCELLED" else str(first)[:500]
            self.log("Run cancelled." if self.status == "CANCELLED" else f"Stopped: {self.error}")
        except Exception as e:
            self.status = "FAILED"
            self.error = str(e)[:500]
            self.log(f"Stopped: {self.error}")
        for n in list(self.graph.nodes.values()):
            if n.status == "running":
                n.status, n.detail = "failed", (n.detail or ("cancelled" if self.status == "CANCELLED" else self.error))[:300]
            elif n.status == "pending":
                n.status = "skipped"
        self.stage = "finished"
        self.log(f"Finished: {self.status}. Spent ${self.spent:.2f} in {round(time.time() - self.started)}s.")
        return self.report()
