"""
Robin layer (Ghareeb et al., 2026, Nature; multi_agent_research_skill v2.7), adapted to a literature agent.

- Crow/Falcon split: a code-built citation library, then a synthesis that may cite only that library.
  A hallucination guard (code) accepts a claim only if it cites an on-topic, identifier-verified entry and
  its figures appear in the cited sources.
- BTL tournament: candidate hypotheses are ranked from pairwise judgements, never from absolute 1-10 scores.
- Parallel trajectories: K independent syntheses; a claim survives only if enough trajectories agree.
- ReAct self-healing with a cascade guard: helpers to name and diagnose repeated identical errors.

Everything here is pure and deterministic given its inputs (and a seed), so code, not a model, decides.
See docs/adr/0002-robin-layer.md for what maps to what, and what is deliberately not implemented (Finch).
"""

from __future__ import annotations

import csv
import io
import math
import random
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .checks import check_claim_numbers
from .sources import Evidence

HALLUCINATION_TARGET = 0.02      # Robin scoreboard metric 10: at most 2 % unverified claims
MIN_CANDIDATES = 3               # pitfall 51: fewer than 3 candidates means no tournament
PAIRINGS_PER_CANDIDATE = 4
CONSENSUS_RANGE = (0.5, 0.75)    # pitfall 52: 1.0 yields nothing; 0.75 is the high-stakes ceiling
TRAJECTORY_CHOICES = (1, 3, 5, 8)
REACT_MAX_ITERATIONS = 4         # Robin uses 12 for code cells; JSON repairs converge or cascade much sooner
CASCADE_REPEATS = 3              # stop after 3 consecutive identical errors
MATCH_JACCARD = 0.4
CLAIM_TYPES = ("literature", "hypothesis", "unsupported", "derived", "simulated", "observed")
ALLOWED_HERE = {"literature", "hypothesis", "unsupported"}  # nothing is measured in a literature run
CITE_RE = re.compile(r"\[E\d+(?:\s*,\s*E\d+)*\]")

STOP = set("""a an the and or of in on for to with by from at as is are was were be been being this that these those it its
than then into over under between within without about across after before during per via not no nor but if so such
can could may might will would should shall do does did done has have had their there which who whom whose what when where
while also more most less least very much many some any each other both all only own same study studies paper papers
report reported reports shows show showed shown found find finds using used use based new one two three""".split())


# ---------------------------------------------------------------- Crow: the citation library

def is_verified(e: Evidence) -> bool:
    """An entry is verified when a registry identifier came back from the API with a title; never from model recall."""
    return bool((e.doi or e.pmid or e.arxiv_id or e.nct_id) and e.title.strip())


def citation_library(evidence: Dict[str, Evidence], off_topic: Iterable[str]) -> List[Dict]:
    off = set(off_topic)
    rows = []
    for key, e in evidence.items():
        rows.append({
            "citation_id": key, "title": e.title, "kind": e.kind, "year": e.year,
            "doi": e.doi, "pmid": e.pmid, "arxiv_id": e.arxiv_id, "nct_id": e.nct_id,
            "abstract": (e.text or "")[:600], "verified": is_verified(e), "on_topic": key not in off,
        })
    return rows


# ---------------------------------------------------------------- Falcon: synthesis + hallucination guard

FALCON_SYSTEM = (
    "You are Falcon, a high-tier evidence synthesiser. You have no retrieval tools: you may use only the citation library "
    "given in the message, never your memory of the literature. Every claim must list the library ids it rests on. "
    "Copy figures exactly. Output one JSON object only."
)


def falcon_prompt(topic: str, pack: str, rejected: Optional[List[Dict]] = None) -> str:
    redo = ""
    if rejected:
        redo = ("\nA code guard rejected these claims from your previous attempt; do not repeat them unless you can cite "
                "a library id whose text supports them:\n" + "\n".join(f"- {r['claim'][:200]} ({r['reason']})" for r in rejected[:15]) + "\n")
    return (
        f"Topic: {topic}\n{redo}\nCITATION LIBRARY:\n{pack}\n\n"
        'Return only JSON: {"claims": [{"claim": "one atomic, checkable statement; copy any figure exactly", '
        '"evidence_ids": ["E#"], "claim_type": "literature"}]}. '
        "Give 6-14 claims that together answer the topic, strongest evidence first. Cite only ids shown above."
    )


def strip_cites(text: str) -> str:
    return re.sub(r"\s+", " ", CITE_RE.sub("", str(text or ""))).strip()


def guard_claims(raw, evidence: Dict[str, Evidence], usable: set, verified: set) -> Tuple[List[Dict], List[Dict], Dict]:
    """The guard decides. A claim is accepted only if every rule holds; otherwise it is logged with the reason."""
    accepted: List[Dict] = []
    rejected: List[Dict] = []
    seen: set = set()
    items = raw if isinstance(raw, list) else []
    for item in items:
        if not isinstance(item, dict):
            rejected.append({"claim": str(item)[:200], "evidence_ids": [], "reason": "not a claim object"})
            continue
        text = strip_cites(item.get("claim", ""))
        ids = [str(k).strip() for k in item.get("evidence_ids") or [] if str(k).strip()]
        known = list(dict.fromkeys(k for k in ids if k in usable))
        reason = ""
        if not text:
            reason = "empty claim"
        elif len(text) > 500:
            reason = "claim longer than 500 characters"
        elif not ids:
            reason = "no evidence_ids"
        elif not known:
            reason = "cites no on-topic library entry"
        elif not any(k in verified for k in known):
            reason = "cites no identifier-verified entry"
        elif not check_claim_numbers(text, known, evidence).passed:
            reason = "a figure is not in the cited sources"
        elif text.lower() in seen:
            reason = "duplicate claim"
        if reason:
            rejected.append({"claim": text[:500], "evidence_ids": ids, "reason": reason})
            continue
        seen.add(text.lower())
        accepted.append({"claim": text, "evidence_ids": known, "claim_type": "literature"})
    total = len(accepted) + len(rejected)
    stats = {"total_claims": total, "unverified_claims": len(rejected), "hallucination_rate": round(len(rejected) / total, 4) if total else 0.0}
    return accepted, rejected, stats


# ---------------------------------------------------------------- parallel trajectories: consensus

def tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9.\-%]*", text.lower()) if len(w) > 2 and w not in STOP}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def same_finding(a: Dict, b: Dict) -> bool:
    return bool(set(a["evidence_ids"]) & set(b["evidence_ids"])) and jaccard(tokens(a["claim"]), tokens(b["claim"])) >= MATCH_JACCARD


def check_threshold(threshold: float) -> None:
    low, high = CONSENSUS_RANGE
    if not low <= threshold <= high:
        raise ValueError(f"Consensus threshold must be between {low} and {high} (1.0 leaves no findings).")


def consensus(trajectories: Sequence[List[Dict]], threshold: float) -> Dict:
    """Cluster accepted claims across trajectories; keep a cluster if the share of trajectories in it ≥ threshold."""
    check_threshold(threshold)
    k = len(trajectories)
    clusters: List[Dict] = []
    for t, claims in enumerate(trajectories):
        for claim in claims:
            home = next((c for c in clusters if any(same_finding(claim, m) for m in c["members"])), None)
            if home is None:
                home = {"members": [], "trajectories": set()}
                clusters.append(home)
            home["members"].append(claim)
            home["trajectories"].add(t)
    included, excluded, matrix = [], [], []
    for i, c in enumerate(clusters, 1):
        agreement = round(len(c["trajectories"]) / k, 3) if k else 0.0
        lead = max(c["members"], key=lambda m: (len(m["evidence_ids"]), len(m["claim"])))
        ids = list(dict.fromkeys(e for m in c["members"] for e in m["evidence_ids"]))
        row = {"finding_id": f"F{i}", "claim": lead["claim"], "evidence_ids": ids, "agreement": agreement, "claim_type": "literature"}
        matrix.append({"finding_id": row["finding_id"], "votes": [1 if t in c["trajectories"] else 0 for t in range(k)]})
        (included if agreement >= threshold else excluded).append(row)
    return {"threshold": threshold, "trajectories": k, "included": included, "excluded": excluded, "matrix": matrix}


# ---------------------------------------------------------------- hypotheses (Phase 2 ideas)

HYPOTHESIS_SYSTEM = (
    "You are the high-tier hypothesis generator. From verified claims only, propose new, testable research hypotheses "
    "that the evidence suggests but does not settle. They are proposals, not findings. Output one JSON object only."
)


def hypotheses_prompt(topic: str, claims: List[Dict], n: int) -> str:
    lines = "\n".join(f"- {c['claim']} [{', '.join(c['evidence_ids'])}]" for c in claims[:24]) or "- (no verified claims)"
    return (
        f"Topic: {topic}\n\nVERIFIED CLAIMS (each checked by code against its sources):\n{lines}\n\n"
        f'Return only JSON: {{"hypotheses": [{{"id": "H1", "statement": "one falsifiable sentence", '
        f'"rationale": "why the claims point to it", "evidence_ids": ["E#"], "test": "the study or analysis that would test it"}}]}}. '
        f"Give exactly {n} distinct hypotheses. Cite only ids shown above. Copy any figure exactly; prefer none."
    )


def validate_hypotheses(raw, evidence: Dict[str, Evidence], usable: set) -> Tuple[List[Dict], List[Dict]]:
    kept: List[Dict] = []
    rejected: List[Dict] = []
    seen: set = set()
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        statement = strip_cites(item.get("statement", ""))
        rationale = strip_cites(item.get("rationale", ""))
        test = strip_cites(item.get("test", ""))
        ids = list(dict.fromkeys(str(k).strip() for k in item.get("evidence_ids") or [] if str(k).strip() in usable))
        reason = ""
        if not statement or len(statement) > 400:
            reason = "statement missing or longer than 400 characters"
        elif not ids:
            reason = "cites no on-topic library entry"
        elif not check_claim_numbers(statement + "\n" + rationale, ids, evidence).passed:
            reason = "a figure is not in the cited sources"
        elif statement.lower() in seen:
            reason = "duplicate"
        if reason:
            rejected.append({"statement": statement[:400], "reason": reason})
            continue
        seen.add(statement.lower())
        kept.append({"id": f"H{len(kept) + 1}", "statement": statement, "rationale": rationale[:600], "test": test[:400], "evidence_ids": ids})
    return kept, rejected


# ---------------------------------------------------------------- BTL tournament

JUDGE_SYSTEM = (
    "You are an independent judge in a pairwise tournament. You compare exactly two candidate hypotheses and pick the "
    "stronger one. The order in which they are shown carries no information. Output one JSON object only."
)

LINT = [re.compile(p, re.I) for p in (r"\bscore", r"\brat(e|ing)s?\b", r"\b1\s*[-–—]\s*10\b", r"out of 10")]


def lint_judge(text: str) -> List[str]:
    """Pitfall 54: absolute-scale wording in a BTL judge prompt brings back the bias the tournament removes."""
    return [p.pattern for p in LINT if p.search(text)]


def judge_prompt(topic: str, a: Dict, b: Dict, context: str) -> str:
    show = lambda h: f"Statement: {h['statement']}\nRationale: {h['rationale']}\nTest: {h['test']}\nCites: {', '.join(h['evidence_ids'])}"
    return (
        f"Topic: {topic}\n\nSUPPORTING EVIDENCE:\n{context}\n\nCANDIDATE A\n{show(a)}\n\nCANDIDATE B\n{show(b)}\n\n"
        "Which candidate is the stronger research hypothesis? Prefer, in this order: better support from the cited evidence, "
        "a sharper and more falsifiable statement, a feasible test, and novelty beyond what the evidence already settles. "
        'Return only JSON: {"winner": "A" | "B" | "tie", "reason": "one sentence"}.'
    )


def schedule_pairings(n: int, per: int = PAIRINGS_PER_CANDIDATE, seed: int = 0) -> List[Tuple[int, int]]:
    """`per` rounds of a random perfect matching; with an odd count the spare plays a random other. Every candidate gets ≥ per games."""
    if n < 2:
        return []
    rng = random.Random(seed)
    pairs: List[Tuple[int, int]] = []
    seen: set = set()
    for _ in range(per):
        best, best_repeats = None, None
        for _attempt in range(20):  # prefer a round with fewest repeated pairs
            order = list(range(n))
            rng.shuffle(order)
            round_pairs = [(order[i], order[i + 1]) for i in range(0, n - 1, 2)]
            if n % 2:
                spare = order[-1]
                round_pairs.append((spare, rng.choice([x for x in range(n) if x != spare])))
            repeats = sum(1 for p in round_pairs if frozenset(p) in seen)
            if best is None or repeats < best_repeats:
                best, best_repeats = round_pairs, repeats
            if repeats == 0:
                break
        for p in best:
            seen.add(frozenset(p))
            pairs.append(p if rng.random() < 0.5 else (p[1], p[0]))  # randomise which side is shown as A
    return pairs


def fit_btl(n: int, results: List[Tuple[int, int, float]], iterations: int = 2000, tol: float = 1e-10) -> Tuple[List[float], List[float], List[int]]:
    """
    Bradley-Terry-Luce maximum likelihood by the MM algorithm (Hunter, 2004).
    `results` holds (i, j, outcome): 1.0 = i beat j, 0.0 = j beat i, 0.5 = tie (half a win each).
    A weak prior (one drawn game against a reference of strength 1) keeps every estimate finite.
    Returns (btl_score = ln strength, relative to the reference; win_rate; games played).
    """
    p = [1.0] * n
    wins = [0.5] * n
    games = [0] * n
    for i, j, o in results:
        wins[i] += o
        wins[j] += 1.0 - o
        games[i] += 1
        games[j] += 1
    for _ in range(iterations):
        new = []
        for i in range(n):
            denom = 1.0 / (p[i] + 1.0)
            for a, b, _o in results:
                if a == i:
                    denom += 1.0 / (p[i] + p[b])
                elif b == i:
                    denom += 1.0 / (p[i] + p[a])
            new.append(wins[i] / denom)
        change = max(abs(x - y) for x, y in zip(new, p))
        p = new
        if change < tol:
            break
    rates = [round((wins[i] - 0.5) / games[i], 3) if games[i] else 0.0 for i in range(n)]
    return [round(math.log(x), 3) for x in p], rates, games


def counterbalance(games: List[Tuple[int, int, int, float]]) -> List[Tuple[int, int, float]]:
    """
    `games` holds (pairing_id, i, j, outcome for i). Both orders of one pairing share a pairing_id and are merged into
    one result: the mean outcome from the lower-index candidate's side. Consistent verdicts keep their value; a verdict
    that flips with the order (pure position preference) becomes a tie. A pairing with one surviving order keeps it.
    """
    merged: Dict[int, Tuple[int, int, List[float]]] = {}
    for pid, i, j, o in games:
        lo, hi = min(i, j), max(i, j)
        merged.setdefault(pid, (lo, hi, []))[2].append(o if i == lo else 1.0 - o)
    return [(lo, hi, sum(v) / len(v)) for _, (lo, hi, v) in sorted(merged.items())]


def position_a_share(winners: List[str]) -> Optional[float]:
    """Share of decisive games won by whichever candidate was shown first. About 0.5 means no position preference."""
    decisive = [w for w in winners if w in ("A", "B")]
    return round(sum(w == "A" for w in decisive) / len(decisive), 3) if decisive else None


def rank_candidates(candidates: List[Dict], results: List[Tuple[int, int, float]]) -> List[Dict]:
    scores, rates, games = fit_btl(len(candidates), results)
    order = sorted(range(len(candidates)), key=lambda i: (-scores[i], -rates[i], i))
    return [{**candidates[i], "rank": r, "btl_score": scores[i], "win_rate": rates[i], "games": games[i]} for r, i in enumerate(order, 1)]


# ---------------------------------------------------------------- ReAct cascade guard

def error_signature(error: str) -> str:
    """Two errors are 'identical' when they match after numbers and quoted fragments are removed."""
    text = re.sub(r"'[^']*'|\"[^\"]*\"", "''", str(error).lower())
    return re.sub(r"\d+", "#", text).strip()[:160]


def is_cascade(errors: List[str], repeats: int = CASCADE_REPEATS) -> bool:
    return len(errors) >= repeats and len({error_signature(e) for e in errors[-repeats:]}) == 1


def diagnose(error: str) -> str:
    e = str(error).lower()
    if "json" in e or "expecting" in e or "delimiter" in e:
        return "Output is not parseable JSON; the model keeps adding prose or truncating. Tighten the format instruction or raise the output limit."
    if "missing" in e or "key" in e or "field" in e:
        return "Likely schema mismatch: verify field names in the prompt before retrying."
    if "need" in e or "only" in e:
        return "The model cannot meet a count or evidence requirement from this evidence; consider lowering the requirement or adding evidence."
    return "The same error repeated; escalate to a human or a different model instead of retrying."


# ---------------------------------------------------------------- claim ledger, status, QC

LEDGER_FIELDS = ["claim_id", "claim_type", "claim", "evidence_ids", "artifact_path", "verified", "source_node", "note"]


def ledger_rows(findings: List[Dict], rejected: List[Dict], ranked: List[Dict]) -> List[Dict]:
    rows = []
    for i, f in enumerate(findings, 1):
        rows.append({"claim_id": f"L{i}", "claim_type": "literature", "claim": f["claim"], "evidence_ids": " ".join(f["evidence_ids"]),
                     "artifact_path": "robin/evidence_report.json", "verified": "true", "source_node": "falcon",
                     "note": f"agreement {f['agreement']}" if "agreement" in f else ""})
    for i, r in enumerate(rejected, 1):
        rows.append({"claim_id": f"U{i}", "claim_type": "unsupported", "claim": r["claim"], "evidence_ids": " ".join(r.get("evidence_ids") or []),
                     "artifact_path": "robin/evidence_report.json", "verified": "false", "source_node": "falcon guard", "note": r["reason"]})
    for h in ranked:
        rows.append({"claim_id": h["id"], "claim_type": "hypothesis", "claim": h["statement"], "evidence_ids": " ".join(h["evidence_ids"]),
                     "artifact_path": "robin/ranked_candidates.json", "verified": "false", "source_node": "tournament",
                     "note": f"rank {h.get('rank', '-')}, btl {h.get('btl_score', '-')}"})
    return rows


def ledger_csv(rows: List[Dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=LEDGER_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def ledger_problems(rows: List[Dict], evidence_keys: set) -> List[str]:
    problems = []
    for r in rows:
        if r["claim_type"] not in ALLOWED_HERE:
            problems.append(f"{r['claim_id']}: claim_type {r['claim_type']} is not allowed in a literature run (nothing was measured)")
        if r["claim_type"] == "literature":
            ids = r["evidence_ids"].split()
            if not ids or any(k not in evidence_keys for k in ids):
                problems.append(f"{r['claim_id']}: literature claim cites a key that was not collected")
        if not r["artifact_path"]:
            problems.append(f"{r['claim_id']}: no artifact_path")
    return problems


def robin_status(verified_claims: int, final_rate: float) -> str:
    if verified_claims == 0:
        return "DATA_UNAVAILABLE"
    if final_rate > HALLUCINATION_TARGET:
        return "FAILED_REPRODUCIBILITY"
    return "PROPOSAL_ONLY"  # AI_SCIENTIST_PASS needs executed analysis (Finch), which this engine does not run
