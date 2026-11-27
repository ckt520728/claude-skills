"""Source loaders and chunking.

Supported: .pdf (PyMuPDF), .docx, .md/.txt/.markdown, .html/.htm, .json (Zotero/CSL-ish
or plain), http(s) URLs. Google-Drive `.gdoc/.gsheet` files are only *shortcuts* on disk
(no content) and are reported as skipped — read them via the Google Docs connector and
ingest the text with `kg ingest-text` instead.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

TEXT_EXT = {".md", ".markdown", ".txt"}
SUPPORTED = {".pdf", ".docx", ".html", ".htm", ".json"} | TEXT_EXT
SKIP_DIRS = {"$RECYCLE.BIN", "System Volume Information", "node_modules", ".git", "__pycache__", ".venv"}


@dataclass
class LoadedDoc:
    source: str
    title: str
    text: str
    kind: str

    @property
    def sha1(self) -> str:
        return hashlib.sha1(self.text.encode("utf-8", "ignore")).hexdigest()


def _clean(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"-\n(?=[a-z])", "", text)        # de-hyphenate line breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _cut_references(text: str) -> str:
    """Drop the bibliography of a paper: it adds cost and spurious entities."""
    m = None
    for m in re.finditer(r"\n\s*(References|REFERENCES|Bibliography|Literature Cited)\s*\n", text):
        pass
    if m and m.start() > len(text) * 0.5:
        return text[: m.start()]
    return text


def load_pdf(path: Path, max_pages: int | None = None) -> str:
    import fitz  # PyMuPDF
    fitz.TOOLS.mupdf_display_errors(False)
    with fitz.open(path) as doc:
        pages = doc if max_pages is None else [doc[i] for i in range(min(max_pages, len(doc)))]
        return "\n".join(p.get_text("text") for p in pages)


def load_docx(path: Path) -> str:
    import docx
    return "\n".join(p.text for p in docx.Document(str(path)).paragraphs)


def load_html(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    return re.sub(r"<[^>]+>", " ", raw)


def load_path(path: str | Path, max_pages: int | None = None) -> LoadedDoc:
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".pdf":
        text = load_pdf(p, max_pages)
    elif ext == ".docx":
        text = load_docx(p)
    elif ext in (".html", ".htm"):
        text = load_html(p.read_text("utf-8", "ignore"))
    elif ext in TEXT_EXT or ext == ".json":
        text = p.read_text("utf-8", "ignore")
    else:
        raise ValueError(f"Unsupported file type: {p}")
    return LoadedDoc(source=str(p), title=p.stem, text=_cut_references(_clean(text)), kind=ext.lstrip("."))


def load_url(url: str) -> LoadedDoc:
    import httpx
    r = httpx.get(url, follow_redirects=True, timeout=30, headers={"User-Agent": "kgengine/0.1"})
    r.raise_for_status()
    text = load_html(r.text) if "html" in r.headers.get("content-type", "") else r.text
    return LoadedDoc(source=url, title=url.rsplit("/", 1)[-1] or url, text=_clean(text), kind="url")


def discover(roots: list[str], include: str | None = None, exclude: str | None = None,
             exts: set[str] | None = None) -> list[Path]:
    """Walk roots and return supported files. `include`/`exclude` are case-insensitive
    regexes matched against the full path (e.g. include='exercise|physical|alpha|EEG')."""
    exts = exts or SUPPORTED
    inc = re.compile(include, re.I) if include else None
    exc = re.compile(exclude, re.I) if exclude else None
    out: list[Path] = []
    for root in roots:
        rp = Path(root)
        if rp.is_file():
            out.append(rp)
            continue
        for p in rp.rglob("*"):
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if not p.is_file() or p.suffix.lower() not in exts:
                continue
            s = str(p)
            if inc and not inc.search(s):
                continue
            if exc and exc.search(s):
                continue
            out.append(p)
    return sorted(set(out))


def chunk(text: str, size: int = 6000, overlap: int = 400) -> list[str]:
    """Paragraph-aware chunking (~size chars, small overlap)."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, cur = [], ""
    for para in paras:
        while len(para) > size:  # very long paragraph (PDF without blank lines)
            head, para = para[:size], para[size - overlap:]
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(head)
        if len(cur) + len(para) + 2 > size and cur:
            chunks.append(cur)
            cur = cur[-overlap:] + "\n\n" + para
        else:
            cur = f"{cur}\n\n{para}" if cur else para
    if cur:
        chunks.append(cur)
    return chunks
