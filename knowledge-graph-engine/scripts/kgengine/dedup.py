"""Duplicate-document detection.

The same paper often exists several times in a library (publisher PDF + renamed copy,
"Gutmann_2015_..." vs "Gutmann 等 - 2015 - ..."). Copies would otherwise be counted as
independent supporting documents and inflate edge weights.

Method: word 8-gram shingles over the first ~4,000 characters (title/abstract/intro),
inverted index for candidate pairs, Jaccard similarity >= threshold -> duplicate.
A second sample (chunk 1) must also overlap, to reject shared front matter.
The longest (most complete) copy is kept as canonical; others get documents.dup_of.
"""
from __future__ import annotations

import re
import zlib
from collections import defaultdict

from .store import Store


def shingles(text: str, k: int = 8, head: int = 4000) -> set[int]:
    words = re.findall(r"[a-z0-9]+", text[:head].lower())
    return {zlib.crc32(" ".join(words[i:i + k]).encode()) for i in range(max(0, len(words) - k + 1))}


def find_duplicates(store: Store, threshold: float = 0.5, body_threshold: float = 0.3,
                    short_threshold: float = 0.85) -> list[tuple[int, int, float]]:
    rows = store.q("SELECT d.id, d.n_chars, c.text, (SELECT COUNT(*) FROM chunks x WHERE x.doc_id=d.id AND x.extracted=1) AS n_ext "
                   "FROM documents d JOIN chunks c ON c.doc_id=d.id AND c.idx=0")
    sh = {r["id"]: shingles(r["text"]) for r in rows}
    body = {r["doc_id"]: shingles(r["text"]) for r in store.q("SELECT doc_id, text FROM chunks WHERE idx=1")}
    size = {r["id"]: (r["n_ext"], r["n_chars"]) for r in rows}  # prefer already-extracted, then longest
    index: dict[int, list[int]] = defaultdict(list)
    for d, s in sh.items():
        for h in s:
            index[h].append(d)
    overlap: dict[tuple[int, int], int] = defaultdict(int)
    for ds in index.values():
        if 1 < len(ds) <= 50:  # very common shingles (boilerplate) are skipped
            for i, a in enumerate(ds):
                for b in ds[i + 1:]:
                    overlap[(min(a, b), max(a, b))] += 1
    pairs = []
    for (a, b), inter in overlap.items():
        union = len(sh[a]) + len(sh[b]) - inter
        j = inter / union if union else 0
        if j < threshold:
            continue
        # guard against shared boilerplate (publisher copyright/front-matter pages):
        # when both copies have a second chunk, it must overlap too
        if a in body and b in body and body[a] and body[b]:
            jb = len(body[a] & body[b]) / len(body[a] | body[b])
            if jb < body_threshold:
                continue
        elif j < short_threshold:  # one-chunk docs (e.g. copyright pages): require near-identity
            continue
        pairs.append((a, b, round(j, 3)))
    # union-find -> clusters, canonical = most-extracted, then longest copy
    parent: dict[int, int] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b, _ in pairs:
        parent[find(a)] = find(b)
    clusters: dict[int, list[int]] = defaultdict(list)
    for d in parent:
        clusters[find(d)].append(d)
    out = []
    for members in clusters.values():
        keep = max(members, key=lambda d: (size[d], -d))
        out += [(d, keep, 1.0) for d in members if d != keep]
    return out


def mark_duplicates(store: Store, threshold: float = 0.5) -> dict:
    dups = find_duplicates(store, threshold)
    store.x("UPDATE documents SET dup_of=NULL")
    with store.lock:
        store.db.executemany("UPDATE documents SET dup_of=? WHERE id=?", [(keep, d) for d, keep, _ in dups])
        store.db.commit()
    titles = {r["id"]: r["title"] for r in store.q("SELECT id, title FROM documents")}
    return {"duplicates": len(dups),
            "examples": [f"{titles[d]}  ==>  {titles[k]}" for d, k, _ in dups[:15]]}
