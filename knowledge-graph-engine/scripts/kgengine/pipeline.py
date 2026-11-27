"""Construction pipeline: ingest -> extract (NER+RE) -> resolve (ER) -> summarize.

Follows the claude-cookbooks knowledge_graph guide, hardened for a real corpus:
  * ontology gate on types/predicates (no schema drift)
  * extraction cache keyed on (model, prompt version, chunk) -> re-runs are free
  * two-stage entity resolution: deterministic (normalisation + acronym linking)
    then LLM clustering only inside fuzzy candidate blocks (scales past context limits)
  * names the resolver omits fall back to singleton clusters (cookbook failure mode #1)
  * the resolver prompt warns against sub-type -> super-type over-merge (failure mode #2)
"""
from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from rapidfuzz import fuzz

from . import ontology
from .ingest import chunk, discover, load_path, load_url, LoadedDoc
from .providers import Provider
from .schema import EntityProfile, ExtractedGraph, ResolvedClusters
from .store import Store

log = logging.getLogger("kgengine")

RESEARCH_TOPIC = ontology.RESEARCH_TOPIC
PROMPT_VERSION = "extract-v1"

EXTRACTION_PROMPT = """Extract a knowledge graph from the text below, which comes from the document "{title}".

Research focus of this knowledge graph: {topic}

{ontology}

<text>
{text}
</text>

Guidelines:
- Extract entities central to the text's scientific content (findings, measures, populations, methods, mechanisms). Skip author names, affiliations, journal boilerplate, funding statements and citations to other papers.
- Use the most complete name; when the text defines an acronym write "Full Name (ACRONYM)".
- Give every entity a one-sentence description grounded in this text (used later for disambiguation).
- Relations must be scientific claims stated in the text, connect two entities you extracted, use only the allowed predicates, and include a short evidence phrase.
- Use confidence 1.0 for reported results, ~0.7 for reviewed/cited consensus, ~0.4 for hypotheses or speculation.
- Prefer specific claims: "aerobic exercise -[INCREASES]-> hippocampal volume" over vague "exercise -[RELATED_TO]-> brain".
- If the text contains no relevant scientific content (e.g. a reference list or front matter) return empty lists."""

RESOLVE_PROMPT = """Below are candidate groups of {etype} entities extracted from many papers about {topic}
Within each group some names may be surface variants of the same entity (synonyms, acronyms, spelling, plural).

{groups}

Return clusters. Rules:
- Every input name must appear in exactly one cluster's aliases list (copy names exactly).
- Merge only true synonyms. Do NOT merge a specific sub-type into a broader concept
  (e.g. keep "aerobic exercise" separate from "physical exercise"; keep "theta power" separate from "EEG power";
  keep "mild cognitive impairment" separate from "Alzheimer's disease").
- The canonical name is the most complete, standard form, written as "Full Name (ACRONYM)" when an acronym is common."""

SUMMARIZE_PROMPT = """Write a knowledge-graph profile for this entity in the context of: {topic}

Entity: {name} ({etype})
Aliases: {aliases}

Graph relations (with evidence and source documents):
{relations}

Write a 1-2 paragraph factual summary synthesised ONLY from these relations/evidence, noting contradictions
between sources explicitly. Then give 3-6 atomic key facts, each ending with the source document title in [brackets]."""


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
def ingest_doc(store: Store, doc: LoadedDoc, chunk_size: int = 6000, meta: dict | None = None) -> tuple[int, bool]:
    if len(doc.text) < 200:
        raise ValueError(f"too little text ({len(doc.text)} chars) - scanned PDF?")
    return store.add_document(doc.source, doc.title, doc.kind, doc.sha1, chunk(doc.text, chunk_size), meta)


def ingest_paths(store: Store, roots: list[str], include: str | None = None, exclude: str | None = None,
                 limit: int | None = None, chunk_size: int = 6000, max_pages: int | None = None) -> dict:
    files = discover(roots, include, exclude)
    if limit:
        files = files[:limit]
    report = {"found": len(files), "new": 0, "unchanged": 0, "failed": []}
    for f in files:
        try:
            _, new = ingest_doc(store, load_path(f, max_pages), chunk_size)
            report["new" if new else "unchanged"] += 1
        except Exception as e:  # keep going; report at the end
            report["failed"].append(f"{f}: {e}")
    return report


def ingest_url(store: Store, url: str, chunk_size: int = 6000):
    return ingest_doc(store, load_url(url), chunk_size)


def ingest_text(store: Store, title: str, text: str, source: str | None = None, chunk_size: int = 6000):
    d = LoadedDoc(source=source or f"text://{title}", title=title, text=text, kind="text")
    return ingest_doc(store, d, chunk_size)


# ---------------------------------------------------------------------------
# Extraction (NER + RE)
# ---------------------------------------------------------------------------
def _extract_one(provider: Provider, store: Store, row) -> tuple[int, int, ExtractedGraph]:
    key = hashlib.sha1(f"{PROMPT_VERSION}|{provider.name}|{provider.model_id('fast')}|{row['text']}".encode()).hexdigest()
    cached = store.cache_get(key)
    if cached is not None:
        return row["id"], row["doc_id"], ExtractedGraph.model_validate(cached)
    prompt = EXTRACTION_PROMPT.format(title=row["title"], topic=RESEARCH_TOPIC,
                                      ontology=ontology.describe(), text=row["text"])
    g = provider.structured(prompt, ExtractedGraph, role="fast")
    store.cache_put(key, g.model_dump())
    return row["id"], row["doc_id"], g


def _validate(g: ExtractedGraph) -> ExtractedGraph:
    names = {e.name.strip().lower() for e in g.entities}
    rels = [r for r in g.relations
            if r.source.strip().lower() in names and r.target.strip().lower() in names
            and r.source.strip().lower() != r.target.strip().lower()]
    return ExtractedGraph(entities=g.entities, relations=rels)


def extract(store: Store, provider: Provider, max_chunks_per_doc: int | None = None,
            workers: int = 4, doc_ids: list[int] | None = None, progress=print) -> dict:
    rows = store.pending_chunks(max_chunks_per_doc, doc_ids)
    done, failed = 0, []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_extract_one, provider, store, r): r for r in rows}
        for fut in as_completed(futs):
            r = futs[fut]
            try:
                cid, did, g = fut.result()
                g = _validate(g)
                store.save_extraction(cid, did, g)
                done += 1
                progress(f"[{done}/{len(rows)}] {r['title'][:60]} #{r['idx']}: "
                         f"{len(g.entities)} ent, {len(g.relations)} rel")
            except Exception as e:
                failed.append(f"{r['title']} #{r['idx']}: {e}")
                progress(f"FAILED {r['title'][:60]} #{r['idx']}: {e}")
    return {"chunks": len(rows), "extracted": done, "failed": failed,
            "llm_calls": provider.calls, "cost_usd": round(provider.cost_usd, 4)}


# ---------------------------------------------------------------------------
# Entity resolution (ER)
# ---------------------------------------------------------------------------
_ACR = re.compile(r"^(.*?)\s*\(([A-Za-z0-9\-αβθ/]{2,12})\)\s*$")


def norm(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"^(the|a|an)\s+", "", s)
    s = s.replace("’", "'").replace("–", "-").replace("—", "-")
    s = re.sub(r"[^\w\s'\-αβθδγ]", " ", s)
    s = re.sub(r"[\s\-]+", " ", s).strip()
    words = s.split()
    if words and len(words[-1]) > 4 and words[-1].endswith("s") and not words[-1].endswith(("ss", "is", "us")):
        words[-1] = words[-1][:-1]
    return " ".join(words)


class _UF:
    def __init__(self):
        self.p: dict = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def resolve(store: Store, provider: Provider | None, use_llm: bool = True, block_threshold: int = 82,
            max_names_per_call: int = 120, progress=print) -> dict:
    rows = store.q("SELECT name, type, description FROM raw_entities")
    if not rows:
        return {"unique_names": 0, "canonical": 0}
    # 1. majority-vote type per name; keep first description + counts
    type_votes: dict[str, Counter] = defaultdict(Counter)
    desc: dict[str, str] = {}
    count: Counter = Counter()
    for r in rows:
        type_votes[r["name"]][ontology.normalize_type(r["type"])] += 1
        desc.setdefault(r["name"], r["description"])
        count[r["name"]] += 1
    etype = {n: v.most_common(1)[0][0] for n, v in type_votes.items()}

    # 2. deterministic merge: normalised form + acronym linking (within type).
    #    A shared acronym alone never joins two different full names ("Exhaustive exercise (EE)"
    #    vs "Enriched environment (EE)"); a bare acronym links only when it is unambiguous.
    uf = _UF()
    key_owner: dict[tuple[str, str], str] = {}
    acr_full: dict[tuple[str, str], set[str]] = defaultdict(set)
    for n in etype:
        uf.find(n)
        m = _ACR.match(n)
        keys = {norm(n)} | ({norm(m.group(1))} if m else set())
        if m:
            acr_full[(etype[n], norm(m.group(2)))].add(norm(m.group(1)))
        for k in keys:
            kk = (etype[n], k)
            if kk in key_owner:
                uf.union(n, key_owner[kk])
            else:
                key_owner[kk] = n
    for n in etype:  # bare acronyms, e.g. "IAPF"
        fulls = acr_full.get((etype[n], norm(n)))
        if fulls and len(fulls) == 1 and not _ACR.match(n):
            uf.union(n, key_owner[(etype[n], next(iter(fulls)))])

    def canonical_of(members: list[str]) -> str:
        with_acr = [m for m in members if _ACR.match(m)]
        pool = with_acr or members
        return max(pool, key=lambda m: (sum(count[x] for x in members if norm(x) == norm(m)), len(m)))

    groups: dict[str, list[str]] = defaultdict(list)
    for n in etype:
        groups[uf.find(n)].append(n)
    reps = {canonical_of(ms): ms for ms in groups.values()}
    det_merges = len(etype) - len(reps)

    # 3. LLM clustering inside fuzzy candidate blocks (per type)
    llm_merges = 0
    if use_llm and provider is not None:
        by_type: dict[str, list[str]] = defaultdict(list)
        for rep in reps:
            by_type[etype[rep]].append(rep)
        for t, names in by_type.items():
            buf = _UF()
            for i, a in enumerate(names):
                na = norm(_ACR.sub(r"\1", a))
                for b in names[i + 1:]:
                    nb = norm(_ACR.sub(r"\1", b))
                    if fuzz.token_set_ratio(na, nb) >= block_threshold or _acronym_of(a, b) or _acronym_of(b, a):
                        buf.union(a, b)
            blocks: dict[str, list[str]] = defaultdict(list)
            for n in names:
                blocks[buf.find(n)].append(n)
            cand = [b for b in blocks.values() if len(b) > 1]
            batch, size = [], 0
            for b in cand + [None]:
                if b is not None and size + len(b) <= max_names_per_call:
                    batch.append(b)
                    size += len(b)
                    continue
                if batch:
                    llm_merges += _llm_cluster(provider, store, t, batch, reps, desc, progress)
                batch, size = ([b], len(b)) if b else ([], 0)

    # 4. write alias table
    out = []
    for canon, members in reps.items():
        for m in members:
            out.append((m, etype[m], canon, "llm" if m != canon and norm(m) != norm(canon) else "deterministic"))
    store.x("DELETE FROM aliases")
    store.set_aliases(out)
    return {"unique_names": len(etype), "canonical": len(reps),
            "deterministic_merges": det_merges, "llm_merges": llm_merges}


def _acronym_of(short: str, long: str) -> bool:
    s = re.sub(r"[^A-Za-z]", "", short)
    if not (2 <= len(s) <= 6 and short.strip().isupper()):
        return False
    initials = "".join(w[0] for w in re.findall(r"[A-Za-z]+", long) if w.lower() not in {"of", "and", "the", "in"})
    return initials.upper().startswith(s.upper()) or s.upper() in initials.upper()


def _llm_cluster(provider, store, etype, blocks, reps, desc, progress) -> int:
    lines = []
    for gi, b in enumerate(blocks, 1):
        lines.append(f"Group {gi}:")
        lines += [f"- {n}: {desc.get(n, '')[:160]}" for n in b]
    prompt = RESOLVE_PROMPT.format(etype=etype, topic=RESEARCH_TOPIC, groups="\n".join(lines))
    key = "resolve|" + hashlib.sha1(f"{provider.name}|{provider.model_id('smart')}|{prompt}".encode()).hexdigest()
    try:
        cached = store.cache_get(key)
        res = ResolvedClusters.model_validate(cached) if cached else provider.structured(prompt, ResolvedClusters, role="smart")
        store.cache_put(key, res.model_dump())
    except Exception as e:
        progress(f"resolve LLM failed for {etype}: {e}; keeping deterministic result")
        return 0
    valid = {n for b in blocks for n in b}
    merges = 0
    seen: set[str] = set()
    for c in res.clusters:
        members = [a for a in c.aliases if a in valid and a not in seen]
        if len(members) < 2:
            continue
        canon = c.canonical if c.canonical in members else max(members, key=len)
        if c.canonical not in valid and c.canonical.strip():
            canon = max(members, key=lambda m: (bool(_ACR.match(m)), len(m)))
        for m in members:
            seen.add(m)
            if m != canon and m in reps:
                reps[canon].extend(reps.pop(m))
                merges += 1
    progress(f"resolved {etype}: {sum(map(len, blocks))} candidates -> {merges} merges")
    return merges  # names the model omitted simply remain their own cluster


# ---------------------------------------------------------------------------
# Entity summarization (hub profiles)
# ---------------------------------------------------------------------------
def summarize(store: Store, provider: Provider, kg, top: int = 15, names: list[str] | None = None, progress=print) -> int:
    import json, time
    from .graph import edge_lines
    targets = names or [n for n, _ in sorted(kg.G.degree(), key=lambda x: -x[1])[:top]]
    n_done = 0
    for name in targets:
        if name not in kg.G:
            continue
        node = kg.G.nodes[name]
        rels = edge_lines(kg.G, name, with_evidence=True, limit=80)
        prompt = SUMMARIZE_PROMPT.format(topic=RESEARCH_TOPIC, name=name, etype=node["type"],
                                         aliases=", ".join(node.get("aliases", [])) or "-", relations=rels)
        try:
            p = provider.structured(prompt, EntityProfile, role="smart")
        except Exception as e:
            progress(f"summary failed for {name}: {e}")
            continue
        store.x("INSERT OR REPLACE INTO profiles VALUES(?,?,?,?)", (name, p.summary, json.dumps(p.key_facts), time.time()))
        n_done += 1
        progress(f"profiled {name}")
    return n_done
