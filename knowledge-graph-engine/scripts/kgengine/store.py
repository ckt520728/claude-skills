"""SQLite persistence. Raw extractions are kept forever (with provenance) and the
canonical graph is *derived* from raw rows + the alias table, so re-running entity
resolution never loses information."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents(
  id INTEGER PRIMARY KEY, source TEXT UNIQUE, title TEXT, kind TEXT, sha1 TEXT,
  n_chars INTEGER, added_at REAL, status TEXT DEFAULT 'ingested', meta TEXT);
CREATE TABLE IF NOT EXISTS chunks(
  id INTEGER PRIMARY KEY, doc_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
  idx INTEGER, text TEXT, extracted INTEGER DEFAULT 0, UNIQUE(doc_id, idx));
CREATE TABLE IF NOT EXISTS raw_entities(
  id INTEGER PRIMARY KEY, chunk_id INTEGER REFERENCES chunks(id) ON DELETE CASCADE,
  doc_id INTEGER, name TEXT, type TEXT, description TEXT);
CREATE TABLE IF NOT EXISTS raw_relations(
  id INTEGER PRIMARY KEY, chunk_id INTEGER REFERENCES chunks(id) ON DELETE CASCADE,
  doc_id INTEGER, source TEXT, predicate TEXT, target TEXT, evidence TEXT, confidence REAL);
CREATE TABLE IF NOT EXISTS aliases(
  alias TEXT, type TEXT, canonical TEXT, method TEXT, PRIMARY KEY(alias, type));
CREATE TABLE IF NOT EXISTS profiles(
  canonical TEXT PRIMARY KEY, summary TEXT, key_facts TEXT, updated_at REAL);
CREATE TABLE IF NOT EXISTS llm_cache(key TEXT PRIMARY KEY, value TEXT);
CREATE INDEX IF NOT EXISTS ix_re_doc ON raw_entities(doc_id);
CREATE INDEX IF NOT EXISTS ix_rr_doc ON raw_relations(doc_id);
"""


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(self.path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA)
        cols = {r[1] for r in self.db.execute("PRAGMA table_info(documents)")}
        if "dup_of" not in cols:  # migration: duplicate-document detection
            self.db.execute("ALTER TABLE documents ADD COLUMN dup_of INTEGER")
        self.db.commit()

    # --- generic -------------------------------------------------------
    def q(self, sql: str, args=()) -> list[sqlite3.Row]:
        with self.lock:
            return self.db.execute(sql, args).fetchall()

    def x(self, sql: str, args=()):
        with self.lock:
            cur = self.db.execute(sql, args)
            self.db.commit()
            return cur

    # --- documents -----------------------------------------------------
    def add_document(self, source, title, kind, sha1, chunks: list[str], meta: dict | None = None) -> tuple[int, bool]:
        """Returns (doc_id, is_new). Re-ingesting unchanged content is a no-op."""
        with self.lock:
            row = self.db.execute("SELECT id, sha1 FROM documents WHERE source=?", (source,)).fetchone()
            if row and row["sha1"] == sha1:
                return row["id"], False
            if row:  # content changed: drop old chunks (cascades raw rows)
                self.db.execute("DELETE FROM documents WHERE id=?", (row["id"],))
            cur = self.db.execute(
                "INSERT INTO documents(source,title,kind,sha1,n_chars,added_at,meta) VALUES(?,?,?,?,?,?,?)",
                (source, title, kind, sha1, sum(map(len, chunks)), time.time(), json.dumps(meta or {})))
            doc_id = cur.lastrowid
            self.db.executemany("INSERT INTO chunks(doc_id, idx, text) VALUES(?,?,?)",
                                [(doc_id, i, c) for i, c in enumerate(chunks)])
            self.db.commit()
            return doc_id, True

    def pending_chunks(self, max_chunks_per_doc: int | None = None, doc_ids: list[int] | None = None):
        sql = "SELECT c.id, c.doc_id, c.idx, c.text, d.title FROM chunks c JOIN documents d ON d.id=c.doc_id WHERE c.extracted=0 AND d.dup_of IS NULL"
        args: list = []
        if max_chunks_per_doc is not None:
            sql += " AND c.idx < ?"
            args.append(max_chunks_per_doc)
        if doc_ids:
            sql += f" AND c.doc_id IN ({','.join('?' * len(doc_ids))})"
            args += doc_ids
        return self.q(sql + " ORDER BY c.doc_id, c.idx", args)

    def save_extraction(self, chunk_id: int, doc_id: int, graph) -> None:
        with self.lock:
            self.db.execute("DELETE FROM raw_entities WHERE chunk_id=?", (chunk_id,))
            self.db.execute("DELETE FROM raw_relations WHERE chunk_id=?", (chunk_id,))
            self.db.executemany(
                "INSERT INTO raw_entities(chunk_id,doc_id,name,type,description) VALUES(?,?,?,?,?)",
                [(chunk_id, doc_id, e.name.strip(), e.type, e.description) for e in graph.entities])
            self.db.executemany(
                "INSERT INTO raw_relations(chunk_id,doc_id,source,predicate,target,evidence,confidence) VALUES(?,?,?,?,?,?,?)",
                [(chunk_id, doc_id, r.source.strip(), r.predicate, r.target.strip(), r.evidence, r.confidence)
                 for r in graph.relations])
            self.db.execute("UPDATE chunks SET extracted=1 WHERE id=?", (chunk_id,))
            self.db.commit()

    # --- aliases -------------------------------------------------------
    def set_aliases(self, rows: list[tuple[str, str, str, str]]) -> None:
        with self.lock:
            self.db.executemany("INSERT OR REPLACE INTO aliases(alias,type,canonical,method) VALUES(?,?,?,?)", rows)
            self.db.commit()

    def alias_map(self) -> dict[tuple[str, str], str]:
        return {(r["alias"], r["type"]): r["canonical"] for r in self.q("SELECT * FROM aliases")}

    # --- cache ---------------------------------------------------------
    def cache_get(self, key: str):
        r = self.q("SELECT value FROM llm_cache WHERE key=?", (key,))
        return json.loads(r[0]["value"]) if r else None

    def cache_put(self, key: str, value) -> None:
        self.x("INSERT OR REPLACE INTO llm_cache(key,value) VALUES(?,?)", (key, json.dumps(value)))

    def stats(self) -> dict:
        one = lambda sql: self.q(sql)[0][0]
        return {
            "documents": one("SELECT COUNT(*) FROM documents"),
            "chunks": one("SELECT COUNT(*) FROM chunks"),
            "chunks_extracted": one("SELECT COUNT(*) FROM chunks WHERE extracted=1"),
            "raw_entities": one("SELECT COUNT(*) FROM raw_entities"),
            "raw_relations": one("SELECT COUNT(*) FROM raw_relations"),
            "aliases": one("SELECT COUNT(*) FROM aliases"),
            "profiles": one("SELECT COUNT(*) FROM profiles"),
            "duplicate_documents": one("SELECT COUNT(*) FROM documents WHERE dup_of IS NOT NULL"),
        }
