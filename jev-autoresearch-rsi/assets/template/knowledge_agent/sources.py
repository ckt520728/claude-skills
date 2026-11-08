"""
Live evidence collection: PubMed (with Europe PMC and Crossref fallbacks), arXiv, ClinicalTrials.gov,
local reference PDFs, NotebookLM and saved answers from services that have no API.

Every source reports what really happened. Nothing falls back to built-in sample papers:
a source that cannot be reached contributes no evidence and says so in its status.
"""

from __future__ import annotations

import difflib
import json
import logging
import os
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

import requests
from pypdf import PdfReader

from .config import CONFIG, REFERENCES_DIR, SAVED_ANSWERS_DIR

logging.getLogger("pypdf").setLevel(logging.ERROR)

ARXIV_API_BASE = "https://export.arxiv.org/api/query"
PUBMED_TOOL_NAME = "RSI_Knowledge_Dashboard"
PUBMED_EMAIL = os.environ.get("NCBI_EMAIL", "")
PUBMED_API_KEY = os.environ.get("NCBI_API_KEY", "")
USER_AGENT = {"User-Agent": f"{PUBMED_TOOL_NAME}/1.0" + (f" (mailto:{PUBMED_EMAIL})" if PUBMED_EMAIL else "")}
TIMEOUT = 25


@dataclass
class Evidence:
    """One citable item. `key` is assigned when it joins the evidence pack."""
    kind: str
    title: str
    text: str = ""
    authors: str = ""
    journal: str = ""
    year: str = ""
    doi: str = ""
    pmid: str = ""
    arxiv_id: str = ""
    nct_id: str = ""
    url: str = ""
    key: str = ""

    def identity(self) -> str:
        return (self.doi or self.pmid or self.arxiv_id or self.nct_id or self.title).lower()

    def citation(self) -> str:
        parts = [p for p in (self.authors, self.title, self.journal, self.year) if p]
        line = " ".join(p if p[-1] in ".?!" else p + "." for p in (x.strip() for x in parts))
        if self.doi:
            line += f" doi:{self.doi}."
        if self.pmid:
            line += f" PMID:{self.pmid}."
        if self.arxiv_id:
            line += f" arXiv:{self.arxiv_id}."
        if self.nct_id:
            line += f" ClinicalTrials.gov {self.nct_id}."
        if self.url and not (self.doi or self.pmid or self.arxiv_id or self.nct_id):
            line += f" {self.url}"
        return line

    def to_dict(self, include_text: bool = False) -> Dict:
        data = asdict(self)
        if not include_text:
            data.pop("text")
        return data


@dataclass
class SourceStatus:
    """What a source actually did during a run, shown to the user."""
    name: str
    state: str  # LIVE | FALLBACK | SAVED | UNAVAILABLE | SKIPPED
    items: int = 0
    detail: str = ""


def _get(url: str, params: Optional[Dict] = None, retries: int = 2) -> requests.Response:
    last: Optional[Exception] = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers=USER_AGENT, timeout=TIMEOUT)
            if resp.status_code < 500 and resp.status_code != 429:
                resp.raise_for_status()
                return resp
            last = RuntimeError(f"HTTP {resp.status_code}")
        except requests.RequestException as e:
            last = e
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(str(last))


def _strip_tags(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


# ---------------------------------------------------------------- literature

def _ncbi_params(extra: Dict) -> Dict:
    params = {"db": "pubmed", "tool": PUBMED_TOOL_NAME, **extra}
    if PUBMED_EMAIL:
        params["email"] = PUBMED_EMAIL
    if PUBMED_API_KEY:
        params["api_key"] = PUBMED_API_KEY
    return params


def _search_ncbi(query: str, limit: int) -> List[Evidence]:
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    ids = _get(f"{base}/esearch.fcgi", _ncbi_params({"term": query, "retmode": "json", "retmax": limit, "sort": "relevance"})).json()["esearchresult"]["idlist"]
    if not ids:
        return []
    root = ET.fromstring(_get(f"{base}/efetch.fcgi", _ncbi_params({"id": ",".join(ids), "retmode": "xml"})).content)
    results = []
    for article in root.findall(".//PubmedArticle"):
        node = article.find(".//Article")
        abstract = " ".join("".join(t.itertext()) for t in node.findall(".//AbstractText"))
        authors = ["{} {}".format(a.findtext("LastName", ""), a.findtext("Initials", "")).strip() for a in node.findall(".//Author") if a.findtext("LastName")]
        doi = next((i.text for i in article.findall(".//ArticleId") if i.get("IdType") == "doi" and i.text), "")
        results.append(Evidence(
            kind="PubMed",
            title="".join(node.find("ArticleTitle").itertext()),
            text=abstract,
            authors=", ".join(authors[:3]) + (", et al" if len(authors) > 3 else ""),
            journal=node.findtext(".//Journal/ISOAbbreviation") or node.findtext(".//Journal/Title", ""),
            year=node.findtext(".//JournalIssue/PubDate/Year") or (node.findtext(".//JournalIssue/PubDate/MedlineDate") or "")[:4],
            doi=doi,
            pmid=article.findtext(".//PMID", ""),
        ))
    return results


def _search_europe_pmc(query: str, limit: int) -> List[Evidence]:
    data = _get(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        {"query": f"({query}) AND SRC:MED", "format": "json", "resultType": "core", "pageSize": limit},
    ).json()
    results = []
    for item in data.get("resultList", {}).get("result", []):
        results.append(Evidence(
            kind="PubMed",
            title=item.get("title", ""),
            text=_strip_tags(item.get("abstractText", "")),
            authors=item.get("authorString", "").rstrip("."),
            journal=(item.get("journalInfo", {}).get("journal", {}) or {}).get("isoabbreviation") or item.get("journalTitle", ""),
            year=str(item.get("pubYear", "")),
            doi=item.get("doi", ""),
            pmid=item.get("pmid", ""),
        ))
    return results


def _crossref_to_evidence(item: Dict, kind: str = "Crossref") -> Evidence:
    names = [f"{a.get('family', '')} {''.join(w[0] for w in a.get('given', '').split() if w)}".strip() for a in item.get("author", []) if a.get("family")]
    return Evidence(
        kind=kind,
        title=_strip_tags((item.get("title") or [""])[0]),
        text=_strip_tags(item.get("abstract", "")),
        authors=", ".join(names[:3]) + (", et al" if len(names) > 3 else ""),
        journal=(item.get("container-title") or [""])[0],
        year=str(((item.get("issued") or {}).get("date-parts") or [[""]])[0][0] or ""),
        doi=item.get("DOI", ""),
    )


def _search_crossref(query: str, limit: int) -> List[Evidence]:
    items = _get("https://api.crossref.org/works", {
        "query.bibliographic": query, "rows": limit, "filter": "type:journal-article",
        "select": "DOI,title,author,container-title,issued,abstract",
    }).json()["message"]["items"]
    return [_crossref_to_evidence(i) for i in items]


def search_literature(queries: Iterable[str], per_query: int) -> Tuple[List[Evidence], SourceStatus]:
    """PubMed first. If NCBI is down, Europe PMC, then Crossref; the status says which one answered."""
    backends: List[Tuple[str, Callable[[str, int], List[Evidence]]]] = [
        ("NCBI PubMed", _search_ncbi), ("Europe PMC", _search_europe_pmc), ("Crossref", _search_crossref),
    ]
    collected: List[Evidence] = []
    used: List[str] = []
    errors: List[str] = []
    down: Set[str] = set()
    for query in queries:
        for name, backend in backends:
            if name in down:
                continue
            try:
                found = backend(query, per_query)
            except Exception as e:
                errors.append(f"{name}: {e}")
                down.add(name)
                continue
            collected.extend(found)
            used.append(name)
            break
    if not used:
        return [], SourceStatus("Literature", "UNAVAILABLE", 0, "; ".join(dict.fromkeys(errors))[:300])
    state = "LIVE" if set(used) == {"NCBI PubMed"} else "FALLBACK"
    with_abstract = sum(1 for e in collected if e.text)
    detail = f"Answered by {', '.join(sorted(set(used)))}; {with_abstract} of {len(collected)} have abstracts"
    if errors:
        detail += f". Failed: {'; '.join(dict.fromkeys(errors))[:160]}"
    return collected, SourceStatus("Literature", state, len(collected), detail)


def search_arxiv(queries: Iterable[str], per_query: int) -> Tuple[List[Evidence], SourceStatus]:
    results: List[Evidence] = []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    errors = []
    for query in queries:
        try:
            root = ET.fromstring(_get(ARXIV_API_BASE, {"search_query": " AND ".join(f"all:{w}" for w in re.findall(r"[\w-]+", query)[:6]), "max_results": per_query, "sortBy": "relevance"}).content)
        except Exception as e:
            errors.append(str(e))
            continue
        for entry in root.findall("a:entry", ns):
            names = [a.findtext("a:name", "", ns) for a in entry.findall("a:author", ns)]
            url = entry.findtext("a:id", "", ns)
            results.append(Evidence(
                kind="arXiv preprint",
                title=re.sub(r"\s+", " ", entry.findtext("a:title", "", ns)).strip(),
                text=re.sub(r"\s+", " ", entry.findtext("a:summary", "", ns)).strip(),
                authors=", ".join(names[:3]) + (", et al" if len(names) > 3 else ""),
                journal="arXiv (not peer reviewed)",
                year=entry.findtext("a:published", "", ns)[:4],
                arxiv_id=url.split("/abs/")[-1],
                url=url,
            ))
    if errors and not results:
        return [], SourceStatus("arXiv", "UNAVAILABLE", 0, errors[0][:200])
    return results, SourceStatus("arXiv", "LIVE", len(results))


def search_trials(queries: Iterable[str], per_query: int) -> Tuple[List[Evidence], SourceStatus]:
    """Ongoing trials from ClinicalTrials.gov, the registry of record for this question."""
    results: List[Evidence] = []
    errors = []
    for query in queries:
        try:
            studies = _get("https://clinicaltrials.gov/api/v2/studies", {
                "query.term": query, "pageSize": per_query,
                "filter.overallStatus": "RECRUITING|ACTIVE_NOT_RECRUITING|NOT_YET_RECRUITING",
            }).json().get("studies", [])
        except Exception as e:
            errors.append(str(e))
            continue
        for study in studies:
            p = study.get("protocolSection", {})
            ident = p.get("identificationModule", {})
            status = p.get("statusModule", {})
            design = p.get("designModule", {})
            arms = [i.get("name", "") for i in p.get("armsInterventionsModule", {}).get("interventions", [])]
            nct = ident.get("nctId", "")
            results.append(Evidence(
                kind="ClinicalTrials.gov",
                title=ident.get("briefTitle", ""),
                text=(
                    f"Status: {status.get('overallStatus', '')}. Phase: {', '.join(design.get('phases', []))}. "
                    f"Enrollment: {design.get('enrollmentInfo', {}).get('count', 'not stated')}. "
                    f"Interventions: {', '.join(arms)}. Conditions: {', '.join(p.get('conditionsModule', {}).get('conditions', []))}. "
                    f"Summary: {p.get('descriptionModule', {}).get('briefSummary', '')}"
                ),
                year=(status.get("startDateStruct", {}).get("date") or "")[:4],
                nct_id=nct,
                url=f"https://clinicaltrials.gov/study/{nct}",
            ))
    if errors and not results:
        return [], SourceStatus("ClinicalTrials.gov", "UNAVAILABLE", 0, errors[0][:200])
    return results, SourceStatus("ClinicalTrials.gov", "LIVE", len(results))


# ---------------------------------------------------------------- local reference PDFs

def _compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _title_on_page(title: str, page_compact: str) -> bool:
    """PDF text often loses spacing, so compare without it, and allow ligature and hyphen losses."""
    words = [_compact(w) for w in title.split() if len(_compact(w)) > 2]
    if len(words) < 3:
        return False
    return sum(w in page_compact for w in words) / len(words) >= 0.8


def _crossref_record(doi: str) -> Optional[Evidence]:
    try:
        data = _get("https://api.crossref.org/works/" + requests.utils.quote(doi, safe="/()"), retries=1).json()["message"]
    except Exception:
        return None
    return _crossref_to_evidence(data, "Reference PDF")


def _identify_pdf(pdf: Path, meta, first_page: str, text: str) -> Optional[Evidence]:
    """
    Find the paper's own record. PDFs also contain the DOIs of everything they cite, so a DOI is
    accepted only when its registered title appears on the first page of this file.
    """
    page = _compact(first_page)
    declared = [str(meta.get("/doi", "") or "")] + re.findall(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", str(meta.get("/Subject", "") or ""))
    found_in_text = re.findall(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", text)
    candidates = list(dict.fromkeys(d.rstrip(".,;)") for d in declared + found_in_text if d))
    for doi in candidates[:12]:
        record = _crossref_record(doi)
        if record and _title_on_page(record.title, page):
            return record
    query = re.sub(r"[_\s]+", " ", re.sub(r"^[A-Za-z-]+[ _]?\d{4}[ _]?", "", pdf.stem)).strip()
    try:
        for hit in _search_crossref(query, 3):
            if _title_on_page(hit.title, page):
                hit.kind = "Reference PDF"
                return hit
    except Exception:
        pass
    return None


def load_reference_pdfs(max_chars: int = 9000) -> Tuple[List[Evidence], SourceStatus]:
    results: List[Evidence] = []
    failed = []
    unmatched = []
    for pdf in sorted(REFERENCES_DIR.glob("*.pdf")):
        try:
            reader = PdfReader(str(pdf))
            pages = [re.sub(r"\s+", " ", p.extract_text() or "") for p in reader.pages[:8]]
            text = " ".join(pages)
            item = _identify_pdf(pdf, reader.metadata or {}, " ".join(pages[:1]), text)
            if item is None:
                # No registered record, such as a drug label: name the local file rather than guess.
                unmatched.append(pdf.name)
                item = Evidence(kind="Reference PDF (no registered record)", title=re.sub(r"[_\s]+", " ", pdf.stem).strip(), journal="Local file in references/")
            item.text = text[:max_chars]
            results.append(item)
        except Exception as e:
            failed.append(f"{pdf.name}: {e}")
    state = "LIVE" if results else "UNAVAILABLE"
    detail = "; ".join(filter(None, [f"No registered record for: {', '.join(unmatched)}" if unmatched else "", "; ".join(failed)]))
    return results, SourceStatus("Reference PDFs", state, len(results), detail[:300])


# ---------------------------------------------------------------- NotebookLM and OpenEvidence

def query_notebook(questions: Iterable[str], timeout: int = 150) -> Tuple[List[Evidence], SourceStatus]:
    """Query a NotebookLM notebook through the `nlm` CLI. Answers are treated as secondary evidence."""
    notebook = CONFIG.get("sources", {}).get("notebooklm_id", "")
    # Prefer the uv-tool install (same package as the notebooklm-mcp server); an older nlm can sit earlier on PATH.
    local = Path.home() / ".local" / "bin" / ("nlm.exe" if os.name == "nt" else "nlm")
    binary = str(local) if local.exists() else (shutil.which("nlm") or str(local))
    if not Path(binary).exists():
        return [], SourceStatus("NotebookLM", "UNAVAILABLE", 0, "The nlm command is not installed")
    results: List[Evidence] = []
    error = ""
    for question in questions:
        prompt = f"{question} Answer from the sources. Do not include any personal or case identifiers."
        try:
            done = subprocess.run(
                [binary, "notebook", "query", notebook, prompt, "--json"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                # nlm is Python; on Windows a piped stdout defaults to the ANSI code page and garbles Chinese.
                env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
            )
            data = json.loads(done.stdout or "{}")
        except (subprocess.TimeoutExpired, ValueError, OSError) as e:
            error = str(e)
            continue
        body = data.get("value") or data
        answer = body.get("answer") if isinstance(body, dict) else ""
        if not answer:
            error = str(data.get("error") or done.stderr or "No answer returned")[:220]
            continue
        results.append(Evidence(kind="NotebookLM answer (secondary)", title=f"Notebook answer: {question}", text=str(answer), journal=f"NotebookLM notebook {notebook}"))
    if results:
        return results, SourceStatus("NotebookLM", "LIVE", len(results), error)
    detail = error or "No questions asked"
    if "auth" in detail.lower():
        detail = "Login expired. Run: nlm login --force"
    return [], SourceStatus("NotebookLM", "UNAVAILABLE", 0, detail)


def load_saved_answers(questions: Iterable[str], run_dir: Path) -> Tuple[List[Evidence], SourceStatus]:
    """
    For services with no API, such as sites that need a signed-in browser. Reads answers the user saved
    to references/saved_answers/ and writes the questions to ask, for the next run.
    """
    (run_dir / "questions_to_ask.md").write_text(
        "# Questions to ask a specialist service or expert\n\n"
        "Save each answer as a .md or .txt file in `references/saved_answers/`. The next run will include them.\n\n"
        + "\n".join(f"- {q}" for q in questions) + "\n",
        encoding="utf-8",
    )
    results = []
    if SAVED_ANSWERS_DIR.exists():
        for path in sorted(list(SAVED_ANSWERS_DIR.glob("*.md")) + list(SAVED_ANSWERS_DIR.glob("*.txt"))):
            results.append(Evidence(kind="Saved answer (secondary)", title=f"Saved answer: {path.stem}", text=path.read_text(encoding="utf-8", errors="replace")[:9000]))
    state = "SAVED" if results else "UNAVAILABLE"
    detail = f"{len(results)} saved answers used" if results else "None saved yet. Questions were written to questions_to_ask.md in the run folder"
    return results, SourceStatus("Saved answers", state, len(results), detail)


# ---------------------------------------------------------------- final citation lookup

def _title_ratio(registered: str, cited: str) -> float:
    a, b = _compact(registered), _compact(cited)
    return difflib.SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def citation_problems(item: Evidence) -> List[str]:
    """A DOI must exist AND be registered to this title: a real DOI can belong to a different paper."""
    problems: List[str] = []
    if item.doi:
        try:
            resp = requests.get("https://api.crossref.org/works/" + requests.utils.quote(item.doi, safe="/()"), headers=USER_AGENT, timeout=TIMEOUT)
            if resp.status_code == 404:
                held = requests.get("https://doi.org/api/handles/" + requests.utils.quote(item.doi, safe="/()"), headers=USER_AGENT, timeout=TIMEOUT)
                if held.status_code == 404:
                    problems.append(f"DOI {item.doi} was not found ({item.title[:60]})")
            elif resp.ok:
                titles = resp.json()["message"].get("title") or []
                if titles and _title_ratio(_strip_tags(titles[0]), item.title) < 0.6:
                    problems.append(f"DOI {item.doi} is registered to a different title ({item.title[:60]})")
            else:
                problems.append(f"DOI {item.doi} could not be checked ({item.title[:60]})")
        except (requests.RequestException, ValueError):
            problems.append(f"DOI {item.doi} could not be checked ({item.title[:60]})")
    if item.arxiv_id:
        try:
            resp = requests.get(ARXIV_API_BASE, params={"id_list": item.arxiv_id, "max_results": 1}, headers=USER_AGENT, timeout=TIMEOUT)
            found = re.findall(r"<title>([^<]+)</title>", resp.text)[1:2]
            if not found:
                problems.append(f"arXiv {item.arxiv_id} was not found ({item.title[:60]})")
            elif _title_ratio(found[0], item.title) < 0.6:
                problems.append(f"arXiv {item.arxiv_id} is registered to a different title ({item.title[:60]})")
        except requests.RequestException:
            problems.append(f"arXiv {item.arxiv_id} could not be checked ({item.title[:60]})")
    return problems
