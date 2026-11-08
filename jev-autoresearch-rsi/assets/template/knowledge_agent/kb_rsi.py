"""
Self-improvement of the knowledge base.

Fitness is computed by code from the files, never by a model. A proposed change is tried on a copy of the
KB; it is promoted to the real KB only when its own metric improves and the overall score rises without any
other metric getting worse. Every decision is appended to a SHA-256 chained ledger.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from . import kb

# score = 1 - sum(weight * count / (count + K)). Each term rises strictly with its count, so any rise lowers
# the score; a perfect KB (all counts 0) scores exactly 1.0; an empty KB (0 pages) scores 0.
WEIGHTS = {"broken_links": 0.30, "unsourced_claims": 0.25, "orphans": 0.20,
           "duplicate_concepts": 0.10, "single_source_concepts": 0.10, "open_gaps": 0.05}
SATURATION = 5.0
LEDGER_START = "0" * 64
HEADING_RE = re.compile(r"^#{1,6}\s")
CLAIMS_HEADING_RE = re.compile(r"^#{1,6}\s*Claims\b")
SOURCE_LINK_RE = re.compile(r"\[\[" + kb.SOURCE_DIR + r"/([^\]|#]+)")


def _score(counts: Dict[str, int]) -> float:
    return round(1.0 - sum(w * counts[k] / (counts[k] + SATURATION) for k, w in WEIGHTS.items()), 6)


def claim_lines(text: str) -> List[str]:
    """Bullet lines under a 'Claims' heading inside the managed block."""
    block = kb.get_block(text)
    if block is None:
        return []
    out, inside = [], False
    for line in block.splitlines():
        if CLAIMS_HEADING_RE.match(line):
            inside = True
        elif HEADING_RE.match(line):
            inside = False
        elif inside and re.match(r"^\s*[-*]\s+\S", line):
            out.append(line.strip())
    return out


def fitness(root: Path) -> dict:
    root = Path(root)
    pages = kb.iter_md(root)
    zero = {k: 0 for k in WEIGHTS}
    if not pages:
        return {"pages": 0, "broken_links": 0, "orphans": 0, "unsourced_claims": 0, "open_gaps": 0, "concepts": 0,
                "single_source_concepts": 0, "duplicate_concepts": 0, "score": 0.0,
                "details": {"broken": [], "orphans": [], "unsourced": [], "duplicates": []}}
    texts = {pid: kb.read_text(p) for pid, p in pages}
    by_cf = {pid.casefold(): pid for pid in texts}
    inbound: Dict[str, set] = {pid: set() for pid in texts}
    broken, seen = [], set()
    for pid, text in texts.items():
        for t in kb.wikilinks(text):
            target = by_cf.get(t.casefold())
            if target:
                if target != pid:
                    inbound[target].add(pid)
            elif (pid, t) not in seen and not _file_exists(root, t):
                seen.add((pid, t))
                broken.append({"page": pid, "target": t})
    redirects = {pid for pid, t in texts.items() if kb.is_redirect(t)}
    orphans = [pid for pid in texts if pid != "index" and pid != kb.GAPS_ID and pid not in redirects and not inbound[pid]]
    concepts = {pid: t for pid, t in texts.items() if pid.startswith(kb.CONCEPT_DIR + "/") and pid not in redirects}
    unsourced, single = [], 0
    for pid, text in concepts.items():
        claims = claim_lines(text)
        for line in claims:
            if not SOURCE_LINK_RE.search(line):
                unsourced.append({"page": pid, "claim": line})
        if claims and len({s for line in claims for s in SOURCE_LINK_RE.findall(line)}) == 1:
            single += 1
    duplicates = _duplicate_pairs(concepts)
    counts = {"broken_links": len(broken), "unsourced_claims": len(unsourced), "orphans": len(orphans),
              "duplicate_concepts": len(duplicates), "single_source_concepts": single, "open_gaps": len(kb.open_gaps(root))}
    return {"pages": len(texts), **counts, "concepts": len(concepts), "score": _score(counts),
            "details": {"broken": broken, "orphans": orphans, "unsourced": unsourced, "duplicates": duplicates}}


def _file_exists(root: Path, target: str) -> bool:
    if not Path(target).suffix:
        return False
    try:
        return (root / target).is_file()
    except (OSError, ValueError):
        return False


def _duplicate_pairs(concepts: Dict[str, str]) -> List[dict]:
    """Mergeable pairs: equal normalized names or ratio >= 0.92; keep the page with more claims."""
    mergeable = sorted(pid for pid, t in concepts.items() if "claims" in kb.load_state(t))
    names = {pid: kb.norm_name(pid.split("/", 1)[1]) for pid in mergeable}
    out = []
    for i, a in enumerate(mergeable):
        for b in mergeable[i + 1:]:
            ratio = 1.0 if names[a] == names[b] else difflib.SequenceMatcher(None, names[a], names[b]).ratio()
            if ratio >= 0.92:
                ca, cb = len(kb.load_state(concepts[a]).get("claims", [])), len(kb.load_state(concepts[b]).get("claims", []))
                keep, drop = (a, b) if ca >= cb else (b, a)
                out.append({"keep": keep, "drop": drop, "ratio": round(ratio, 3)})
    return out


# ------------------------------------------------------------------ proposals

@dataclass
class Proposal:
    kind: str       # "repair_link" | "merge_concepts" | "link_orphan"
    target: str
    detail: dict = field(default_factory=dict)
    metric: str = ""


def _closest(target: str, ids: List[str]) -> Optional[str]:
    folder, _, base = target.rpartition("/")
    want = kb.norm_name(base)
    best = None
    for pid in ids:
        d, _, b = pid.rpartition("/")
        if pid.casefold() == target.casefold() or (folder and d.casefold() != folder.casefold()):
            continue
        r = difflib.SequenceMatcher(None, want, kb.norm_name(b)).ratio()
        if r >= 0.85 and (best is None or r > best[0] or (r == best[0] and pid < best[1])):
            best = (r, pid)
    return best[1] if best else None


def propose(root: Path) -> List[Proposal]:
    root = Path(root)
    f = fitness(root)
    ids = [pid for pid, _ in kb.iter_md(root)]
    out: List[Proposal] = []
    groups: Dict[str, List[str]] = {}
    for b in f["details"]["broken"]:
        groups.setdefault(b["target"], []).append(b["page"])
    for target in sorted(groups):
        new = _closest(target, ids)
        if new:
            out.append(Proposal("repair_link", target, {"new": new, "pages": sorted(set(groups[target]))}, "broken_links"))
    for d in sorted(f["details"]["duplicates"], key=lambda d: (d["drop"], d["keep"])):
        out.append(Proposal("merge_concepts", d["drop"], {"keep": d["keep"], "ratio": d["ratio"]}, "duplicate_concepts"))
    for pid in sorted(f["details"]["orphans"]):
        out.append(Proposal("link_orphan", pid, {}, "orphans"))
    return out


def _rewrite_links(root: Path, old: str, new: str, pages: List[str]) -> List[str]:
    """Point every `[[old...]]` in `pages` at `new`, keeping aliases and headings."""
    touched = []
    want = old.casefold()

    def sub(m):
        inner = m.group(1)
        if kb.link_target(inner).casefold() != want:
            return m.group(0)
        rest = re.search(r"[|#].*$", inner)
        return "[[" + new + (rest.group(0) if rest else "") + "]]"

    for pid in pages:
        path = root / (pid + ".md")
        if not path.is_file():
            continue
        text = kb.read_text(path)
        inner = kb.get_block(text)
        if inner is None:
            continue  # Only code-owned text is rewritten; user text outside the markers stays byte-for-byte.
        new_inner = kb.LINK_RE.sub(sub, inner)
        updated = text.replace(kb.BEGIN + inner + kb.END, kb.BEGIN + new_inner + kb.END, 1)
        if updated != text:
            kb.write_text(path, updated)
            touched.append(pid + ".md")
    return touched


def apply(root: Path, proposal: Proposal) -> List[str]:
    root = Path(root)
    kind, d = proposal.kind, proposal.detail
    if kind == "repair_link":
        new = d.get("new", "")
        if not new or not (root / (new + ".md")).is_file():
            raise ValueError(f"repair target does not exist: {new!r}")
        return _rewrite_links(root, proposal.target, new, list(d.get("pages") or []))
    if kind == "link_orphan":
        if not (root / (proposal.target + ".md")).is_file():
            raise ValueError(f"orphan page does not exist: {proposal.target}")
        return kb.add_unlinked(root, proposal.target)
    if kind == "merge_concepts":
        return _merge(root, d.get("keep", ""), proposal.target)
    raise ValueError(f"unknown proposal kind: {kind}")


def _merge(root: Path, keep: str, drop: str) -> List[str]:
    kp, dp = root / (keep + ".md"), root / (drop + ".md")
    if keep == drop or not kp.is_file() or not dp.is_file():
        raise ValueError("both concept pages must exist and differ")
    ktext, dtext = kb.read_text(kp), kb.read_text(dp)
    ks, ds = kb.load_state(ktext), kb.load_state(dtext)
    if "claims" not in ks or "claims" not in ds:
        raise ValueError("concept pages without managed state cannot be merged")
    own = {kb.norm_name(ks.get("name", "")), kb.norm_name(ds.get("name", ""))}
    ks["claims"] = kb._merge_claims(ks["claims"], ds["claims"])
    ks["related"] = [r for r in kb._merge_names(ks.get("related", []), ds.get("related", [])) if kb.norm_name(r) not in own]
    ks["topics"] = kb._merge_names(ks.get("topics", []), ds.get("topics", []))
    ks["run_ids"] = list(dict.fromkeys(ks.get("run_ids", []) + ds.get("run_ids", [])))
    ks["aliases"] = kb._merge_names(ks.get("aliases", []), [ds.get("name", drop.split("/", 1)[1])])
    kb.write_text(kp, kb.set_block(ktext, kb.render_concept(ks, kb.Ctx(root))))
    redirect = "\n".join([kb.dump_state({"redirect": keep, "name": ds.get("name", "")}), kb.REDIRECT_MARK, f"See [[{keep}]]"])
    kb.write_text(dp, kb.set_block(dtext, redirect))
    others = [pid for pid, _ in kb.iter_md(root) if pid != drop]
    touched = [keep + ".md", drop + ".md"] + _rewrite_links(root, drop, keep, others)
    return list(dict.fromkeys(touched))


# ------------------------------------------------------------------ ledger

def _digest(entry: dict) -> str:
    return hashlib.sha256(json.dumps(entry, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _lines(ledger: Path) -> List[str]:
    ledger = Path(ledger)
    return [l for l in ledger.read_bytes().decode("utf-8").splitlines() if l.strip()] if ledger.exists() else []


def append_ledger(ledger: Path, entry: dict) -> dict:
    """Tamper-evident, not tamper-proof: anyone who can write the file can recompute the chain."""
    ledger = Path(ledger)
    lines = _lines(ledger)
    previous = LEDGER_START
    if lines:
        try:
            previous = json.loads(lines[-1])["hash"]
        except (ValueError, KeyError, TypeError):
            previous = _digest({"unreadable": lines[-1]})
    entry = {**entry, "prev_hash": previous}
    entry["hash"] = _digest(entry)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def ledger_entries(ledger: Path, limit: int = 100) -> List[dict]:
    out = []
    for line in reversed(_lines(ledger)):
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
        if len(out) >= limit:
            break
    return out


def verify_ledger(ledger: Path) -> bool:
    previous = LEDGER_START
    for line in _lines(ledger):
        try:
            entry = json.loads(line)
            claimed = entry.pop("hash")
        except (ValueError, KeyError, AttributeError):
            return False
        if entry.get("prev_hash") != previous or _digest(entry) != claimed:
            return False
        previous = claimed
    return True


# ------------------------------------------------------------------ the improvement loop

def _key(p: Proposal) -> str:
    return json.dumps([p.kind, p.target, p.detail], sort_keys=True, ensure_ascii=False)


def _evaluate(root: Path, p: Proposal, before: dict) -> dict:
    """Try the proposal on a copy and decide. Held-in: its own metric falls. Held-out: score rises, nothing else worsens."""
    metric = p.metric
    decision = {"kind": p.kind, "target": p.target, "decision": "REJECT", "metric": metric, "before": before.get(metric),
                "after": before.get(metric), "delta_score": 0.0, "reason": "", "time": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if metric not in WEIGHTS:
        decision["reason"] = f"unknown metric {metric!r}"
        return decision
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "kb"
        shutil.copytree(root, work)
        try:
            apply(work, p)
        except Exception as e:  # a failed proposal is a rejected proposal, never a crash
            decision["reason"] = f"apply failed: {e}"
            return decision
        after = fitness(work)
    delta = round(after["score"] - before["score"], 6)
    decision.update(after=after[metric], delta_score=delta)
    worse = [k for k in WEIGHTS if k != metric and after[k] > before[k]]
    if not after[metric] < before[metric]:
        decision["reason"] = f"{metric} did not fall ({before[metric]} -> {after[metric]})"
    elif not delta > 1e-9:
        decision["reason"] = f"score did not rise ({before['score']} -> {after['score']})"
    elif worse:
        decision["reason"] = "held-out metric got worse: " + ", ".join(f"{k} {before[k]} -> {after[k]}" for k in worse)
    else:
        decision["decision"] = "PROMOTE"
        decision["reason"] = f"{metric} {before[metric]} -> {after[metric]}; score {before['score']} -> {after['score']}"
    return decision


def improve(root: Path, ledger: Path, queue_md: Optional[Path] = None, max_proposals: int = 20) -> List[dict]:
    root = Path(root)
    decisions: List[dict] = []
    tried = set()
    while len(decisions) < max_proposals:
        candidates = [p for p in propose(root) if _key(p) not in tried]
        if not candidates:
            break
        p = candidates[0]
        tried.add(_key(p))
        decision = _evaluate(root, p, fitness(root))
        if decision["decision"] == "PROMOTE":
            try:
                apply(root, p)
            except Exception as e:
                decision.update(decision="REJECT", reason=f"apply to the real KB failed: {e}")
        append_ledger(ledger, {**decision, "detail": p.detail})
        if queue_md is not None:
            queue_md = Path(queue_md)
            if queue_md.exists() or queue_md.parent.exists():
                line = (f"- {decision['time'][:10]} {decision['decision']} {p.kind} {p.target} "
                        f"Δscore={decision['delta_score']:+.3f} — {decision['reason']}\n")
                with open(queue_md, "ab") as f:
                    f.write(line.encode("utf-8"))
        decisions.append(decision)
    return decisions
