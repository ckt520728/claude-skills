"""Offline tests: a fake provider stands in for the LLM so the whole pipeline runs without network."""
from kgengine import pipeline
from kgengine.graph import KnowledgeGraph
from kgengine.ingest import chunk
from kgengine.ontology import normalize_predicate
from kgengine.providers import Provider, inline_schema
from kgengine.schema import Answer, EntityProfile, ExtractedGraph, ResolvedClusters
from kgengine.store import Store

DOC_A = ("Aerobic exercise training for 12 months increased hippocampal volume in older adults. "
         "Individual alpha peak frequency (IAPF) was higher after training and predicted episodic memory. ") * 5
DOC_B = ("Physical activity was associated with faster IAPF in healthy older adults measured with MEG. "
         "Resistance training showed no effect on hippocampal volumes. ") * 5

EXTRACTIONS = {
    "A": {"entities": [
        {"name": "Aerobic exercise", "type": "INTERVENTION", "description": "12-month aerobic training"},
        {"name": "hippocampal volume", "type": "BIOMARKER", "description": "MRI hippocampal size"},
        {"name": "Individual Alpha Peak Frequency (IAPF)", "type": "BIOMARKER", "description": "EEG alpha peak"},
        {"name": "episodic memory", "type": "COGNITIVE_DOMAIN", "description": "memory for events"},
        {"name": "older adults", "type": "POPULATION", "description": "study sample"}],
        "relations": [
        {"source": "Aerobic exercise", "predicate": "INCREASES", "target": "hippocampal volume", "evidence": "increased hippocampal volume", "confidence": 1},
        {"source": "Aerobic exercise", "predicate": "INCREASES", "target": "Individual Alpha Peak Frequency (IAPF)", "evidence": "IAPF higher after training", "confidence": 1},
        {"source": "Individual Alpha Peak Frequency (IAPF)", "predicate": "PREDICTS", "target": "episodic memory", "evidence": "predicted episodic memory", "confidence": 1},
        {"source": "Aerobic exercise", "predicate": "STUDIED_IN", "target": "ghost entity", "evidence": "x", "confidence": 1}]},
    "B": {"entities": [
        {"name": "Physical activity", "type": "INTERVENTION", "description": "habitual PA"},
        {"name": "IAPF", "type": "BIOMARKER", "description": "alpha peak frequency from MEG"},
        {"name": "Resistance training", "type": "INTERVENTION", "description": "strength training"},
        {"name": "Hippocampal volumes", "type": "BIOMARKER", "description": "hippocampus size"},
        {"name": "Aerobic exercise", "type": "INTERVENTION", "description": "aerobic"}],
        "relations": [
        {"source": "Physical activity", "predicate": "ASSOCIATED_WITH", "target": "IAPF", "evidence": "associated with faster IAPF", "confidence": 1},
        {"source": "Resistance training", "predicate": "NO_EFFECT_ON", "target": "Hippocampal volumes", "evidence": "no effect", "confidence": 1},
        {"source": "Aerobic exercise", "predicate": "NO_EFFECT_ON", "target": "Hippocampal volumes", "evidence": "conflicting", "confidence": 1}]},
}


class FakeProvider(Provider):
    name = "fake"

    def structured(self, prompt, schema, role="fast", system=""):
        self.calls += 1
        if schema is ExtractedGraph:
            return ExtractedGraph.model_validate(EXTRACTIONS["A" if "increased hippocampal" in prompt else "B"])
        if schema is ResolvedClusters:
            return ResolvedClusters(clusters=[])  # deterministic stage must already merge IAPF
        if schema is EntityProfile:
            return EntityProfile(summary="s", key_facts=["f [doc]"])
        if schema is Answer:
            return Answer(answer="yes", cited_edges=[], confidence="high", gaps=[])
        raise AssertionError(schema)


def build(tmp_path):
    store = Store(tmp_path / "kg.sqlite")
    pipeline.ingest_text(store, "docA", DOC_A)
    pipeline.ingest_text(store, "docB", DOC_B)
    p = FakeProvider()
    rep = pipeline.extract(store, p, workers=2, progress=lambda *_: None)
    assert rep["extracted"] == 2 and not rep["failed"]
    pipeline.resolve(store, p, progress=lambda *_: None)
    return store, KnowledgeGraph(store), p


def test_pipeline_resolution_and_queries(tmp_path):
    store, kg, p = build(tmp_path)
    G = kg.G
    # acronym + plural merges
    assert "Individual Alpha Peak Frequency (IAPF)" in G and "IAPF" not in G
    assert "Hippocampal volumes" not in G or "hippocampal volume" not in G
    assert "ghost entity" not in G  # relation to unextracted entity dropped
    hv = kg.resolve_name("hippocampal volumes")
    assert hv is not None
    # aggregated multi-document edge carries evidence from both docs? (here one doc each)
    assert G.edges["Aerobic exercise", hv, "INCREASES"]["weight"] == 1
    # pattern match: intervention -> biomarker -> cognition
    m = kg.match("(INTERVENTION)-[INCREASES|IMPROVES]->(BIOMARKER)-[PREDICTS]->(COGNITIVE_DOMAIN)")
    assert m["count"] == 1 and m["results"][0]["bindings"][-1] == "episodic memory"
    m2 = kg.match("(BIOMARKER{name~alpha})<-[*]-(INTERVENTION)")
    assert {r["bindings"][1] for r in m2["results"]} == {"Aerobic exercise", "Physical activity / exercise (PA)"}
    # paths across documents (multi-hop through the merged IAPF node)
    paths = kg.paths("Physical activity", "episodic memory")
    assert paths["paths"] and len(paths["paths"][0]["nodes"]) == 3
    # contradictions: aerobic INCREASES vs NO_EFFECT_ON hippocampal volume
    assert any(c["source"] == "Aerobic exercise" for c in kg.contradictions())
    assert kg.evidence_matrix()[0]["source"] in {"Aerobic exercise", "Physical activity / exercise (PA)", "Resistance training"}
    # re-extraction is cached: no new LLM calls
    calls = p.calls
    store.x("UPDATE chunks SET extracted=0")
    pipeline.extract(store, p, progress=lambda *_: None)
    assert p.calls == calls


def test_summarize_ask_viz_export(tmp_path):
    from kgengine import qa
    from kgengine.export import export
    from kgengine.viz import export_html
    store, kg, p = build(tmp_path)
    assert pipeline.summarize(store, p, kg, top=2, progress=lambda *_: None) == 2
    kg.reload()
    r = qa.ask(kg, p, "Does aerobic exercise change IAPF?")
    assert "Aerobic exercise" in r["seeds"] and r["answer"] == "yes"
    html = export_html(kg, tmp_path / "g.html").read_text(encoding="utf-8")
    assert "vis-network" in html and "Aerobic exercise" in html
    for fmt in ("graphml", "json", "cypher"):
        assert export(kg, fmt, tmp_path / f"g.{fmt}").stat().st_size > 0


def test_helpers():
    assert normalize_predicate("enhances") == "IMPROVES"
    assert normalize_predicate("weird") == "RELATED_TO"
    assert "$defs" not in str(inline_schema(ExtractedGraph))
    cs = chunk("para\n\n" * 3000, size=1000, overlap=100)
    assert all(len(c) <= 1100 for c in cs)


def test_api(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from kgengine import api
    store, kg, _ = build(tmp_path)
    api._state.update(store=store, kg=kg)
    c = TestClient(api.app)
    assert c.get("/stats").json()["nodes"] > 0
    assert c.get("/search", params={"q": "alpha"}).json()[0]["type"] == "BIOMARKER"
    assert c.get("/match", params={"pattern": "(INTERVENTION)-[*]->(*)"}).json()["count"] > 0
    assert c.get("/match", params={"pattern": "bad"}).status_code == 400
    assert c.get("/viz").status_code == 200


def test_duplicate_documents_count_once(tmp_path):
    from kgengine.dedup import mark_duplicates
    store = Store(tmp_path / "kg.sqlite")
    pipeline.ingest_text(store, "docA", DOC_A, source="a.pdf")
    pipeline.ingest_text(store, "docA copy", DOC_A + " Downloaded copy.", source="a_copy.pdf")
    pipeline.ingest_text(store, "docB", DOC_B, source="b.pdf")
    p = FakeProvider()
    pipeline.extract(store, p, progress=lambda *_: None)   # both copies extracted (worst case)
    rep = mark_duplicates(store)
    assert rep["duplicates"] == 1
    pipeline.resolve(store, p, progress=lambda *_: None)
    kg = KnowledgeGraph(store)
    hv = kg.resolve_name("hippocampal volume")
    assert kg.G.edges["Aerobic exercise", hv, "INCREASES"]["weight"] == 1   # not 2
    assert len(kg.G.edges["Aerobic exercise", hv, "INCREASES"]["evidence"]) == 2


def test_shared_acronym_does_not_merge_different_entities(tmp_path):
    from kgengine.schema import Entity
    store = Store(tmp_path / "kg.sqlite")
    pipeline.ingest_text(store, "d", DOC_A)
    cid = store.q("SELECT id FROM chunks")[0]["id"]
    g = ExtractedGraph(entities=[
        Entity(name="Exhaustive exercise (EE)", type="INTERVENTION", description="bout to exhaustion"),
        Entity(name="Enriched environment (EE)", type="INTERVENTION", description="rodent housing"),
        Entity(name="Individual alpha peak frequency (IAPF)", type="BIOMARKER", description="x"),
        Entity(name="IAPF", type="BIOMARKER", description="y")], relations=[])
    store.save_extraction(cid, 1, g)
    pipeline.resolve(store, None, use_llm=False, progress=lambda *_: None)
    kg = KnowledgeGraph(store)
    assert "Exhaustive exercise (EE)" in kg.G and "Enriched environment (EE)" in kg.G
    assert "IAPF" not in kg.G   # unambiguous bare acronym still merges


def _save(store, rels, ents):
    from kgengine.schema import Entity, Relation
    cid = store.q("SELECT id FROM chunks")[0]["id"]
    store.save_extraction(cid, 1, ExtractedGraph(
        entities=[Entity(name=n, type=t, description="d") for n, t in ents],
        relations=[Relation(source=a, predicate=p, target=b, evidence="e", confidence=1, timescale=ts)
                   for a, p, b, ts in rels]))


def test_acute_and_chronic_effects_are_separate_edges(tmp_path):
    store = Store(tmp_path / "kg.sqlite")
    pipeline.ingest_text(store, "d", DOC_A)
    ents = [("Aerobic exercise", "INTERVENTION"), ("P300 amplitude", "BIOMARKER"), ("BDNF", "BIOMARKER")]
    _save(store, [("Aerobic exercise", "INCREASES", "P300 amplitude", "acute"),
                  ("Aerobic exercise", "NO_EFFECT_ON", "P300 amplitude", "chronic"),
                  ("Aerobic exercise", "INCREASES", "BDNF", "chronic"),
                  ("Aerobic exercise", "NO_EFFECT_ON", "BDNF", "unspecified")], ents)
    pipeline.resolve(store, None, use_llm=False, progress=lambda *_: None)
    kg = KnowledgeGraph(store)
    es = kg.G["Aerobic exercise"]["P300 amplitude"]
    assert set(es) == {"INCREASES@acute", "NO_EFFECT_ON@chronic"}
    assert es["INCREASES@acute"]["predicate"] == "INCREASES" and es["INCREASES@acute"]["timescale"] == "acute"
    # acute effect vs chronic null is NOT a contradiction; chronic vs unspecified is
    c = kg.contradictions()
    assert {x["target"] for x in c} == {"BDNF"}
    # predicate filters still work, and timescale-qualified patterns narrow them
    assert kg.match("(INTERVENTION)-[INCREASES]->(BIOMARKER)")["count"] == 2
    assert kg.match("(INTERVENTION)-[INCREASES@acute]->(BIOMARKER)")["count"] == 1
    from kgengine.graph import edge_lines
    assert "-[INCREASES|acute]->" in edge_lines(kg.G, "Aerobic exercise")


def test_curated_merge_physical_activity_exercise_one_node(tmp_path):
    store = Store(tmp_path / "kg.sqlite")
    pipeline.ingest_text(store, "d", DOC_A)
    ents = [("Physical activity (PA)", "INTERVENTION"), ("Physical Exercise (PE)", "INTERVENTION"),
            ("Exercise", "INTERVENTION"), ("Physical activity and exercise", "INTERVENTION"),
            ("Aerobic exercise", "INTERVENTION"), ("Exercise training", "INTERVENTION"),
            ("hippocampal volume", "BIOMARKER")]
    _save(store, [("Exercise", "INCREASES", "hippocampal volume", "chronic")], ents)
    rep = pipeline.resolve(store, None, use_llm=False, progress=lambda *_: None)
    kg = KnowledgeGraph(store)
    pa = "Physical activity / exercise (PA)"
    assert pa in kg.G and rep["curated_merges"] >= 3
    for n in ("Physical activity (PA)", "Physical Exercise (PE)", "Exercise", "Physical activity and exercise"):
        assert n not in kg.G and kg.resolve_name(n) == pa
    assert "Aerobic exercise" in kg.G and "Exercise training" in kg.G   # sub-types stay separate
    assert kg.G.has_edge(pa, "hippocampal volume")
    assert {r["method"] for r in store.q("SELECT method FROM aliases WHERE canonical=?", (pa,))} >= {"curated"}


def test_rag_context_ranking_is_seed_aware():
    """Pitfall 24: heavy hub edges far from the seeds must not crowd out the seed's own biomarker edges."""
    import networkx as nx
    from kgengine.qa import rank_edges
    G = nx.MultiDiGraph()
    for n, t in [("Aerobic exercise", "INTERVENTION"), ("P300 amplitude", "BIOMARKER"),
                 ("PA", "INTERVENTION"), ("Cognition", "COGNITIVE_DOMAIN"), ("Mood", "CONCEPT")]:
        G.add_node(n, type=t)
    G.add_edge("Aerobic exercise", "P300 amplitude", key="INCREASES", weight=1)
    G.add_edge("Aerobic exercise", "PA", key="IS_A", weight=2)
    for i in range(40):                       # a hub with many heavy edges
        G.add_node(f"x{i}", type="CONCEPT")
        G.add_edge("PA", f"x{i}", key="IMPROVES", weight=20)
    G.add_edge("PA", "Cognition", key="IMPROVES", weight=19)
    dist = {"Aerobic exercise": 0, "P300 amplitude": 1, "PA": 1, "Cognition": 2, "Mood": 2,
            **{f"x{i}": 2 for i in range(40)}}
    ranked = rank_edges(G, ["Aerobic exercise"], dist, "Does aerobic exercise change ERP P300 and cognition in older adults?",
                        per_node_cap=10)
    assert (ranked[0][0], ranked[0][1]) == ("Aerobic exercise", "P300 amplitude")
    assert sum(1 for e in ranked if e[0] == "PA") <= 9          # hub capped
    assert any(e[1] == "Cognition" for e in ranked)             # typed edge beats untyped hub edges
