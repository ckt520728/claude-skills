"""Auto-dictionary learning: find terms the user corrected in the editor.

Pure functions, no I/O.  Token level diff (difflib) between the model output
and the user's edited text; CJK runs are split into single characters, latin
words are kept whole.
"""
import difflib
import re
from collections import OrderedDict

MAX_GLOSSARY_CHARS = 1000
MAX_CJK_TERM = 6
MAX_LATIN_WORDS = 3

_TOKEN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]|[A-Za-z][A-Za-z0-9'\-]*|\d+|[^\s]")
_CJK = re.compile(r"^[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]$")
_LATIN = re.compile(r"^[A-Za-z]")


def _tokens(text):
    return _TOKEN.findall(text or "")


def _kind(token):
    if _CJK.match(token):
        return "cjk"
    if _LATIN.match(token):
        return "latin"
    return None  # punctuation / digits break a run


def _runs(tokens):
    """Split tokens into runs of the same kind; other tokens are separators."""
    runs, cur, kind = [], [], None
    for tok in tokens:
        k = _kind(tok)
        if k is None or k != kind:
            if cur:
                runs.append((kind, cur))
            cur, kind = [], k
        if k is not None:
            cur.append(tok)
    if cur:
        runs.append((kind, cur))
    return runs


def _join(kind, toks):
    return "".join(toks) if kind == "cjk" else " ".join(toks)


def candidates(original_segments, edited_text, known_terms=()):
    """Return [{'term', 'replaced', 'count'}] learned from replacements."""
    if isinstance(original_segments, str):
        original_segments = [original_segments]
    original = " ".join(s for s in (original_segments or []) if s)
    a, b = _tokens(original), _tokens(edited_text)
    known = {str(t).strip().lower() for t in (known_terms or ()) if str(t).strip()}
    found = OrderedDict()
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op != "replace":
            continue
        old_runs = _runs(a[i1:i2])
        new_runs = _runs(b[j1:j2])
        for kind, toks in new_runs:
            term = _join(kind, toks)
            if kind == "cjk" and not 1 <= len(toks) <= MAX_CJK_TERM:
                continue
            if kind == "latin" and not 1 <= len(toks) <= MAX_LATIN_WORDS:
                continue
            if term.lower() in known:
                continue
            same = [r for r in old_runs if r[0] == kind]
            replaced = _join(kind, same[0][1]) if same else " ".join(a[i1:i2])
            if replaced == term:
                continue
            rank = 0
            if kind == "latin" and any(t[0].isupper() for t in toks):
                rank = 1
            elif kind == "cjk" and same and abs(len(same[0][1]) - len(toks)) <= 1:
                rank = 1
            key = (term, replaced)
            if key in found:
                found[key]["count"] += 1
            else:
                found[key] = {"term": term, "replaced": replaced,
                              "count": 1, "_rank": rank, "_order": len(found)}
    ordered = sorted(found.values(),
                     key=lambda c: (-c["_rank"], -c["count"], c["_order"]))
    return [{"term": c["term"], "replaced": c["replaced"], "count": c["count"]}
            for c in ordered]


def _split_terms(value):
    if not value:
        return []
    if isinstance(value, str):
        value = re.split(r"[,，、;；\n]+", value)
    return [str(t).strip() for t in value if str(t).strip()]


def merge_vocabulary(manual, accepted_auto):
    """Comma-joined glossary: manual terms first, then accepted ones, <=1000 chars."""
    seen, out, total = set(), [], 0
    for term in _split_terms(manual) + _split_terms(accepted_auto):
        key = term.lower()
        if key in seen:
            continue
        add = len(term) + (2 if out else 0)
        if total + add > MAX_GLOSSARY_CHARS:
            continue
        seen.add(key)
        out.append(term)
        total += add
    return ", ".join(out)
