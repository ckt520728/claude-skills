"""Offline tests for the knowledge base writer (kb.py) and its self-improvement loop (kb_rsi.py). Temp dirs only."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge_agent import kb, kb_rsi
from knowledge_agent.kb_rsi import Proposal

EVIDENCE = [
    {"kind": "PubMed", "title": "Self-improving agents: a trial", "authors": "Lee J, Park S, et al", "journal": "Nature", "year": "2024", "doi": "10.1000/abc", "pmid": "111", "key": "E1"},
    {"kind": "arXiv preprint", "title": "Autoresearch loops", "authors": "Yann LeCun", "journal": "arXiv", "year": "2025", "arxiv_id": "2501.00001", "key": "E2"},
    {"kind": "ClinicalTrials.gov registry entry", "title": "A registry study", "nct_id": "NCT01234567", "key": "E3"},
]


def make_run(run_id="r1", topic="Agentic autoresearch (RSI) [2026]", **over):
    run = {
        "run_id": run_id, "topic": topic, "date": "2026-11-08",
        "summary": "Agents improve themselves [E1] and loops matter [E2, E3].",
        "evidence": [dict(e) for e in EVIDENCE],
        "notes": [
            {"concept": "Recursive self-improvement", "definition": "A system that improves its own improver.",
             "claims": [{"text": "Loops with held-out checks avoid regressions [E1]", "keys": ["E1"]},
                        {"text": "Gains saturate quickly", "keys": ["E2", "E3"]}], "related": ["Autoresearch", "Missing concept"]},
            {"concept": "Autoresearch", "definition": "Agents that run research loops.",
             "claims": [{"text": "Autoresearch needs verified evidence", "keys": ["E2"]}], "related": ["Recursive self-improvement"]},
        ],
        "gaps": ["No long-horizon benchmark", "Unclear cost curve"],
        "conflicts": [{"concept": "Autoresearch", "detail": "E2 and E3 disagree on scale", "keys": ["E2", "E3"]}],
        "deliverables": {"paper": str(Path(__file__).resolve())},
    }
    run.update(over)
    return run


@pytest.fixture
def root(tmp_path):
    return tmp_path / "vault" / "KB"


def snapshot(folder: Path) -> dict:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


def put(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))


def managed(body: str) -> str:
    return f"---\ntitle: x\n---\n{kb.BEGIN}\n{body}\n{kb.END}\n"


def perfect_kb(root: Path) -> None:
    """A tiny KB with no broken links, orphans, unsourced claims, duplicates, single-source concepts or gaps."""
    put(root, "index.md", managed("## Home\n- [[概念/A]]"))
    put(root, "概念/A.md", managed("## 定義\nx\n\n## Claims（主張）\n- first ([[來源/pmid-111]])\n- second ([[來源/pmid-222]])"))
    put(root, "來源/pmid-111.md", managed("source one"))
    put(root, "來源/pmid-222.md", managed("source two"))


# ------------------------------------------------------------------ names and paths

def test_safe_name_is_windows_safe_and_keeps_cjk():
    bad = 'a<b>c:d"e/f\\g|h?i*j'
    out = kb.safe_name(bad)
    assert not set('<>:"|?*\\/') & set(out)
    assert kb.safe_name("腎臟病 與 糖尿病") == "腎臟病 與 糖尿病"
    long = kb.safe_name("字" * 300)
    assert len(long) <= 80 and long.startswith("字")
    assert kb.safe_name("CON") != "CON"
    assert kb.safe_name("???") == "untitled"
    assert kb.safe_name("x" * 200) != kb.safe_name("x" * 201)  # truncation keeps names distinct


def test_norm_name_identity():
    assert kb.norm_name("  Recursive   Self-Improvement! ") == kb.norm_name("recursive self improvement")
    assert kb.norm_name("腎臟，病") == kb.norm_name("腎臟 病")
    assert kb.norm_name("Alpha") != kb.norm_name("Beta")


def test_kb_root_uses_config_then_default(monkeypatch):
    monkeypatch.setitem(kb.CONFIG, "knowledge_base", {"root": "X:/somewhere"})
    assert kb.kb_root() == Path("X:/somewhere")
    monkeypatch.setitem(kb.CONFIG, "knowledge_base", {})
    assert kb.kb_root() == kb.KB_ROOT_DEFAULT
    assert kb.vault_kb_dir(Path("a/b/c")) == Path("a/b")


# ------------------------------------------------------------------ integrate_run

def test_integrate_run_writes_expected_pages(root):
    result = kb.integrate_run(root, make_run())
    assert set(result) == {"created", "updated", "concepts", "sources", "gaps_added"}
    assert result["concepts"] == 2 and result["sources"] == 3 and result["gaps_added"] == 2
    assert result["updated"] == [] and "index.md" in result["created"]
    topic_stem = kb.safe_name("Agentic autoresearch (RSI) [2026]")
    topic = (root / "主題" / f"{topic_stem}.md").read_text(encoding="utf-8")
    assert "[[概念/Recursive self-improvement]]" in topic and "[[來源/doi-10.1000_abc]]" in topic
    assert "[[來源/doi-10.1000_abc|E1]]" in topic          # [E#] in the summary became a link
    assert "run r1" in topic and "No long-horizon" not in "".join(l for l in topic.splitlines() if "[ ]" in l)
    fm, _ = kb.parse_frontmatter(topic)
    assert fm["title"] == "Agentic autoresearch (RSI) [2026]" and "autoresearch" in fm["tags"] and fm["run_ids"] == ["r1"]
    assert (root / "來源" / "arxiv-2501.00001.md").exists() and (root / "來源" / "NCT01234567.md").exists()
    src = (root / "來源" / "doi-10.1000_abc.md").read_text(encoding="utf-8")
    assert "Lee J" in src and "https://doi.org/10.1000/abc" in src and "[[概念/Recursive self-improvement]]" in src
    assert (root / "RSI ledger.md").exists() and "[[RSI ledger]]" in (root / "index.md").read_text(encoding="utf-8")


def test_every_concept_claim_line_ends_with_source_links(root):
    kb.integrate_run(root, make_run())
    text = (root / "概念" / "Recursive self-improvement.md").read_text(encoding="utf-8")
    claims = kb_rsi.claim_lines(text)
    assert len(claims) == 2
    assert claims[0].endswith("([[來源/doi-10.1000_abc]])")
    assert claims[1].endswith("([[來源/arxiv-2501.00001]], [[來源/NCT01234567]])")
    assert "[E1]" not in text.split(kb.BEGIN)[1].split("## 相關概念")[0]
    assert "Missing concept" in text and "[[概念/Missing concept]]" not in text   # no link to a page that does not exist
    assert kb_rsi.fitness(root)["broken_links"] == 0


def test_claim_with_unknown_key_stays_unsourced_and_is_counted(root):
    run = make_run(notes=[{"concept": "Orphan idea", "definition": "d", "claims": [{"text": "Cited nowhere [E9]", "keys": ["E9"]}], "related": []}])
    kb.integrate_run(root, run)
    assert kb_rsi.fitness(root)["unsourced_claims"] == 1


def test_mindmap_escapes_brackets_and_parentheses(root):
    kb.integrate_run(root, make_run(topic="Topic (with) [brackets] {and} braces", notes=[
        {"concept": "Concept (x) [y]", "definition": "d", "claims": [{"text": "c", "keys": ["E1"]}], "related": []}]))
    topic = next((root / "主題").glob("*.md")).read_text(encoding="utf-8")
    block = topic.split("```mermaid")[1].split("```")[0]
    lines = block.strip().splitlines()
    assert lines[0] == "mindmap"
    root_inner = lines[1].strip()[len("root(("):-len("))")]
    for node in [root_inner] + [l.strip() for l in lines[2:]]:
        assert not set("()[]{}") & set(node), node
    assert mm_ok("a (b)") and "(" not in kb.mm("a (b)")


def mm_ok(text):
    return not set("()[]{}") & set(kb.mm(text))


def test_merge_safety_outside_markers_is_byte_for_byte(root):
    kb.integrate_run(root, make_run())
    top, bottom = "USER-TOP 我的筆記\r\nline two\r\n", "\r\nUSER-BOTTOM 結尾 \u00e9\r\n"
    before = {}
    for pid, p in kb.iter_md(root):
        t = p.read_bytes().decode("utf-8")
        t = t.replace(kb.BEGIN, top + kb.BEGIN).replace(kb.END, kb.END + bottom)
        p.write_bytes(t.encode("utf-8"))
        before[pid] = t

    def outside(t):
        b, e = t.index(kb.BEGIN), t.index(kb.END) + len(kb.END)
        return t[:b].encode("utf-8"), t[e:].encode("utf-8")

    second = make_run("r2", notes=[{"concept": "Recursive self-improvement", "definition": "ignored: first definition wins",
                                    "claims": [{"text": "loops with HELD-OUT checks avoid regressions!", "keys": ["E3"]},
                                               {"text": "A brand new claim", "keys": ["E1"]}], "related": []}])
    result = kb.integrate_run(root, second)
    assert "概念/Recursive self-improvement.md" in result["updated"]
    for pid, p in kb.iter_md(root):
        if pid in before:
            assert outside(p.read_bytes().decode("utf-8")) == outside(before[pid]), pid
    text = (root / "概念" / "Recursive self-improvement.md").read_bytes().decode("utf-8")
    claims = kb_rsi.claim_lines(text)
    assert len(claims) == 3                                   # the near-duplicate claim was merged, not repeated
    assert claims[0].count("[[來源/") == 2 and "NCT01234567" in claims[0]   # its extra source was merged in
    assert "ignored" not in text and "A system that improves its own improver." in text
    state = kb.load_state(text)
    assert state["run_ids"] == ["r1", "r2"]


def test_gaps_dedupe_and_keep_checked_boxes(root):
    first = kb.integrate_run(root, make_run())
    assert first["gaps_added"] == 2
    gaps = root / "缺口" / "gaps.md"
    gaps.write_bytes(gaps.read_bytes().decode("utf-8").replace("- [ ] Unclear cost curve", "- [x] Unclear cost curve").encode("utf-8"))
    second = kb.integrate_run(root, make_run("r2", gaps=["no long-horizon BENCHMARK!", "Unclear cost curve", "Brand new gap"]))
    assert second["gaps_added"] == 1
    text = gaps.read_text(encoding="utf-8")
    assert text.count("No long-horizon benchmark") == 1 and "- [x] Unclear cost curve" in text
    assert kb.open_gaps(root) == ["No long-horizon benchmark", "Brand new gap"]
    stem = kb.safe_name("Agentic autoresearch (RSI) [2026]")
    assert kb.open_gaps(root, "Agentic autoresearch (RSI) [2026]") == ["No long-horizon benchmark", "Brand new gap"]
    assert kb.open_gaps(root, "Another topic") == [] and stem


def test_vault_index_gets_one_line_and_log_one_line_per_run(root):
    vault = root.parent
    kb.integrate_run(root, make_run("r1"))
    kb.integrate_run(root, make_run("r2"))
    kb.integrate_run(root, make_run("r2"))                    # the same run again must not add another line
    index = (vault / "index.md").read_text(encoding="utf-8")
    log = (vault / "log.md").read_text(encoding="utf-8")
    assert index.count("[[KB/index") == 1
    assert log.count("[run:r1]") == 1 and log.count("[run:r2]") == 1
    assert sum(1 for l in log.splitlines() if l.startswith("- ")) == 2


def test_existing_vault_index_is_appended_not_rewritten(root):
    vault = root.parent
    vault.mkdir(parents=True)
    original = "---\ntitle: 知識庫索引\n---\n| 主題 | 筆記 |\n|---|---|\n| a | b |"
    (vault / "index.md").write_bytes(original.encode("utf-8"))
    kb.integrate_run(root, make_run())
    now = (vault / "index.md").read_text(encoding="utf-8")
    assert now.startswith(original) and now.count("[[KB/index") == 1


def test_integrate_writes_only_inside_root_and_vault_files(root):
    kb.integrate_run(root, make_run(topic="../../escape/attempt"))
    assert {p.name for p in root.parent.iterdir()} == {"KB", "index.md", "log.md"}
    for pid, p in kb.iter_md(root):
        assert root.resolve() in p.resolve().parents or p.resolve().parent == root.resolve()


def test_unbalanced_markers_refuse_to_write(root):
    kb.integrate_run(root, make_run())
    page = root / "概念" / "Autoresearch.md"
    page.write_bytes(page.read_bytes().replace(kb.END.encode(), b""))
    with pytest.raises(ValueError):
        kb.integrate_run(root, make_run("r2"))


def test_clippings_folder_is_never_touched_or_listed(root):
    kb.integrate_run(root, make_run())
    put(root, "Clippings/raw.md", "# raw clip [[nowhere]]")
    before = (root / "Clippings" / "raw.md").read_bytes()
    kb.integrate_run(root, make_run("r2"))
    assert (root / "Clippings" / "raw.md").read_bytes() == before
    assert all(not n["id"].startswith("Clippings") for n in kb.build_graph(root)["nodes"])
    assert kb_rsi.fitness(root)["broken_links"] == 0


# ------------------------------------------------------------------ read side

@pytest.mark.parametrize("bad", ["../x.md", "a/../../x.md", "a\\..\\x.md", "/etc/x.md", "\\x.md", "C:/Windows/x.md", "C:\\x.md", "概念/A.txt", "概念/A", "", "Clippings/raw.md", ".rsi/x.md"])
def test_read_page_rejects_bad_paths(root, bad):
    kb.integrate_run(root, make_run())
    put(root, "Clippings/raw.md", "x")
    with pytest.raises(ValueError):
        kb.read_page(root, bad)


def test_read_page_returns_frontmatter_and_body(root):
    kb.integrate_run(root, make_run())
    page = kb.read_page(root, "概念/Autoresearch.md")
    assert page["path"] == "概念/Autoresearch.md" and page["title"] == "Autoresearch"
    assert page["frontmatter"]["title"] == "Autoresearch" and "## 定義" in page["body"]
    with pytest.raises(FileNotFoundError):
        kb.read_page(root, "概念/nope.md")


def test_graph_nodes_edges_and_write(root, tmp_path):
    kb.integrate_run(root, make_run())
    out = tmp_path / "out" / "kb_graph.json"
    graph = kb.write_graph(root, out)
    assert json.loads(out.read_text(encoding="utf-8")) == graph
    nodes = {n["id"]: n for n in graph["nodes"]}
    assert nodes["概念/Recursive self-improvement"]["type"] == "concept" and nodes["index"]["type"] == "other"
    assert any(n["type"] == "topic" for n in nodes.values()) and nodes["缺口/gaps"]["type"] == "gap"
    ids = set(nodes)
    assert all(e["source"] in ids and e["target"] in ids for e in graph["edges"])
    edge = {"source": "概念/Autoresearch", "target": "概念/Recursive self-improvement"}
    assert edge in graph["edges"]
    assert nodes["概念/Autoresearch"]["degree"] >= 3


def test_list_pages_filters_by_title_and_body(root):
    kb.integrate_run(root, make_run())
    assert {r["title"] for r in kb.list_pages(root, "recursive")} >= {"Recursive self-improvement"}
    by_body = kb.list_pages(root, "HELD-OUT checks")
    assert by_body and all(r["type"] in {"concept", "topic"} for r in by_body)
    assert kb.list_pages(root, "zzz-not-present") == []
    assert len(kb.list_pages(root, "", limit=2)) == 2
    assert set(kb.list_pages(root)[0]) == {"path", "title", "type", "updated"}


# ------------------------------------------------------------------ fitness

def test_fitness_empty_kb_scores_zero(tmp_path):
    f = kb_rsi.fitness(tmp_path / "does-not-exist")
    assert f["pages"] == 0 and f["score"] == 0.0
    empty = tmp_path / "e"
    empty.mkdir()
    assert kb_rsi.fitness(empty)["score"] == 0.0


def test_fitness_perfect_kb_is_one(root):
    perfect_kb(root)
    f = kb_rsi.fitness(root)
    assert f["score"] == 1.0 and f["pages"] == 4 and f["concepts"] == 1
    assert (f["broken_links"], f["orphans"], f["unsourced_claims"], f["open_gaps"], f["single_source_concepts"]) == (0, 0, 0, 0, 0)
    assert set(f["details"]) >= {"broken", "orphans", "unsourced"}


def test_fitness_counts_broken_links_and_lowers_score(root):
    perfect_kb(root)
    base = kb_rsi.fitness(root)["score"]
    put(root, "index.md", managed("## Home\n- [[概念/A]]\n- [[概念/Nope]] and [[來源/pmid-111|alias]] and [[來源/pmid-222#h]] and [[概念/A]]"))
    f = kb_rsi.fitness(root)
    assert f["broken_links"] == 1 and f["details"]["broken"] == [{"page": "index", "target": "概念/Nope"}]
    assert f["score"] < base
    put(root, "index.md", managed("- [[概念/A]]\n- [[概念/Nope]] [[概念/Nope2]]"))
    assert kb_rsi.fitness(root)["broken_links"] == 2 and kb_rsi.fitness(root)["score"] < f["score"]


def test_fitness_ignores_links_in_code_fences(root):
    perfect_kb(root)
    put(root, "index.md", managed("- [[概念/A]]\n```\n[[概念/Fake]]\n```"))
    assert kb_rsi.fitness(root)["broken_links"] == 0


def test_fitness_counts_orphans_and_lowers_score(root):
    perfect_kb(root)
    base = kb_rsi.fitness(root)["score"]
    put(root, "概念/Lonely.md", managed("## Claims（主張）\n- c ([[來源/pmid-111]])"))
    put(root, "缺口/gaps.md", managed("## 開放缺口"))                # gaps and index are never orphans
    f = kb_rsi.fitness(root)
    assert f["orphans"] == 1 and f["details"]["orphans"] == ["概念/Lonely"] and f["score"] < base
    put(root, "概念/Lonely2.md", managed("## Claims（主張）\n- c ([[來源/pmid-111]])"))
    assert kb_rsi.fitness(root)["orphans"] == 2


def test_self_link_does_not_rescue_an_orphan(root):
    perfect_kb(root)
    put(root, "概念/Lonely.md", managed("## Claims（主張）\n- c ([[來源/pmid-111]])\nsee [[概念/Lonely]]"))
    assert kb_rsi.fitness(root)["orphans"] == 1


def test_fitness_counts_unsourced_claims_and_lowers_score(root):
    perfect_kb(root)
    base = kb_rsi.fitness(root)["score"]
    put(root, "概念/A.md", managed("## Claims（主張）\n- first ([[來源/pmid-111]])\n- second ([[來源/pmid-222]])\n- nobody cites this\n- 也沒有來源"))
    f = kb_rsi.fitness(root)
    assert f["unsourced_claims"] == 2 and f["score"] < base
    assert [u["claim"] for u in f["details"]["unsourced"]] == ["- nobody cites this", "- 也沒有來源"]
    # bullets outside the Claims heading, and claims outside the managed block, are not counted
    put(root, "概念/A.md", managed("## Claims（主張）\n- first ([[來源/pmid-111]])\n- second ([[來源/pmid-222]])\n\n## Notes\n- plain bullet") + "\n## Claims\n- user bullet\n")
    assert kb_rsi.fitness(root)["unsourced_claims"] == 0


def test_fitness_counts_single_source_and_gaps(root):
    perfect_kb(root)
    put(root, "概念/A.md", managed("## Claims（主張）\n- first ([[來源/pmid-111]])\n- again ([[來源/pmid-111]])"))
    f = kb_rsi.fitness(root)
    assert f["single_source_concepts"] == 1 and f["score"] < 1.0
    put(root, "缺口/gaps.md", managed("- [ ] one\n- [x] done\n- [ ] two"))
    g = kb_rsi.fitness(root)
    assert g["open_gaps"] == 2 and g["score"] < f["score"]


def test_fitness_score_is_strictly_monotone_in_each_count():
    base = {k: 0 for k in kb_rsi.WEIGHTS}
    totals = {d: 40 for d in kb_rsi.DENOMINATORS.values()}
    assert kb_rsi._score(base, totals) == 1.0
    for k in kb_rsi.WEIGHTS:
        prev = 1.0
        for n in range(1, 30):
            s = kb_rsi._score({**base, k: n}, totals)
            assert s < prev and 0 <= s <= 1
            prev = s


def test_fitness_does_not_penalise_growth():
    """The 2026-11-08 case: the wiki grew and every share improved, yet v1 (absolute counts) fell 0.906 -> 0.879."""
    zero = {k: 0 for k in kb_rsi.WEIGHTS}
    before = kb_rsi._score({**zero, "single_source_concepts": 10, "open_gaps": 6}, {"concepts": 14, "gaps": 8})
    after = kb_rsi._score({**zero, "single_source_concepts": 21, "open_gaps": 20}, {"concepts": 33, "gaps": 30})
    assert after > before
    # Same proportions at twice the size: identical score.
    small = kb_rsi._score({**zero, "orphans": 1, "single_source_concepts": 3}, {"linkable_pages": 10, "concepts": 6})
    big = kb_rsi._score({**zero, "orphans": 2, "single_source_concepts": 6}, {"linkable_pages": 20, "concepts": 12})
    assert small == big


def test_fitness_reports_rates_and_totals(root):
    perfect_kb(root)
    put(root, "缺口/gaps.md", managed("- [ ] one\n- [x] done\n- [ ] two"))
    f = kb_rsi.fitness(root)
    assert f["score_basis"] == "normalised-v2"
    assert f["totals"]["gaps"] == 3 and f["open_gaps"] == 2 and f["rates"]["open_gaps"] == round(2 / 3, 6)
    assert set(f["rates"]) == set(kb_rsi.WEIGHTS) and all(0 <= v <= 1 for v in f["rates"].values())


# ------------------------------------------------------------------ proposals and improve

def typo_kb(root: Path) -> None:
    perfect_kb(root)
    put(root, "index.md", managed("## Home\n- [[概念/A]]\n- [[來源/pmid-1111]]"))     # typo for 來源/pmid-111


def test_propose_repair_link_needs_a_close_match(root):
    typo_kb(root)
    props = kb_rsi.propose(root)
    assert [(p.kind, p.target, p.detail["new"], p.metric) for p in props] == [("repair_link", "來源/pmid-1111", "來源/pmid-111", "broken_links")]
    put(root, "index.md", managed("- [[概念/A]]\n- [[來源/completely different]]"))
    assert kb_rsi.propose(root) == []                                          # no page is close enough: no proposal
    assert kb_rsi.propose(root) == kb_rsi.propose(root)                        # deterministic


def test_improve_promotes_repair_link_and_changes_real_files(root, tmp_path):
    typo_kb(root)
    ledger, queue = tmp_path / "led" / "ledger.jsonl", tmp_path / "queue.md"
    queue.write_text("# queue\n", encoding="utf-8")
    before = kb_rsi.fitness(root)
    decisions = kb_rsi.improve(root, ledger, queue)
    assert [d["decision"] for d in decisions] == ["PROMOTE"]
    d = decisions[0]
    assert set(d) == {"kind", "target", "decision", "metric", "before", "after", "delta_score", "reason", "time"}
    assert (d["kind"], d["metric"], d["before"], d["after"]) == ("repair_link", "broken_links", 1, 0) and d["delta_score"] > 0
    after = kb_rsi.fitness(root)
    assert after["score"] > before["score"] and after["broken_links"] == 0
    assert "[[來源/pmid-111]]" in (root / "index.md").read_text(encoding="utf-8") and "pmid-1111" not in (root / "index.md").read_text(encoding="utf-8")
    assert kb_rsi.verify_ledger(ledger) and len(kb_rsi.ledger_entries(ledger)) == 1
    line = queue.read_text(encoding="utf-8").splitlines()[-1]
    assert " PROMOTE repair_link 來源/pmid-1111 Δscore=+0." in line and line.startswith("- 20")
    assert kb_rsi.improve(root, ledger, queue) == []                           # nothing left to improve


def test_improve_rejects_proposal_that_does_not_reduce_its_metric(root, tmp_path, monkeypatch):
    typo_kb(root)
    real_before = snapshot(root)
    ledger = tmp_path / "ledger.jsonl"
    crafted = Proposal("repair_link", "來源/pmid-1111", {"new": "來源/pmid-111", "pages": ["概念/A"]}, "broken_links")   # A has no such link
    monkeypatch.setattr(kb_rsi, "propose", lambda r: [crafted])
    decisions = kb_rsi.improve(root, ledger)
    assert [d["decision"] for d in decisions] == ["REJECT"] and "did not fall" in decisions[0]["reason"]
    assert snapshot(root) == real_before                                       # the real KB is untouched
    assert kb_rsi.verify_ledger(ledger)
    assert kb_rsi.ledger_entries(ledger)[0]["decision"] == "REJECT"


def test_improve_rejects_when_apply_raises(root, tmp_path, monkeypatch):
    typo_kb(root)
    real_before = snapshot(root)
    crafted = Proposal("repair_link", "來源/pmid-1111", {"new": "來源/ghost", "pages": ["index"]}, "broken_links")
    monkeypatch.setattr(kb_rsi, "propose", lambda r: [crafted])
    d = kb_rsi.improve(root, tmp_path / "l.jsonl")[0]
    assert d["decision"] == "REJECT" and "apply failed" in d["reason"] and snapshot(root) == real_before


def test_improve_rejects_when_another_metric_gets_worse(root, tmp_path, monkeypatch):
    typo_kb(root)
    real_before = snapshot(root)

    def sneaky_apply(r, proposal):                      # fixes the broken link but adds an unsourced claim
        # Many sourced claims dilute the unsourced one, so the overall score RISES: only the held-out guard can catch it.
        sourced = "\n".join(f"- c{i} ([[來源/pmid-{'111' if i % 2 else '222'}]])" for i in range(12))
        put(r, "index.md", managed("## Home\n- [[概念/A]]"))
        put(r, "概念/A.md", managed("## Claims（主張）\n" + sourced + "\n- unsourced new claim"))
        return ["index.md", "概念/A.md"]

    crafted = Proposal("repair_link", "來源/pmid-1111", {"new": "來源/pmid-111", "pages": ["index"]}, "broken_links")
    monkeypatch.setattr(kb_rsi, "propose", lambda r: [crafted])
    monkeypatch.setattr(kb_rsi, "apply", sneaky_apply)
    d = kb_rsi.improve(root, tmp_path / "l.jsonl")[0]
    assert d["decision"] == "REJECT" and "unsourced_claims" in d["reason"] and d["after"] == 0
    assert d["delta_score"] > 0                          # the score alone would have promoted it
    assert snapshot(root) == real_before


def test_improve_rejects_when_score_does_not_rise(root, tmp_path, monkeypatch):
    perfect_kb(root)
    real_before = snapshot(root)
    crafted = Proposal("link_orphan", "概念/A", {}, "orphans")
    monkeypatch.setattr(kb_rsi, "propose", lambda r: [crafted])
    monkeypatch.setattr(kb_rsi, "apply", lambda r, p: [])
    d = kb_rsi.improve(root, tmp_path / "l.jsonl")[0]
    assert d["decision"] == "REJECT" and snapshot(root) == real_before


def test_improve_respects_max_proposals(root, tmp_path):
    perfect_kb(root)
    for i in range(4):
        put(root, f"概念/Lone{i}.md", managed("## Claims（主張）\n- c ([[來源/pmid-111]])\n- d ([[來源/pmid-222]])"))
    assert len(kb_rsi.improve(root, tmp_path / "l.jsonl", max_proposals=2)) == 2


def test_link_orphan_promoted_and_survives_next_run(root, tmp_path):
    kb.integrate_run(root, make_run())
    put(root, "概念/Lonely.md", "# Lonely\nuser written page without markers\n")
    f = kb_rsi.fitness(root)
    assert f["details"]["orphans"] == ["概念/Lonely"]
    decisions = kb_rsi.improve(root, tmp_path / "l.jsonl")
    promoted = [d for d in decisions if d["decision"] == "PROMOTE" and d["kind"] == "link_orphan"]
    assert promoted and kb_rsi.fitness(root)["orphans"] == 0
    index = (root / "index.md").read_text(encoding="utf-8")
    assert kb.UNLINKED_HEADING in index and "[[概念/Lonely]]" in index
    assert (root / "概念" / "Lonely.md").read_text(encoding="utf-8") == "# Lonely\nuser written page without markers\n"
    kb.integrate_run(root, make_run("r2"))                                       # regenerating the index keeps the entry
    assert "[[概念/Lonely]]" in (root / "index.md").read_text(encoding="utf-8")
    assert kb_rsi.fitness(root)["orphans"] == 0


def test_merge_concepts_promoted_keeps_user_text_and_rewrites_links(root, tmp_path):
    kb.integrate_run(root, make_run("r1", notes=[{"concept": "Recursive self improvement", "definition": "d1", "claims": [{"text": "Claim from run one", "keys": ["E1"]}], "related": []}]))
    kb.integrate_run(root, make_run("r2", notes=[{"concept": "Recursive self improvements", "definition": "d2", "claims": [{"text": "Claim from run two", "keys": ["E2"]}, {"text": "Second claim two", "keys": ["E3"]}], "related": []}]))
    keep_p, drop_p = root / "概念" / "Recursive self improvements.md", root / "概念" / "Recursive self improvement.md"
    assert keep_p.exists() and drop_p.exists()
    drop_p.write_bytes(drop_p.read_bytes().decode("utf-8").replace(kb.BEGIN, "MY OWN NOTE 我的筆記\r\n" + kb.BEGIN).encode("utf-8"))
    f = kb_rsi.fitness(root)
    assert f["duplicate_concepts"] == 1
    prop = [p for p in kb_rsi.propose(root) if p.kind == "merge_concepts"][0]
    assert prop.target == "概念/Recursive self improvement" and prop.detail["keep"] == "概念/Recursive self improvements"   # more claims is kept
    decisions = kb_rsi.improve(root, tmp_path / "l.jsonl")
    merged = [d for d in decisions if d["kind"] == "merge_concepts"]
    assert merged and merged[0]["decision"] == "PROMOTE" and merged[0]["delta_score"] > 0
    keep_text, drop_text = keep_p.read_text(encoding="utf-8"), drop_p.read_bytes().decode("utf-8")
    assert "Claim from run one" in keep_text and "Claim from run two" in keep_text and len(kb_rsi.claim_lines(keep_text)) == 3
    assert drop_text.startswith("---") and "MY OWN NOTE 我的筆記\r\n" in drop_text         # user text outside markers survives
    assert "See [[概念/Recursive self improvements]]" in drop_text and "Claim from run one" not in kb.get_block(drop_text).split("See")[1]
    topic = next((root / "主題").glob("*.md")).read_text(encoding="utf-8")
    assert "[[概念/Recursive self improvement]]" not in topic and "[[概念/Recursive self improvements]]" in topic
    after = kb_rsi.fitness(root)
    assert after["duplicate_concepts"] == 0 and after["broken_links"] == 0 and after["orphans"] == 0 and after["unsourced_claims"] == 0
    # a later run that uses the old name lands on the kept page, not on a new one
    before_files = {p.name for p in (root / "概念").glob("*.md")}
    kb.integrate_run(root, make_run("r3", notes=[{"concept": "Recursive self improvement", "definition": "", "claims": [{"text": "Claim from run three", "keys": ["E1"]}], "related": []}]))
    assert {p.name for p in (root / "概念").glob("*.md")} == before_files
    assert "Claim from run three" in keep_p.read_text(encoding="utf-8")


def test_merge_apply_refuses_pages_without_managed_state(root):
    perfect_kb(root)
    put(root, "概念/B.md", managed("## Claims（主張）\n- x ([[來源/pmid-111]])"))
    with pytest.raises(ValueError):
        kb_rsi.apply(root, Proposal("merge_concepts", "概念/B", {"keep": "概念/A"}, "duplicate_concepts"))
    with pytest.raises(ValueError):
        kb_rsi.apply(root, Proposal("unknown_kind", "x", {}, "orphans"))


# ------------------------------------------------------------------ ledger

def test_ledger_chain_verifies_and_tampering_is_detected(root, tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    assert kb_rsi.verify_ledger(ledger)                                         # no file: nothing to doubt
    for i in range(3):
        kb_rsi.append_ledger(ledger, {"kind": "repair_link", "target": f"t{i}", "decision": "PROMOTE", "reason": "r"})
    entries = kb_rsi.ledger_entries(ledger)
    assert [e["target"] for e in entries] == ["t2", "t1", "t0"]                  # newest first
    assert entries[2]["prev_hash"] == "0" * 64 and entries[1]["prev_hash"] == entries[2]["hash"]
    assert kb_rsi.verify_ledger(ledger) and len(kb_rsi.ledger_entries(ledger, limit=2)) == 2
    good = ledger.read_text(encoding="utf-8")
    ledger.write_text(good.replace('"t1"', '"tampered"'), encoding="utf-8")
    assert not kb_rsi.verify_ledger(ledger)
    lines = good.splitlines()
    ledger.write_text("\n".join([lines[0], lines[2]]) + "\n", encoding="utf-8")   # a removed line breaks the chain
    assert not kb_rsi.verify_ledger(ledger)
    ledger.write_text(good + "not json\n", encoding="utf-8")
    assert not kb_rsi.verify_ledger(ledger)
    ledger.write_text(good, encoding="utf-8")
    assert kb_rsi.verify_ledger(ledger)


def test_ledger_chain_survives_a_real_improve_run(root, tmp_path, monkeypatch):
    typo_kb(root)
    ledger = tmp_path / "ledger.jsonl"
    kb_rsi.improve(root, ledger)
    monkeypatch.setattr(kb_rsi, "propose", lambda r: [Proposal("link_orphan", "概念/A", {}, "orphans")])
    kb_rsi.improve(root, ledger)
    assert len(kb_rsi.ledger_entries(ledger)) == 2 and kb_rsi.verify_ledger(ledger)
    ledger.write_text(ledger.read_text(encoding="utf-8").replace("PROMOTE", "REJECT", 1), encoding="utf-8")
    assert not kb_rsi.verify_ledger(ledger)
