"""
The RSI research loop: plan -> collect -> draft -> verify and repair -> critique -> collect more -> revise,
then produce the deliverables. The model writes; code decides what counts as verified.
Every run writes to its own folder, so earlier results are never overwritten.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set

from . import llm, render, sources
from .checks import Check, cited_keys, extract_json, phi_hits, run_checks
from .config import CONFIG, LANGUAGE, LANGUAGE_NAME, RSI_DIR, RUNS_DIR
from .sources import Evidence, SourceStatus

PACK_CHARS = 5200
MAX_EVIDENCE = 60
FINAL_RESERVE = 0.45  # Share of the budget kept for the slides, blog post and infographic.

CONSTRAINTS = [
    "Every factual claim must carry a citation using the supplied keys, such as [E3] or [E3, E7]. Never invent a source.",
    "Copy every number exactly from the evidence cited beside it. If a figure is not in the evidence, leave it out.",
    "Never type DOIs, PMIDs, arXiv IDs, registry numbers or a reference list; those are generated automatically from the keys.",
    "Label preprints, secondary answers and registry entries for what they are. State plainly where evidence is missing or conflicting.",
    "Never include personal, institutional, date or case identifiers. Use plain Unicode, never LaTeX.",
    "Readers never see evidence keys: never write E3 in a sentence. Refer to a study by author or description, and put keys only inside citation brackets.",
]
# What a failing check teaches. A rule is kept only if it measurably helps (see _evolve).
RULES = {
    "CitationKeys": ("rule_citations_from_keys", "Cite only supplied [E#] keys, inside brackets, and never type identifiers or a reference list."),
    "NumericGrounding": ("rule_numbers_beside_source", "Put each figure in a sentence or table row that cites the source containing that exact figure; do not round or recompute."),
    "CleanText": ("rule_clean_text", "Use plain Unicode and the required terms, and never write placeholders or identifiers."),
    "Structure": ("rule_required_structure", "Follow the required section list and output format exactly before adding anything else."),
}


def _specs() -> Dict[str, str]:
    abstract = "## Abstract, ## 摘要 (the abstract in Traditional Chinese), " if LANGUAGE == "zh-TW" else "## Abstract, "
    note = {"zh-TW": "不能取代專業人員的個別評估與諮詢"}.get(LANGUAGE, "this does not replace professional advice")
    return {
        "paper": f"""Write a publication-style English review as Markdown on the topic: {{topic}}.
Use exactly these headings: # (a title), {abstract}## Introduction, ## Methods, ## Results, ## Discussion, ## Limitations, ## Conclusion. Do not write a References section.
In Methods, describe the sources actually listed in the evidence. In Results, compare studies with effect sizes, using at least one Markdown table with a citation in every row.
In Discussion, cover practical implications and ongoing work, and separate peer-reviewed evidence from preprints and registry entries.
Length: 1200-2200 words. Output only the Markdown.""",
        "deck": f"""Create a slide deck in {LANGUAGE_NAME}, keeping standard English technical terms, for professionals. Base it on the paper and evidence below.
Return only one JSON object: {{{{"slides":[{{{{"title":"...","bullets":["... [E1]"],"notes":"speaker notes"}}}}]}}}}
Use 9-12 slides and at most 5 short bullets each. Every bullet with a fact or number cites its key inside that same bullet.""",
        "blog": f"""Write a blog post in {LANGUAGE_NAME} for a general audience, as Markdown with one # title. Base it on the paper and evidence below.
Structure: an everyday scene that opens the topic, plain analogies before technical terms, what the evidence shows and where it is uncertain, questions readers can ask, and a closing note that {note} (use that wording).
Any scene must be a fictional composite, not based on a real person. Length: 500-900 words, or 900-1500 characters in Chinese. Cite facts with [E#], and explain any number in plain language beside its citation. Output only the Markdown.""",
        "infographic": f"""Design a six-panel science infographic in {LANGUAGE_NAME}, keeping standard English technical terms. Base it on the paper and evidence below.
Return only one JSON object: {{{{"title":"...","panels":[{{{{"title":"short","stat":{{{{"value":"63.6%","label":"what it measures [E1]"}}}},"points":["short fact [E1]"],"chart":{{{{"title":"what the bars compare [E1]","unit":"%","bars":[{{{{"label":"short","value":63.6}}}}]}}}}}}}}]}}}}
Use exactly six panels with 2-3 short points each. A bar "value" is a bare number. Omit "stat" or "chart" when the evidence has no suitable figure; never invent chart data. Every figure must come from the evidence cited in that same field.""",
    }


class RunCancelled(Exception):
    pass


class BudgetError(Exception):
    pass


@dataclass
class ResearchRequest:
    topic: str
    passes: int = 2
    model: str = ""
    budget_usd: float = 5.0
    feedback: str = ""


@dataclass
class AskResult:
    output: str
    checks: List[Check] = field(default_factory=list)
    attempts: int = 0
    failed_checks: Set[str] = field(default_factory=set)
    error: str = ""

    @property
    def passed(self) -> bool:
        return bool(self.checks) and not self.error and all(c.passed for c in self.checks)


class ResearchRun:
    def __init__(self, request: ResearchRequest, on_log: Optional[Callable[[str], None]] = None):
        self.request = request
        self.run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        self.dir = RUNS_DIR / self.run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        RSI_DIR.mkdir(exist_ok=True)
        self.on_log = on_log or (lambda line: None)
        self.cancel_event = threading.Event()
        self.log_lines: List[str] = []
        self.status = "RUNNING"
        self.stage = "starting"
        self.spent = 0.0
        self.evidence: Dict[str, Evidence] = {}
        self._seen: Set[str] = set()
        self.source_status: Dict[str, SourceStatus] = {}
        self.dropped_for_privacy = 0
        self.passes_done: List[Dict] = []
        self.deliverables: List[Dict] = []
        self.citation_problems: List[str] = []
        self.promotions: List[Dict] = []
        self.candidate_rules: Dict[str, str] = {}
        self.error = ""
        self.started = time.time()
        self._texts: List[str] = []

    # ------------------------------------------------------------ records

    def log(self, line: str) -> None:
        stamped = f"[{time.strftime('%H:%M:%S')}] {line}"
        self.log_lines.append(stamped)
        self.on_log(stamped)
        self._save()

    def report(self) -> Dict:
        return {
            "run_id": self.run_id, "status": self.status, "stage": self.stage, "request": vars(self.request),
            "spent_usd": round(self.spent, 4), "elapsed_seconds": round(time.time() - self.started),
            "sources": [vars(s) for s in self.source_status.values()], "evidence_count": len(self.evidence),
            "dropped_for_privacy": self.dropped_for_privacy, "passes": self.passes_done, "deliverables": self.deliverables,
            "citation_problems": self.citation_problems, "promotions": self.promotions, "error": self.error, "log": self.log_lines[-200:],
        }

    def _save(self) -> None:
        temp = self.dir / "run_report.tmp"
        temp.write_text(json.dumps(self.report(), ensure_ascii=False, indent=1), encoding="utf-8")
        temp.replace(self.dir / "run_report.json")

    def _trace(self, node: str, status: str, error: str = "") -> None:
        # Names and outcomes only: never the prompts or source text, which may be sensitive.
        with open(RSI_DIR / "trace.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"run": self.run_id, "node": node, "status": status, "error": error[:300], "time": time.time()}, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------ model calls

    def _system(self) -> str:
        playbook = {}
        path = RSI_DIR / "playbook.json"
        if path.exists():
            playbook = json.loads(path.read_text(encoding="utf-8"))
        terms = CONFIG.get("terms", {}).get("preferred", {})
        lines = list(CONSTRAINTS) + list(playbook.values()) + list(self.candidate_rules.values())
        if terms:
            lines.append("Use these terms: " + "; ".join(f"{k} = {v}" for k, v in terms.items()) + ".")
        return CONFIG.get("writer_role", "You are a meticulous research writer.") + " Write only from the evidence supplied in the conversation.\n\nRules that always apply:\n" + "\n".join(f"- {l}" for l in lines)

    def _remaining(self) -> float:
        return self.request.budget_usd - self.spent

    def _guard(self) -> None:
        if self.cancel_event.is_set():
            raise RunCancelled()
        if self._remaining() <= 0.01:
            raise BudgetError(f"The ${self.request.budget_usd:.2f} budget is used up.")

    async def _ask(self, prompt: str, kind: Optional[str] = None, max_repairs: int = 1, model: Optional[str] = None,
                   system: Optional[str] = None, budget_share: float = 1.0) -> AskResult:
        """Ask, check with code, and send failures back in the same conversation."""
        self._guard()
        result = AskResult("")
        limit = max(0.01, self._remaining() * budget_share)
        async with llm.open_conversation(system or self._system(), model or self.request.model, limit) as chat:
            turn = prompt
            for attempt in range(1, max_repairs + 2):
                self._guard()
                result.attempts = attempt
                try:
                    reply = await chat.send(turn)
                except llm.ProviderError as e:
                    result.error = str(e)
                    self._trace(kind or "plan", "FAILED", result.error)
                    return result
                self.spent += reply.cost_usd
                result.output = reply.text
                if not kind:
                    return result
                result.checks = run_checks(kind, reply.text, self._check_evidence())
                failures = [c for c in result.checks if not c.passed]
                self._trace(kind, "FAILED" if failures else "COMPLETED", "; ".join(c.name for c in failures))
                if not failures:
                    return result
                result.failed_checks.update(c.name for c in failures)
                turn = "Your last answer failed these automated checks:\n" + "\n".join(f"- {c.name}: {c.message}" for c in failures) + "\n\nFix only these problems and keep everything else unchanged. Reply with the complete corrected answer."
        return result

    # ------------------------------------------------------------ evidence

    def _add_evidence(self, status: SourceStatus, items: List[Evidence]) -> int:
        previous = self.source_status.get(status.name)
        if previous and previous.state in ("LIVE", "FALLBACK", "SAVED") and status.state == "UNAVAILABLE":
            status = previous
        elif previous:
            status.items += previous.items
        self.source_status[status.name] = status
        added = 0
        for item in items:
            if len(self.evidence) >= MAX_EVIDENCE:
                break
            identity = item.identity()
            if identity in self._seen or not (item.title or item.text):
                continue
            self._seen.add(identity)
            if phi_hits(f"{item.title} {item.text} {item.authors}"):
                self.dropped_for_privacy += 1
                continue
            item.key = f"E{len(self.evidence) + 1}"
            self.evidence[item.key] = item
            added += 1
        return added

    def _collect(self, plan: Dict, first: bool) -> int:
        enabled = CONFIG.get("sources", {})
        topic = self.request.topic
        steps = []
        if first and enabled.get("reference_pdfs", True):
            steps.append(("Reference PDFs", sources.load_reference_pdfs))
        if enabled.get("pubmed", True) and (plan.get("pubmed") or first):
            steps.append(("Literature", lambda: sources.search_literature((plan.get("pubmed") or [topic])[:4], 6)))
        if enabled.get("arxiv", True) and plan.get("arxiv"):
            steps.append(("arXiv", lambda: sources.search_arxiv(plan["arxiv"][:2], 3)))
        if enabled.get("clinical_trials", False) and (plan.get("trials") or first):
            steps.append(("ClinicalTrials.gov", lambda: sources.search_trials((plan.get("trials") or [topic])[:2], 4)))
        if enabled.get("notebooklm_id") and plan.get("notebook"):
            steps.append(("NotebookLM", lambda: sources.query_notebook(plan["notebook"][:3])))
        if first and enabled.get("saved_answers", True):
            steps.append(("Saved answers", lambda: sources.load_saved_answers(plan.get("questions") or [], self.dir)))
        added = 0
        for name, fetch in steps:
            if self.cancel_event.is_set():
                raise RunCancelled()
            self.log(f"Collecting from {name}...")
            try:
                items, status = fetch()
            except Exception as e:
                items, status = [], SourceStatus(name, "UNAVAILABLE", 0, str(e)[:200])
            new = self._add_evidence(status, items)
            added += new
            self.log(f"  {name}: {status.state}, {new} new item(s). {status.detail}")
        return added

    def _pack(self, keys: Optional[List[str]] = None) -> str:
        chosen = [self.evidence[k] for k in keys] if keys else list(self.evidence.values())
        return "\n\n".join(f"[{e.key}] {e.kind}: {e.citation()}\n{e.text[:PACK_CHARS] or '(metadata only: no text available, so cite no figures from it)'}" for e in chosen)

    # ------------------------------------------------------------ RSI loop

    async def _plan(self) -> Dict:
        self.stage = "planning"
        self.log("Planning searches...")
        feedback = f"\nFeedback to act on: {self.request.feedback}" if self.request.feedback else ""
        prompt = (
            f'Research topic: {self.request.topic}{feedback}\n\nPlan literature searches. Return only JSON with these keys: '
            '"pubmed" (3-4 literature query strings), "arxiv" (1-2 short phrases), "trials" (1-2 short registry terms), '
            '"notebook" (2 questions for a curated notebook), "questions" (3 questions to ask an expert or specialist service).'
        )
        result = await self._ask(prompt)
        try:
            if result.error:
                raise ValueError(result.error)
            return json.loads(extract_json(result.output))
        except ValueError as e:
            self.log(f"Planning output unusable ({str(e)[:120]}); searching the topic directly.")
            return {"pubmed": [self.request.topic], "arxiv": [self.request.topic], "trials": [self.request.topic], "questions": [f"What is the current evidence on {self.request.topic}?"]}

    async def _research_loop(self) -> AskResult:
        plan = await self._plan()
        self._collect(plan, first=True)
        if not self.evidence:
            raise RuntimeError("No evidence could be collected from any source.")
        spec = _specs()["paper"].format(topic=self.request.topic)
        feedback = f"\n\nAct on this feedback: {self.request.feedback}" if self.request.feedback else ""
        best = AskResult("")
        for number in range(1, self.request.passes + 1):
            if number > 1 and self._remaining() < self.request.budget_usd * FINAL_RESERVE:
                self.log(f"Stopping before pass {number}: keeping the rest of the budget for the other deliverables.")
                break
            self.stage = f"RSI pass {number} of {self.request.passes}"
            added, instructions = 0, ""
            if number > 1:
                self.log("Critiquing the draft to find gaps...")
                critique = await self._ask(
                    f"You are the critical peer reviewer of this draft. Find what is missing or weak.\nTopic: {self.request.topic}\nFeedback: {self.request.feedback or 'none'}\n\nDRAFT:\n{best.output}\n\n"
                    'Return only JSON: {"gaps":["specific weakness"],"pubmed":["query to fill a gap"],"trials":["term"],"revisions":["specific instruction to the author"]}. Use empty lists when nothing important remains.'
                )
                try:
                    review = json.loads(extract_json(critique.output))
                except ValueError:
                    self.log("The critique was unusable; stopping the loop here.")
                    break
                gaps, revisions = review.get("gaps", []), review.get("revisions", [])
                self.passes_done[-1]["gaps_found"] = gaps
                if not gaps and not revisions and best.passed:
                    self.log("The reviewer found no remaining gaps; stopping early.")
                    break
                added = self._collect(review, first=False)
                instructions = "Revisions required:\n" + "\n".join(f"- {r}" for r in revisions + gaps)
                self.log(f"Pass {number}: {len(gaps)} gap(s), {added} new source(s).")
                for name in self.passes_done[-1]["failed_checks"]:
                    if name in RULES:
                        self.candidate_rules[RULES[name][0]] = RULES[name][1]
            if number == 1:
                prompt = f"{spec}{feedback}\n\nEVIDENCE:\n{self._pack()}"
            else:
                prompt = f"{spec}{feedback}\n\nRevise the draft below. Change only what the revisions require and keep all supported statements.\n{instructions}\n\nDRAFT:\n{best.output}\n\nEVIDENCE:\n{self._pack()}"
            self.log(f"Pass {number}: writing and checking the paper...")
            result = await self._ask(prompt, "paper", max_repairs=2)
            if result.output:
                best = result
            score = round(sum(c.score for c in result.checks) / max(1, len(result.checks)), 3)
            self.passes_done.append({
                "pass": number, "new_sources": added, "attempts": result.attempts, "failed_checks": sorted(result.failed_checks),
                "all_checks_passed": result.passed, "score": score, "checks": [c.to_dict() for c in result.checks],
                "spent_usd": round(self.spent, 4), "gaps_found": [], "error": result.error,
            })
            self.log(f"Pass {number}: {'all checks passed' if result.passed else 'checks still failing'}; score {score}, {result.attempts} attempt(s), ${self.spent:.2f} spent.")
            if result.error and not best.output:
                raise RuntimeError(result.error)
        self._evolve()
        return best

    def _evolve(self) -> None:
        """
        Keep a rule only on measured evidence: its check stopped failing in the pass that tested it
        (held-in) and overall fitness strictly rose (held-out). Every decision goes in a hash chain.
        """
        fitness = lambda p: 1 - len(p["failed_checks"]) / 4
        for earlier, later in zip(self.passes_done, self.passes_done[1:]):
            for name in earlier["failed_checks"]:
                if name not in RULES:
                    continue
                key, text = RULES[name]
                fixed = name not in later["failed_checks"]
                delta = round(fitness(later) - fitness(earlier), 3)
                decision = "PROMOTE" if fixed and delta > 0 else "REJECT"
                reason = "The failure stopped and fitness rose." if decision == "PROMOTE" else ("The failure continued." if not fixed else "Fitness did not rise.")
                if decision == "PROMOTE":
                    path = RSI_DIR / "playbook.json"
                    playbook = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
                    playbook[key] = text
                    path.write_text(json.dumps(playbook, ensure_ascii=False, indent=1), encoding="utf-8")
                self._ledger({"rule": key, "decision": decision, "delta_fitness": delta, "rationale": reason, "run": self.run_id})
                self.promotions.append({"rule": key, "decision": decision, "delta_fitness": delta, "rationale": reason})
                self.log(f"RSI rule {key}: {decision}. {reason}")

    @staticmethod
    def _ledger(entry: Dict) -> None:
        """Tamper-evident, not tamper-proof: anyone who can write the file can recompute the chain."""
        path = RSI_DIR / "ledger.jsonl"
        previous = "0" * 64
        if path.exists():
            lines = path.read_text(encoding="utf-8").splitlines()
            if lines:
                previous = json.loads(lines[-1])["hash"]
        entry = {**entry, "prev_hash": previous, "time": time.time()}
        entry["hash"] = hashlib.sha256(json.dumps(entry, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------ deliverables

    @staticmethod
    def _note(result: AskResult) -> str:
        problems = [c.message[:220] for c in result.checks if not c.passed]
        if result.error:
            problems.append(result.error[:220])
        return " ".join(problems) or render.label("verified_note")

    def _record(self, kind: str, result: AskResult, files: Dict[str, str], error: str = "") -> None:
        verified = result.passed and bool(files) and not error
        self.deliverables.append({"kind": kind, "verified": verified, "attempts": result.attempts, "files": files, "checks": [c.to_dict() for c in result.checks], "error": error or result.error})
        self.log(f"{kind}: {'verified' if verified else 'NEEDS REVIEW'} after {result.attempts} attempt(s). ${self.spent:.2f} spent.")

    def _check_evidence(self) -> Dict[str, Evidence]:
        return self.evidence

    def _spec(self, kind: str) -> str:
        return _specs()[kind]

    async def _make(self, kind: str, paper: str, build: Callable[[AskResult], Dict[str, str]], budget_share: float = 1.0) -> None:
        self.stage = f"writing {kind}"
        self.log(f"Writing the {kind}...")
        keys = [k for k in cited_keys(paper) if k in self.evidence]
        try:
            result = await self._ask(f"{self._spec(kind)}\n\nPAPER:\n{paper}\n\nEVIDENCE (cite only these keys):\n{self._pack(keys or None)}", kind, max_repairs=2, budget_share=budget_share)
        except BudgetError as e:
            self.deliverables.append({"kind": kind, "verified": False, "attempts": 0, "files": {}, "checks": [], "error": str(e)})
            self.log(f"{kind}: skipped. {e}")
            return
        if not result.output:
            self._record(kind, result, {}, result.error or "No output")
            return
        self._texts.append(result.output)
        try:
            self._record(kind, result, build(result))
        except Exception as e:
            self._record(kind, result, {}, f"Could not build the file: {e}")

    async def _make_deliverables(self, paper: AskResult) -> None:
        ev, out = self.evidence, self.dir
        self._record("paper", paper, render.render_document(paper.output, ev, out, "Academic_Paper", paper.passed, self._note(paper)))
        title = (re.search(r"^#\s+(.+)$", paper.output, re.M) or [None, self.request.topic])[1]
        wanted = CONFIG.get("deliverables", ["deck", "blog", "infographic"])
        if "deck" in wanted:
            await self._make("deck", paper.output, lambda r: {
                "html": render.render_deck_html(r.output, ev, out, "Interactive_Deck", r.passed, self._note(r)),
                "pptx": render.render_deck_pptx(r.output, ev, out, "Presentation", r.passed),
            })
        if "blog" in wanted:
            await self._make("blog", paper.output, lambda r: render.render_document(r.output, ev, out, "Blog_Post", r.passed, self._note(r)))
        if "infographic" in wanted:
            await self._make("infographic", paper.output, lambda r: render.render_infographic(r.output, ev, out, "Infographic", title, r.passed, self._note(r)))

    def _verify_citations(self, texts: List[str]) -> None:
        self.stage = "checking citations"
        self.log("Looking up every cited identifier online...")
        used = {k for text in texts for k in cited_keys(text)}
        for key in sorted(used, key=lambda k: int(k[1:])):
            item = self.evidence.get(key)
            if item:
                self.citation_problems.extend(sources.citation_problems(item))
        self.log(f"Citation lookup: {len(self.citation_problems)} problem(s) among {len(used)} cited sources.")

    # ------------------------------------------------------------ entry point

    async def execute(self) -> Dict:
        try:
            self.log(f"Run {self.run_id}: model {self.request.model}, up to {self.request.passes} pass(es), budget ${self.request.budget_usd:.2f}.")
            problem = llm.budget_problem()
            if problem:
                raise RuntimeError(problem)
            paper = await self._research_loop()
            if not paper.output:
                raise RuntimeError(paper.error or "No draft was produced.")
            await self._make_deliverables(paper)
            (self.dir / "evidence.json").write_text(json.dumps([e.to_dict() for e in self.evidence.values()], ensure_ascii=False, indent=1), encoding="utf-8")
            self._verify_citations([paper.output] + self._texts)
            wanted = 1 + len(CONFIG.get("deliverables", ["deck", "blog", "infographic"]))
            complete = len(self.deliverables) == wanted and all(d["verified"] for d in self.deliverables)
            self.status = "COMPLETED" if complete and not self.citation_problems else "NEEDS_REVIEW"
        except RunCancelled:
            self.status = "CANCELLED"
            self.log("Run cancelled.")
        except Exception as e:
            self.status = "FAILED"
            self.error = str(e)[:500]
            self.log(f"Stopped: {self.error}")
        self.stage = "finished"
        self.log(f"Finished: {self.status}. Spent ${self.spent:.2f} in {round(time.time() - self.started)}s.")
        return self.report()


def list_runs(limit: int = 12) -> List[Dict]:
    runs = []
    if RUNS_DIR.exists():
        for folder in sorted(RUNS_DIR.iterdir(), reverse=True):
            report = folder / "run_report.json"
            if report.exists():
                try:
                    data = json.loads(report.read_text(encoding="utf-8"))
                except ValueError:
                    continue
                data.pop("log", None)
                runs.append(data)
            if len(runs) >= limit:
                break
    return runs
