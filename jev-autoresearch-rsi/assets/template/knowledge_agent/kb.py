"""
Second Brain knowledge base writer.

Every research run is merged into an Obsidian-style wiki (topics, concepts, sources, gaps).
Code owns only the text between BEGIN and END on each page. Everything outside those markers,
including front matter written by the user, is kept byte for byte. Nothing is ever deleted.
"""

from __future__ import annotations

import json
import re
import hashlib
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import BASE_DIR, CONFIG

KB_ROOT_DEFAULT = BASE_DIR / "knowledge_base"  # used when project.json has no knowledge_base.root
BEGIN, END = "<!-- autoresearch:begin -->", "<!-- autoresearch:end -->"
REDIRECT_MARK = "<!-- autoresearch:redirect -->"
UNLINKED_HEADING = "## Unlinked pages"
TOPIC_DIR, CONCEPT_DIR, SOURCE_DIR, GAP_DIR = "主題", "概念", "來源", "缺口"
GAPS_ID = f"{GAP_DIR}/gaps"
LEDGER_PAGE = "RSI ledger"

DATA_RE = re.compile(r"<!-- autoresearch:data (.*?) -->", re.S)
LINK_RE = re.compile(r"\[\[([^\[\]\n]+?)\]\]")
FENCE_RE = re.compile(r"```.*?```", re.S)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
CITE_RE = re.compile(r"\[(E\d+(?:\s*,\s*E\d+)*)\]")
GAP_LINE_RE = re.compile(r"^\s*- \[( |x|X)\]\s+(.*?)\s*$")
GAP_TOPIC_RE = re.compile(r"\s+\(topic: \[\[" + TOPIC_DIR + r"/([^\]|#]+)[^\]]*\]\](?:, run (.*?))?\)\s*$")
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


# ------------------------------------------------------------------ paths and text helpers

def kb_root() -> Path:
    configured = (CONFIG.get("knowledge_base") or {}).get("root")
    return Path(configured) if configured else KB_ROOT_DEFAULT


def vault_kb_dir(root: Path) -> Path:
    return Path(root).parent


def read_text(path: Path) -> str:
    return Path(path).read_bytes().decode("utf-8")


def write_text(path: Path, text: str) -> None:
    """One write of the whole page, as bytes, so Windows never rewrites line endings."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def safe_name(text: str, maxlen: int = 80) -> str:
    """Windows-safe file stem: no `<>:"/\\|?*` or wiki-link characters, CJK kept, at most `maxlen` characters."""
    s = unicodedata.normalize("NFC", text or "").replace("/", "_").replace("\\", "_")
    s = re.sub(r'[<>:"|?*\[\]#^\x00-\x1f]', "", s)
    s = re.sub(r"\s+", " ", s).strip(" .")
    if len(s) > maxlen:
        digest = hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]
        s = s[: maxlen - 9].rstrip(" .") + "-" + digest
    if not s:
        return "untitled"
    if s.split(".")[0].upper() in _RESERVED:
        s += "_"
    return s


def norm_name(text: str) -> str:
    """Identity of a name: NFKC, case-folded, punctuation and symbols removed, spaces collapsed. CJK is kept."""
    s = unicodedata.normalize("NFKC", text or "").casefold()
    s = "".join(" " if unicodedata.category(ch)[0] in "PS" else ch for ch in s)
    return re.sub(r"\s+", " ", s).strip()


def source_id(e: dict) -> str:
    if e.get("doi"):
        raw = "doi-" + str(e["doi"]).strip().lower()
    elif e.get("pmid"):
        raw = "pmid-" + str(e["pmid"]).strip()
    elif e.get("arxiv_id"):
        raw = "arxiv-" + str(e["arxiv_id"]).strip()
    elif e.get("nct_id"):
        raw = str(e["nct_id"]).strip().upper()
    else:
        raw = e.get("title") or "untitled"
    return safe_name(raw)


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def iter_md(root: Path) -> List[Tuple[str, Path]]:
    """(page id without .md, path) for every page in the KB. Hidden folders and any Clippings folder are skipped."""
    root = Path(root)
    out = []
    if not root.is_dir():
        return out
    for p in sorted(root.rglob("*.md")):
        rel = p.relative_to(root)
        if any(part.startswith(".") or part.casefold() == "clippings" for part in rel.parts):
            continue
        out.append((rel.with_suffix("").as_posix(), p))
    return out


def page_type(page_id: str) -> str:
    return {TOPIC_DIR: "topic", CONCEPT_DIR: "concept", SOURCE_DIR: "source", GAP_DIR: "gap"}.get(page_id.split("/")[0], "other") if "/" in page_id else "other"


def link_target(raw: str) -> str:
    t = raw.split("|")[0].split("#")[0].strip().replace("\\", "/").lstrip("/")
    return t[:-3] if t.lower().endswith(".md") else t


def wikilinks(text: str) -> List[str]:
    """Targets of `[[...]]` links outside code fences and comments; aliases and headings are removed."""
    text = COMMENT_RE.sub("", FENCE_RE.sub("", text))
    return [t for t in (link_target(m) for m in LINK_RE.findall(text)) if t]


def parse_frontmatter(text: str) -> Tuple[dict, str]:
    t = text.lstrip("\ufeff")
    m = re.match(r"---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", t, re.S)
    if not m:
        return {}, t
    data: dict = {}
    key = None
    for line in m.group(1).splitlines():
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and key is not None:
            if not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(_scalar(item.group(1)))
            continue
        kv = re.match(r"^([^\s:#][^:]*):\s*(.*)$", line)
        if kv:
            key, value = kv.group(1).strip(), kv.group(2).strip()
            if value.startswith("[") and value.endswith("]"):
                data[key] = [_scalar(v) for v in value[1:-1].split(",") if v.strip()]
            elif value == "":
                data[key] = ""
            else:
                data[key] = _scalar(value)
    return data, t[m.end():]


def _scalar(value: str):
    value = value.strip()
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        try:
            return json.loads(value)
        except ValueError:
            return value[1:-1]
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1]
    return value


def frontmatter(title: str, date: str, tags: List[str], **extra) -> str:
    lines = ["---", f"title: {json.dumps(title, ensure_ascii=False)}", f'date: "{date}"', "tags:"]
    lines += [f"  - {t}" for t in tags]
    for k, v in extra.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            lines += [f"  - {json.dumps(x, ensure_ascii=False)}" for x in v]
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: {json.dumps(str(v), ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ managed blocks

def block_span(text: str) -> Optional[Tuple[int, int]]:
    b = text.find(BEGIN)
    if b < 0:
        return None
    e = text.find(END, b + len(BEGIN))
    if e < 0:
        raise ValueError("unbalanced autoresearch markers: BEGIN without END")
    return b, e + len(END)


def get_block(text: str) -> Optional[str]:
    span = block_span(text)
    return None if span is None else text[span[0] + len(BEGIN): span[1] - len(END)]


def set_block(text: Optional[str], inner: str, head: str = "") -> str:
    """Replace the managed block, or append one. Text outside the markers is untouched."""
    block = f"{BEGIN}\n{inner.strip(chr(10))}\n{END}"
    if text is None:
        return head + ("\n" if head else "") + block + "\n"
    span = block_span(text)
    if span is None:
        sep = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        return text + sep + block + "\n"
    return text[: span[0]] + block + text[span[1]:]


def dump_state(state: dict) -> str:
    return "<!-- autoresearch:data " + json.dumps(state, ensure_ascii=False, sort_keys=True).replace("--", "-\\u002d") + " -->"


def load_state(text: Optional[str]) -> dict:
    block = get_block(text) if text else None
    m = DATA_RE.search(block or "")
    if not m:
        return {}
    try:
        data = json.loads(m.group(1))
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def is_redirect(text: str) -> bool:
    return REDIRECT_MARK in (get_block(text) or "")


# ------------------------------------------------------------------ page lookup

def find_page(root: Path, folder: str, name: str, planned: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Stem of the page in `folder` whose normalized name equals `name`, following merge redirects."""
    want = norm_name(name)
    stem = (planned or {}).get(f"{folder}:{want}")
    d = Path(root) / folder
    if stem is None and d.is_dir():
        for p in sorted(d.glob("*.md")):
            if norm_name(p.stem) == want:
                stem = p.stem
                break
    for _ in range(5):
        if stem is None:
            return None
        path = d / (stem + ".md")
        if not path.exists():
            return stem
        redirect = load_state(read_text(path)).get("redirect") if is_redirect(read_text(path)) else None
        if not redirect:
            return stem
        stem = Path(redirect).name
    return stem


class Ctx:
    """What exists, so rendered text only links to pages that will really exist."""

    def __init__(self, root: Path, planned_ids: Optional[set] = None, planned: Optional[Dict[str, str]] = None):
        self.root = Path(root)
        self.planned_ids = planned_ids or set()
        self.planned = planned or {}

    def exists(self, page_id: str) -> bool:
        return page_id in self.planned_ids or (self.root / (page_id + ".md")).exists()

    def link(self, folder: str, name: str) -> str:
        stem = find_page(self.root, folder, name, self.planned)
        if stem is not None and self.exists(f"{folder}/{stem}"):
            return f"[[{folder}/{stem}]]"
        return name


# ------------------------------------------------------------------ rendering

_MM = str.maketrans({"(": "（", ")": "）", "[": "［", "]": "］", "{": "｛", "}": "｝", '"': "'", "<": " ", ">": " ", "\n": " ", "\r": " ", "`": "'"})


def mm(text: str) -> str:
    """Mermaid node text: brackets and parentheses would break the mindmap grammar."""
    return re.sub(r"\s+", " ", (text or "").translate(_MM)).strip() or "-"


def one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _apa_ish(e: dict) -> str:
    parts = [one_line(e.get("authors", "")), f"({e.get('year') or 'n.d.'})."]
    title = one_line(e.get("title", ""))
    if title:
        parts.append(title if title[-1] in ".?!" else title + ".")
    if e.get("journal"):
        parts.append(one_line(e["journal"]) + ".")
    if e.get("doi"):
        parts.append(f"https://doi.org/{e['doi']}")
    elif e.get("pmid"):
        parts.append(f"https://pubmed.ncbi.nlm.nih.gov/{e['pmid']}/")
    elif e.get("arxiv_id"):
        parts.append(f"https://arxiv.org/abs/{e['arxiv_id']}")
    elif e.get("nct_id"):
        parts.append(f"https://clinicaltrials.gov/study/{e['nct_id']}")
    elif e.get("url"):
        parts.append(e["url"])
    return " ".join(p for p in parts if p)


def render_concept(state: dict, ctx: Ctx) -> str:
    lines = [dump_state(state), "", "## 定義", state.get("definition") or "（尚無定義）", "", "## Claims（主張）"]
    for c in state.get("claims", []):
        links = ", ".join(f"[[{SOURCE_DIR}/{s}]]" for s in c.get("sources", []))
        lines.append(f"- {c['text']} ({links})" if links else f"- {c['text']}")
    if not state.get("claims"):
        lines.append("（尚無主張）")
    lines += ["", "## 相關概念"] + [f"- {ctx.link(CONCEPT_DIR, n)}" for n in state.get("related", [])]
    lines += ["", "## 出現的主題"] + [f"- {ctx.link(TOPIC_DIR, n)}" for n in state.get("topics", [])]
    return "\n".join(lines)


def render_source(state: dict, ctx: Ctx) -> str:
    e = state.get("evidence", {})
    info = [f"- 類型：{e.get('kind', '')}"]
    for label, key in (("連結", "url"), ("DOI", "doi"), ("PMID", "pmid"), ("arXiv", "arxiv_id"), ("NCT", "nct_id")):
        if e.get(key):
            info.append(f"- {label}：{e[key]}")
    lines = [dump_state(state), "", "## 引用", _apa_ish(e), "", "## 資訊"] + info
    lines += ["", "## 被引用於概念"] + [f"- {ctx.link(CONCEPT_DIR, n)}" for n in state.get("concepts", [])]
    lines += ["", "## 執行紀錄"] + [f"- run {r}" for r in state.get("run_ids", [])]
    return "\n".join(lines)


def render_topic(state: dict, ctx: Ctx) -> str:
    runs = state.get("runs", [])
    summary = runs[-1].get("summary", "") if runs else ""
    lines = [dump_state(state), "", "## 摘要", summary or "（尚無摘要）", "", "## 關鍵概念"]
    lines += [f"- {ctx.link(CONCEPT_DIR, n)}" for n in state.get("concepts", [])]
    lines += ["", "## 心智圖", "```mermaid", "mindmap", f"  root(({mm(state.get('topic', ''))}))"]
    lines += [f"    {mm(n)}" for n in state.get("concepts", [])]
    lines += ["```", "", "## 來源"]
    titles = state.get("source_titles", {})
    lines += [f"- [[{SOURCE_DIR}/{s}]] — {one_line(titles.get(s, ''))}".rstrip(" —") for s in state.get("sources", [])]
    lines += ["", "## 執行紀錄"] + [f"- {r.get('date', '')} run {r.get('run_id', '')}" for r in runs]
    lines += ["", "## 待補缺口"] + [f"- {g}" for g in state.get("gaps", [])]
    if state.get("conflicts"):
        lines += ["", "## 證據衝突"]
        for c in state["conflicts"]:
            cites = ", ".join(f"[[{SOURCE_DIR}/{s}]]" for s in c.get("sources", []))
            lines.append(f"- **{one_line(c.get('concept', ''))}**：{one_line(c.get('detail', ''))}" + (f" ({cites})" if cites else ""))
    if state.get("deliverables"):
        lines += ["", "## 成果檔案"]
        for d in state["deliverables"]:
            p = d.get("path", "")
            try:
                target = Path(p).as_uri() if Path(p).is_absolute() else ""
            except ValueError:
                target = ""
            lines.append(f"- {d.get('label', '')} (run {d.get('run_id', '')}): " + (f"[{Path(p).name}]({target})" if target else f"`{p}`"))
    return "\n".join(lines)


# ------------------------------------------------------------------ gaps, index, vault files

def parse_gap_lines(text: str) -> List[dict]:
    out = []
    for line in text.splitlines():
        m = GAP_LINE_RE.match(line)
        if not m:
            continue
        body = m.group(2)
        t = GAP_TOPIC_RE.search(body)
        out.append({"done": m.group(1) != " ", "text": body[: t.start()] if t else body, "topic": t.group(1) if t else "", "run": (t.group(2) or "") if t else "", "line": line})
    return out


def open_gaps(root: Path, topic: str = "") -> List[str]:
    path = Path(root) / (GAPS_ID + ".md")
    if not path.exists():
        return []
    wanted = set()
    if topic:
        wanted = {norm_name(topic), norm_name(safe_name(topic))}
        stem = find_page(root, TOPIC_DIR, topic)
        if stem:
            wanted.add(norm_name(stem))
    return [g["text"] for g in parse_gap_lines(read_text(path)) if not g["done"] and (not topic or norm_name(g["topic"]) in wanted)]


def _unlinked_items(text: Optional[str]) -> List[str]:
    block = get_block(text) if text else None
    if not block or UNLINKED_HEADING not in block:
        return []
    tail = block.split(UNLINKED_HEADING, 1)[1]
    return [m.group(1) for line in tail.splitlines() for m in [re.match(r"^- \[\[([^\]|#]+)\]\]", line)] if m]


def write_index(root: Path, add_unlinked: Optional[str] = None) -> Optional[str]:
    """Rewrite the KB home page. Returns its rel path when the file changed."""
    root = Path(root)
    path = root / "index.md"
    old = read_text(path) if path.exists() else None
    ids = [i for i, _ in iter_md(root)]
    topics = [i for i in ids if i.startswith(TOPIC_DIR + "/")]
    sources = [i for i in ids if i.startswith(SOURCE_DIR + "/")]
    concepts = []
    for i, p in iter_md(root):
        if i.startswith(CONCEPT_DIR + "/") and not is_redirect(read_text(p)):
            concepts.append(i)
    unlinked = [u for u in _unlinked_items(old) + ([add_unlinked] if add_unlinked else []) if u in ids]
    unlinked = list(dict.fromkeys(unlinked))
    lines = ["## 概況", f"- 主題：{len(topics)}", f"- 概念：{len(concepts)}", f"- 來源：{len(sources)}", f"- 開放缺口：{len(open_gaps(root))}", "",
             "## 主題"] + [f"- [[{i}]]" for i in topics] + ["", "## 概念"] + [f"- [[{i}]]" for i in concepts]
    lines += ["", "## 導覽", f"- [[{GAPS_ID}]]", f"- [[{LEDGER_PAGE}]]"]
    if unlinked:
        lines += ["", UNLINKED_HEADING] + [f"- [[{u}]]" for u in unlinked]
    head = frontmatter("2026 Autoresearch RSI 知識庫", today(), ["autoresearch", "index"], type="index")
    new = set_block(old, "\n".join(lines), head)
    if new != old:
        write_text(path, new)
        return "index.md"
    return None


def add_unlinked(root: Path, page_id: str) -> List[str]:
    changed = write_index(root, add_unlinked=page_id)
    return [changed] if changed else []


def _ensure_ledger_page(root: Path) -> Optional[str]:
    path = Path(root) / (LEDGER_PAGE + ".md")
    if path.exists():
        return None
    body = ("Every promote or reject decision of the knowledge-base self-improvement step is appended to the project ledger "
            "(SHA-256 chained JSONL) and to the improvement queue in the vault.\n\nBack to [[index]].")
    write_text(path, set_block(None, body, frontmatter("RSI ledger", today(), ["autoresearch", "rsi"])))
    return LEDGER_PAGE + ".md"


def _vault_files(root: Path, run: dict, topic_stem: str, n_concepts: int, n_sources: int) -> None:
    vault = vault_kb_dir(root)
    vault.mkdir(parents=True, exist_ok=True)
    home = f"{Path(root).name}/index"
    idx = vault / "index.md"
    text = read_text(idx) if idx.exists() else "---\ntitle: 知識庫索引\ntype: index\n---\n# 知識庫索引\n"
    if f"[[{home}" not in text:
        write_text(idx, text + ("" if text.endswith("\n") else "\n") + f"- [[{home}|{Path(root).name}]] — 自動研究知識庫首頁\n")
    log = vault / "log.md"
    ltext = read_text(log) if log.exists() else "---\ntitle: 知識庫操作紀錄\ntype: log\n---\n\n# 知識庫操作紀錄\n"
    tag = f"[run:{run['run_id']}]"
    if tag not in ltext:
        line = (f"- {run.get('date') or today()} 自動研究 {tag} [[{Path(root).name}/{TOPIC_DIR}/{topic_stem}]]："
                f"{n_concepts} 個概念、{n_sources} 個來源\n")
        write_text(log, ltext + ("" if ltext.endswith("\n") else "\n") + line)


# ------------------------------------------------------------------ integrate a run

def _merge_names(old: List[str], new: List[str]) -> List[str]:
    seen = {norm_name(n) for n in old}
    out = list(old)
    for n in new:
        n = one_line(n)
        if n and norm_name(n) not in seen:
            seen.add(norm_name(n))
            out.append(n)
    return out


def _merge_claims(old: List[dict], new: List[dict]) -> List[dict]:
    out = [{"text": c["text"], "sources": list(c.get("sources", []))} for c in old]
    index = {norm_name(c["text"]): c for c in out}
    for c in new:
        key = norm_name(c["text"])
        if not key:
            continue
        if key in index:
            for s in c.get("sources", []):
                if s not in index[key]["sources"]:
                    index[key]["sources"].append(s)
        else:
            item = {"text": c["text"], "sources": list(dict.fromkeys(c.get("sources", [])))}
            out.append(item)
            index[key] = item
    return out


def _write_state_page(root: Path, rel: str, kind: str, title: str, date: str, mutate, render, tracker: dict, tags: List[str], **fm_extra) -> None:
    path = Path(root) / (rel + ".md")
    root_resolved = Path(root).resolve()
    if root_resolved not in path.resolve().parents:
        raise ValueError(f"refusing to write outside the knowledge base: {rel}")
    old = read_text(path) if path.exists() else None
    state = mutate(load_state(old) if old else {})
    head = frontmatter(title, date, tags, **fm_extra)
    new = set_block(old, render(state), head)
    if old is None:
        write_text(path, new)
        tracker["created"].add(rel + ".md")
    elif new != old:
        write_text(path, new)
        if rel + ".md" not in tracker["created"]:
            tracker["updated"].add(rel + ".md")


def integrate_run(root: Path, run: dict) -> dict:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    tracker = {"created": set(), "updated": set()}
    run_id, topic, date = str(run["run_id"]), one_line(run["topic"]), run.get("date") or today()
    evidence = list(run.get("evidence") or [])
    notes = [n for n in (run.get("notes") or []) if one_line(n.get("concept", ""))]

    key2sid: Dict[str, str] = {}
    sources: Dict[str, dict] = {}
    for i, e in enumerate(evidence):
        sid = source_id(e)
        key2sid[e.get("key") or f"E{i + 1}"] = sid
        merged = sources.setdefault(sid, {})
        for k, v in e.items():
            if v and not merged.get(k):
                merged[k] = v

    def keys_to_sids(keys) -> List[str]:
        return list(dict.fromkeys(key2sid[k] for k in keys if k in key2sid))

    def convert(text: str) -> str:
        def sub(m):
            keys = [k.strip() for k in m.group(1).split(",")]
            return " ".join(f"[[{SOURCE_DIR}/{key2sid[k]}|{k}]]" if k in key2sid else f"[{k}]" for k in keys)
        return CITE_RE.sub(sub, text or "")

    topic_stem = find_page(root, TOPIC_DIR, topic) or safe_name(topic)
    planned: Dict[str, str] = {f"{TOPIC_DIR}:{norm_name(topic)}": topic_stem}
    for n in notes:
        name = one_line(n["concept"])
        key = f"{CONCEPT_DIR}:{norm_name(name)}"
        if key not in planned:
            planned[key] = find_page(root, CONCEPT_DIR, name) or safe_name(name)
    planned_ids = {f"{SOURCE_DIR}/{s}" for s in sources} | {f"{TOPIC_DIR}/{topic_stem}"}
    planned_ids |= {f"{CONCEPT_DIR}/{s}" for k, s in planned.items() if k.startswith(CONCEPT_DIR + ":")}
    ctx = Ctx(root, planned_ids, planned)

    concept_names: List[str] = []
    concept_sources: Dict[str, List[str]] = {}
    for n in notes:
        name = one_line(n["concept"])
        stem = planned[f"{CONCEPT_DIR}:{norm_name(name)}"]
        claims = []
        for c in n.get("claims") or []:
            text = one_line(CITE_RE.sub("", c.get("text", "")))
            cited = list(c.get("keys") or []) + [k.strip() for g in CITE_RE.findall(c.get("text", "")) for k in g.split(",")]
            if text:
                claims.append({"text": text, "sources": keys_to_sids(cited)})

        def mutate(st, name=name, n=n, claims=claims):
            st.setdefault("name", name)
            if not st.get("definition") and one_line(n.get("definition", "")):
                st["definition"] = one_line(CITE_RE.sub("", n["definition"]))
            st["claims"] = _merge_claims(st.get("claims", []), claims)
            st["related"] = _merge_names(st.get("related", []), [r for r in (n.get("related") or []) if norm_name(r) != norm_name(name)])
            st["topics"] = _merge_names(st.get("topics", []), [topic])
            st["run_ids"] = list(dict.fromkeys(st.get("run_ids", []) + [run_id]))
            return st

        def conf_for(claims=claims):
            n_src = len({s for c in claims for s in c["sources"]})
            return "high" if n_src >= 3 else "medium" if n_src == 2 else "low"

        _write_state_page(root, f"{CONCEPT_DIR}/{stem}", "concept", name, date, mutate, lambda st: render_concept(st, ctx), tracker,
                          ["autoresearch", "concept"], sources=sorted({s for c in claims for s in c["sources"]}), run_ids=[run_id], confidence=conf_for())
        concept_names.append(name)
        for c in claims:
            for s in c["sources"]:
                concept_sources.setdefault(s, [])
                if name not in concept_sources[s]:
                    concept_sources[s].append(name)

    for sid, e in sources.items():
        def mutate(st, e=e, sid=sid):
            old_e = st.get("evidence", {})
            st["evidence"] = {**e, **{k: v for k, v in old_e.items() if v}}
            st["id"] = sid
            st["concepts"] = _merge_names(st.get("concepts", []), concept_sources.get(sid, []))
            st["run_ids"] = list(dict.fromkeys(st.get("run_ids", []) + [run_id]))
            return st
        _write_state_page(root, f"{SOURCE_DIR}/{sid}", "source", e.get("title") or sid, date, mutate, lambda st: render_source(st, ctx), tracker,
                          ["autoresearch", "source"], run_ids=[run_id])

    gaps = [one_line(g) for g in (run.get("gaps") or []) if one_line(g)]
    conflicts = [{"concept": one_line(c.get("concept", "")), "detail": one_line(c.get("detail", "")), "sources": keys_to_sids(c.get("keys") or [])}
                 for c in (run.get("conflicts") or [])]

    def mutate_topic(st):
        st["topic"] = st.get("topic") or topic
        st["concepts"] = _merge_names(st.get("concepts", []), concept_names)
        st["sources"] = list(dict.fromkeys(st.get("sources", []) + list(sources)))
        titles = st.get("source_titles", {})
        titles.update({s: e.get("title", "") for s, e in sources.items()})
        st["source_titles"] = titles
        runs = [r for r in st.get("runs", []) if r.get("run_id") != run_id]
        runs.append({"run_id": run_id, "date": date, "summary": convert(one_line(run.get("summary", "")))})
        st["runs"] = runs
        st["gaps"] = _merge_names(st.get("gaps", []), gaps)
        known = {(norm_name(c["concept"]), norm_name(c["detail"])) for c in st.get("conflicts", [])}
        st["conflicts"] = st.get("conflicts", []) + [c for c in conflicts if (norm_name(c["concept"]), norm_name(c["detail"])) not in known]
        dl = st.get("deliverables", [])
        have = {(d["run_id"], d["label"]) for d in dl}
        dl += [{"run_id": run_id, "label": str(k), "path": str(v)} for k, v in (run.get("deliverables") or {}).items() if (run_id, str(k)) not in have]
        st["deliverables"] = dl
        return st

    _write_state_page(root, f"{TOPIC_DIR}/{topic_stem}", "topic", topic, date, mutate_topic, lambda st: render_topic(st, ctx), tracker,
                      ["autoresearch", "topic"], sources=len(sources), run_ids=[run_id])

    gaps_added = _write_gaps(root, gaps, topic_stem, run_id, date, tracker)
    index_existed = (root / "index.md").exists()
    if _ensure_ledger_page(root):
        tracker["created"].add(LEDGER_PAGE + ".md")
    if write_index(root):
        tracker["created" if not index_existed else "updated"].add("index.md")
    _vault_files(root, run, topic_stem, len(set(concept_names)), len(sources))
    return {"created": sorted(tracker["created"]), "updated": sorted(tracker["updated"] - tracker["created"]),
            "concepts": len({norm_name(c) for c in concept_names}), "sources": len(sources), "gaps_added": gaps_added}


def _write_gaps(root: Path, gaps: List[str], topic_stem: str, run_id: str, date: str, tracker: dict) -> int:
    path = Path(root) / (GAPS_ID + ".md")
    old = read_text(path) if path.exists() else None
    existing = {norm_name(g["text"]) for g in parse_gap_lines(old or "")}
    new_lines = []
    for g in gaps:
        if norm_name(g) not in existing:
            existing.add(norm_name(g))
            new_lines.append(f"- [ ] {g} (topic: [[{TOPIC_DIR}/{topic_stem}]], run {run_id})")
    if old is not None and not new_lines:
        return 0
    inner = (get_block(old) or "").strip("\n") if old else ""
    inner = inner or "## 開放缺口"
    if new_lines:
        inner += "\n" + "\n".join(new_lines)
    new = set_block(old, inner, frontmatter("研究缺口", date, ["autoresearch", "gaps"]))
    if new != old:
        write_text(path, new)
        (tracker["created"] if old is None else tracker["updated"]).add(GAPS_ID + ".md")
    return len(new_lines)


# ------------------------------------------------------------------ read side

def build_graph(root: Path) -> dict:
    root = Path(root)
    pages = iter_md(root)
    by_cf = {i.casefold(): i for i, _ in pages}
    edges = set()
    meta = {}
    for pid, p in pages:
        text = read_text(p)
        fm, _ = parse_frontmatter(text)
        meta[pid] = fm.get("title") or pid.split("/")[-1]
        for t in wikilinks(text):
            target = by_cf.get(t.casefold())
            if target and target != pid:
                edges.add((pid, target))
    degree: Dict[str, int] = {pid: 0 for pid, _ in pages}
    for s, t in edges:
        degree[s] += 1
        degree[t] += 1
    nodes = [{"id": pid, "label": str(meta[pid]), "type": page_type(pid), "degree": degree[pid]} for pid, _ in pages]
    return {"nodes": nodes, "edges": [{"source": s, "target": t} for s, t in sorted(edges)]}


def write_graph(root: Path, out: Path) -> dict:
    graph = build_graph(root)
    write_text(Path(out), json.dumps(graph, ensure_ascii=False, indent=2))
    return graph


def list_pages(root: Path, query: str = "", limit: int = 200) -> List[dict]:
    q = (query or "").casefold()
    rows = []
    for pid, p in iter_md(Path(root)):
        text = read_text(p)
        fm, body = parse_frontmatter(text)
        title = str(fm.get("title") or pid.split("/")[-1])
        if q and q not in title.casefold() and q not in body.casefold():
            continue
        rows.append({"path": pid + ".md", "title": title, "type": page_type(pid),
                     "updated": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")})
    rows.sort(key=lambda r: (r["updated"], r["path"]), reverse=True)
    return rows[: max(0, int(limit))]


def read_page(root: Path, rel: str) -> dict:
    s = str(rel or "")
    if not s or s.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", s) or Path(s).is_absolute():
        raise ValueError("path must be relative to the knowledge base")
    if ".." in re.split(r"[\\/]", s):
        raise ValueError("path must not contain '..'")
    if not s.lower().endswith(".md"):
        raise ValueError("only .md pages can be read")
    root = Path(root).resolve()
    path = (root / s).resolve()
    if root not in path.parents:
        raise ValueError("path escapes the knowledge base")
    parts = path.relative_to(root).parts
    if any(p.startswith(".") or p.casefold() == "clippings" for p in parts):
        raise ValueError("that folder is not part of the knowledge base")
    if not path.is_file():
        raise FileNotFoundError(s)
    fm, body = parse_frontmatter(read_text(path))
    return {"path": path.relative_to(root).as_posix(), "title": str(fm.get("title") or path.stem), "frontmatter": fm, "body": body}
