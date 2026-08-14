"""Unit tests for the LangGraph node wrappers.

All tests are offline: components are injected or monkeypatched (no LLM/API
calls). Every node is tested independently for correct arguments, partial
state updates, and input-state immutability.
"""
import copy

import pytest

import backend.app.graph.nodes as nodes


class FakeChain:
    """Minimal LCEL-chain stand-in with an ``invoke`` method."""

    def __init__(self, result=None, responder=None, error=None):
        self.result = result
        self.responder = responder
        self.error = error
        self.calls = []

    def invoke(self, inputs):
        self.calls.append(inputs)
        if self.error is not None:
            raise self.error
        if self.responder is not None:
            return self.responder(inputs)
        return self.result


def base_state(**overrides):
    state = {"query": "climate change agriculture", "errors": []}
    state.update(overrides)
    return state


def snapshot(state):
    return copy.deepcopy(state)


# ── plan_node ────────────────────────────────────────────────────────────────

def test_plan_node_calls_planner_with_query(monkeypatch):
    plan = {"research_angles": ["crop yields"], "use_rag": True}
    calls = []

    def fake_planner(query):
        calls.append(query)
        return plan

    monkeypatch.setattr(nodes, "plan_research", fake_planner)
    state = base_state()

    out = nodes.plan_node(state)

    assert calls == ["climate change agriculture"]
    assert out == {"research_plan": plan}
    assert state == snapshot(state)  # not mutated


# ── research_node ────────────────────────────────────────────────────────────

def test_research_node_web_only_does_not_call_rag():
    search_calls = []
    rag_called = []

    def search_fn(query, angles):
        search_calls.append((query, angles))
        return ("search text", ["https://a.com"])

    def rag_fn(query):
        rag_called.append(query)
        return ([], [])

    state = base_state(research_plan={"research_angles": ["x"], "use_rag": False})

    out = nodes.research_node(state, search_fn=search_fn, rag_fn=rag_fn)

    assert search_calls == [("climate change agriculture", ["x"])]
    assert rag_called == []
    assert out == {"search_results": "search text", "sources": ["https://a.com"]}
    assert state == snapshot(state)


def test_research_node_use_rag_true_calls_rag():
    chunks = [{"text": "t", "score": 0.5, "metadata": {"document_id": "d1", "source_name": "a.txt", "source_type": "txt"}}]
    refs = [{"document_id": "d1", "source_name": "a.txt", "source_type": "txt"}]
    rag_calls = []

    def rag_fn(query):
        rag_calls.append(query)
        return chunks, refs

    state = base_state(research_plan={"research_angles": [], "use_rag": True})

    out = nodes.research_node(state, search_fn=lambda q, a: ("t", []), rag_fn=rag_fn)

    assert rag_calls == ["climate change agriculture"]
    assert out["retrieved_chunks"] == chunks
    assert out["documents_used"] == refs
    assert set(out.keys()) == {"search_results", "sources", "retrieved_chunks", "documents_used"}
    assert state == snapshot(state)


def test_research_node_missing_plan_defaults_to_web_only():
    out = nodes.research_node(base_state(), search_fn=lambda q, a: ("t", ["https://a.com"]))
    assert "retrieved_chunks" not in out
    assert "documents_used" not in out


# ── evidence_node ────────────────────────────────────────────────────────────

def test_evidence_node_merges_web_and_rag(monkeypatch):
    captured = {}

    def fake_merge(web, rag):
        captured["web"] = web
        captured["rag"] = rag
        return web + rag

    monkeypatch.setattr(nodes, "merge_evidence", fake_merge)
    state = base_state(
        sources=["https://a.com", "https://b.com"],
        search_results="web summary",
        retrieved_chunks=[
            {
                "text": "rag text",
                "score": 0.9,
                "metadata": {
                    "document_id": "doc-1",
                    "source_name": "report.pdf",
                    "source_type": "pdf",
                    "chunk_id": "chunk-1",
                    "chunk_index": 2,
                    "total_chunks": 5,
                    "page_number": 3,
                },
            }
        ],
    )

    out = nodes.evidence_node(state)

    assert len(captured["web"]) == 2
    assert captured["web"][0]["source_type"] == "web"
    assert captured["web"][0]["url"] == "https://a.com"
    assert captured["web"][0]["text"] == "web summary"
    assert len(captured["rag"]) == 1
    rag = captured["rag"][0]
    assert rag["source_type"] == "rag"
    assert rag["document_id"] == "doc-1"
    assert rag["page"] == 3
    assert rag["chunk_index"] == 2
    assert "evidence" in out
    assert state == snapshot(state)


def test_evidence_node_empty_research_returns_empty_evidence():
    out = nodes.evidence_node(base_state())
    assert out == {"evidence": []}


# ── fact_check_node ──────────────────────────────────────────────────────────

def test_fact_check_node_passes_claims_and_evidence(monkeypatch):
    evidence = [{"id": "E1", "source_type": "web", "text": "t", "title": "T", "score": 0.8}]
    captured = {}

    def fake_check(claims, evidence_):
        captured["claims"] = claims
        captured["evidence"] = evidence_
        return [{"claim": "c", "verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1"]}]

    monkeypatch.setattr(nodes, "fact_check_claims", fake_check)
    state = base_state(evidence=evidence)

    out = nodes.fact_check_node(state, claims=["the claim"])

    assert captured["claims"] == ["the claim"]
    assert captured["evidence"] == evidence
    assert out["fact_checks"][0]["verdict"] == "supported"
    assert state == snapshot(state)


def test_fact_check_node_without_claims_returns_empty():
    state = base_state(evidence=[{"id": "E1"}])
    out = nodes.fact_check_node(state)
    assert out == {"fact_checks": []}


# ── citation_node ────────────────────────────────────────────────────────────

def test_citation_node_passes_evidence_and_fact_checks(monkeypatch):
    evidence = [{"id": "E1", "source_type": "web", "text": "t", "title": "T", "url": "https://a.com", "score": 0.8}]
    fact_checks = [{"claim": "c", "verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1"]}]
    citations = [{"index": 1, "source_type": "web", "title": "T", "url": "https://a.com", "document_id": None, "page": None, "chunk_index": None}]
    captured = {}

    def fake_gen(ev, fc):
        captured["evidence"] = ev
        captured["fact_checks"] = fc
        return citations

    monkeypatch.setattr(nodes, "generate_citations", fake_gen)
    state = base_state(evidence=evidence, fact_checks=fact_checks)

    out = nodes.citation_node(state)

    assert captured["evidence"] == evidence
    assert captured["fact_checks"] == fact_checks
    assert out == {"citations": citations}
    assert state == snapshot(state)


# ── confidence_node ──────────────────────────────────────────────────────────

def test_confidence_node_calls_calculate_confidence(monkeypatch):
    captured = {}

    def fake_calc(ev, fc, cit):
        captured["evidence"] = ev
        captured["fact_checks"] = fc
        captured["citations"] = cit
        return "high"

    monkeypatch.setattr(nodes, "calculate_confidence", fake_calc)
    state = base_state(
        evidence=[{"id": "E1", "score": 0.9}],
        fact_checks=[{"claim": "c", "verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1"]}],
        citations=[{"index": 1, "source_type": "web", "title": "T"}],
    )

    out = nodes.confidence_node(state)

    assert captured["evidence"] == state["evidence"]
    assert captured["fact_checks"] == state["fact_checks"]
    assert captured["citations"] == state["citations"]
    assert out == {"confidence": "high"}
    assert state == snapshot(state)


def test_confidence_node_does_not_execute_routing(monkeypatch):
    # route_research belongs to the graph; the node must not call it.
    def boom(*args, **kwargs):
        raise AssertionError("route_research must not be called by confidence_node")

    monkeypatch.setattr("backend.app.agents.confidence.route_research", boom)
    monkeypatch.setattr(nodes, "calculate_confidence", lambda ev, fc, cit: "low")

    out = nodes.confidence_node(base_state(evidence=[{"id": "E1", "score": 0.1}]))
    assert out == {"confidence": "low"}  # no routing decision leaked


# ── writer_node ──────────────────────────────────────────────────────────────

def test_writer_node_passes_topic_and_evidence(monkeypatch):
    chain = FakeChain(result="drafted report")
    monkeypatch.setattr(nodes, "writer_chain", chain)
    evidence = [{"id": "E1", "source_type": "web", "title": "Alpha", "text": "evidence body", "score": 0.8}]
    state = base_state(evidence=evidence)

    out = nodes.writer_node(state)

    assert out == {"report_draft": "drafted report"}
    inputs = chain.calls[0]
    assert inputs["topic"] == "climate change agriculture"
    assert "evidence body" in inputs["research"]
    assert "Alpha" in inputs["research"]
    assert state == snapshot(state)


def test_writer_node_empty_evidence_still_invokes_writer(monkeypatch):
    chain = FakeChain(result="report")
    monkeypatch.setattr(nodes, "writer_chain", chain)
    out = nodes.writer_node(base_state())
    assert out == {"report_draft": "report"}
    assert chain.calls[0]["research"] == ""


# ── critic_node ──────────────────────────────────────────────────────────────

def test_critic_node_returns_feedback_and_score(monkeypatch):
    chain = FakeChain(result="Score: 7/10\n\nStrengths:\n- good")
    monkeypatch.setattr(nodes, "critic_chain", chain)
    state = base_state(report_draft="the report")

    out = nodes.critic_node(state)

    assert out["critic_feedback"] == "Score: 7/10\n\nStrengths:\n- good"
    assert out["critic_score"] == 7
    assert chain.calls[0] == {"report": "the report"}
    assert state == snapshot(state)


def test_critic_node_without_score_in_feedback(monkeypatch):
    chain = FakeChain(result="no score line here")
    monkeypatch.setattr(nodes, "critic_chain", chain)
    out = nodes.critic_node(base_state(report_draft="r"))
    assert out["critic_score"] is None
    assert out["critic_feedback"] == "no score line here"


# ── Determinism & shared guarantees ──────────────────────────────────────────

def test_nodes_are_deterministic(monkeypatch):
    plan = {"research_angles": ["a"], "use_rag": False}
    monkeypatch.setattr(nodes, "plan_research", lambda q: plan)
    state = base_state()
    assert nodes.plan_node(state) == nodes.plan_node(snapshot(state))

    chain = FakeChain(result="r")
    monkeypatch.setattr(nodes, "writer_chain", chain)
    assert nodes.writer_node(state) == nodes.writer_node(snapshot(state))


def test_nodes_never_add_unexpected_state_fields(monkeypatch):
    monkeypatch.setattr(nodes, "plan_research", lambda q: {"research_angles": [], "use_rag": False})
    assert set(nodes.plan_node(base_state()).keys()) == {"research_plan"}
    assert set(nodes.confidence_node(base_state(evidence=[])).keys()) == {"confidence"}
    assert set(nodes.fact_check_node(base_state()).keys()) == {"fact_checks"}
    assert set(nodes.evidence_node(base_state()).keys()) == {"evidence"}
    assert set(nodes.citation_node(base_state()).keys()) == {"citations"}
