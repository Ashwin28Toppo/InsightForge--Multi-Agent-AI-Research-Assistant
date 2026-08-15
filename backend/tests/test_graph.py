"""Unit tests for the research StateGraph (Phase 2C Steps 2-4).

Offline: graph execution uses fake node functions patched into
``backend.app.graph.nodes``; the real graph is only built (never executed with
real dependencies). No LLM/Tavily/Qdrant/API calls.
"""
import copy

import pytest

import backend.app.graph.graph as graph_mod
import backend.app.graph.nodes as nodes

NODE_NAMES = [
    "plan", "research", "evidence", "claim_extraction", "fact_check",
    "citation", "confidence", "writer", "critic",
]

# Conditional edges appear in get_graph().edges as one edge per distinct target.
EXPECTED_EDGES = [
    ("__start__", "plan"),
    ("plan", "research"),
    ("research", "evidence"),
    ("evidence", "claim_extraction"),
    ("claim_extraction", "fact_check"),
    ("fact_check", "citation"),
    ("citation", "confidence"),
    ("confidence", "writer"),
    ("writer", "critic"),
    ("critic", "__end__"),               # conditional: complete / insufficient
    ("critic", "increment_rounds"),      # conditional: additional_research
    ("increment_rounds", "research"),    # loop back
]


def edge_pairs(compiled):
    return [(e.source, e.target) for e in compiled.get_graph().edges]


def make_fake(name, update):
    def fake(state):
        return update

    fake.__name__ = name
    return fake


def make_running_graph(monkeypatch, confidence="medium"):
    """Patch business nodes as recorders; confidence node returns the label."""
    counts = {name: 0 for name in NODE_NAMES}

    def recorder(name, result):
        def fake(state):
            counts[name] += 1
            return result

        return fake

    for name in NODE_NAMES:
        if name == "confidence":
            monkeypatch.setattr(
                nodes, "confidence_node", recorder("confidence", {"confidence": confidence})
            )
        else:
            monkeypatch.setattr(nodes, f"{name}_node", recorder(name, {}))
    return counts


# ── Build & topology ─────────────────────────────────────────────────────────

def test_graph_builds_successfully():
    compiled = graph_mod.build_research_graph()
    assert hasattr(compiled, "invoke")
    assert compiled.get_graph() is not None


def test_all_expected_nodes_exist():
    node_names = set(graph_mod.build_research_graph().get_graph().nodes.keys())
    for name in NODE_NAMES:
        assert name in node_names
    assert "increment_rounds" in node_names


@pytest.mark.parametrize("source,target", EXPECTED_EDGES)
def test_expected_edge_exists(source, target):
    assert (source, target) in edge_pairs(graph_mod.build_research_graph())


def test_start_connects_to_plan():
    assert ("__start__", "plan") in edge_pairs(graph_mod.build_research_graph())


def test_linear_chain_edges_preserved():
    edges = edge_pairs(graph_mod.build_research_graph())
    chain = [
        ("__start__", "plan"), ("plan", "research"), ("research", "evidence"),
        ("evidence", "claim_extraction"), ("claim_extraction", "fact_check"),
        ("fact_check", "citation"), ("citation", "confidence"),
        ("confidence", "writer"), ("writer", "critic"),
    ]
    for source, target in chain:
        assert (source, target) in edges


def test_evidence_connects_to_claim_extraction():
    assert ("evidence", "claim_extraction") in edge_pairs(graph_mod.build_research_graph())


def test_claim_extraction_connects_to_fact_check():
    assert ("claim_extraction", "fact_check") in edge_pairs(graph_mod.build_research_graph())


def test_no_direct_evidence_to_fact_check_edge():
    assert ("evidence", "fact_check") not in edge_pairs(graph_mod.build_research_graph())


def test_critic_has_conditional_routing():
    edges = edge_pairs(graph_mod.build_research_graph())
    critic_targets = {t for s, t in edges if s == "critic"}
    assert critic_targets == {"__end__", "increment_rounds"}


def test_complete_and_insufficient_route_to_end():
    assert ("critic", "__end__") in edge_pairs(graph_mod.build_research_graph())


def test_additional_research_routes_back_to_research():
    edges = edge_pairs(graph_mod.build_research_graph())
    assert ("critic", "increment_rounds") in edges
    assert ("increment_rounds", "research") in edges


def test_topology_matches_bounded_loop():
    assert sorted(edge_pairs(graph_mod.build_research_graph())) == sorted(EXPECTED_EDGES)


def test_compilation_is_deterministic():
    a = graph_mod.build_research_graph()
    b = graph_mod.build_research_graph()
    assert sorted(edge_pairs(a)) == sorted(edge_pairs(b))
    assert set(a.get_graph().nodes.keys()) == set(b.get_graph().nodes.keys())


def test_module_level_graph_exists():
    assert hasattr(graph_mod, "research_graph")
    assert hasattr(graph_mod.research_graph, "invoke")


# ── Routing behavior (fake nodes) ────────────────────────────────────────────

def test_route_research_is_invoked_by_router(monkeypatch):
    calls = []

    def fake_route(confidence, research_rounds):
        calls.append((confidence, research_rounds))
        return "complete"

    monkeypatch.setattr(graph_mod, "route_research", fake_route)
    make_running_graph(monkeypatch, confidence="high")
    graph_mod.build_research_graph().invoke({"query": "q"})
    assert calls == [("high", 0)]


def test_route_after_critic_delegates(monkeypatch):
    calls = []

    def fake_route(confidence, research_rounds):
        calls.append((confidence, research_rounds))
        return "additional_research"

    monkeypatch.setattr(graph_mod, "route_research", fake_route)
    assert graph_mod._route_after_critic(
        {"confidence": "medium", "research_rounds": 1}
    ) == "additional_research"
    assert calls == [("medium", 1)]


def test_high_confidence_finishes_immediately(monkeypatch):
    counts = make_running_graph(monkeypatch, confidence="high")
    result = graph_mod.build_research_graph().invoke({"query": "q"})
    assert counts["research"] == 1
    assert counts["critic"] == 1
    assert result["confidence"] == "high"
    assert "research_rounds" not in result  # no loop, no increment


def test_high_confidence_any_round_complete(monkeypatch):
    counts = make_running_graph(monkeypatch, confidence="high")
    result = graph_mod.build_research_graph().invoke({"query": "q", "research_rounds": 5})
    assert counts["research"] == 1
    assert result["research_rounds"] == 5


def test_medium_rounds_0_performs_another_round(monkeypatch):
    counts = make_running_graph(monkeypatch, confidence="medium")
    result = graph_mod.build_research_graph().invoke({"query": "q"})
    assert counts["research"] == 3
    assert result["research_rounds"] == 2


def test_low_rounds_0_performs_another_round(monkeypatch):
    counts = make_running_graph(monkeypatch, confidence="low")
    result = graph_mod.build_research_graph().invoke({"query": "q"})
    assert counts["research"] == 3
    assert result["research_rounds"] == 2


def test_medium_rounds_2_finishes_insufficient(monkeypatch):
    counts = make_running_graph(monkeypatch, confidence="medium")
    result = graph_mod.build_research_graph().invoke({"query": "q", "research_rounds": 2})
    assert counts["research"] == 1
    assert result["research_rounds"] == 2


def test_low_rounds_2_finishes_insufficient(monkeypatch):
    counts = make_running_graph(monkeypatch, confidence="low")
    result = graph_mod.build_research_graph().invoke({"query": "q", "research_rounds": 2})
    assert counts["research"] == 1
    assert result["research_rounds"] == 2


def test_research_rounds_increase_correctly(monkeypatch):
    make_running_graph(monkeypatch, confidence="medium")
    result = graph_mod.build_research_graph().invoke({"query": "q"})
    # Two loop-backs -> rounds incremented 1 then 2.
    assert result["research_rounds"] == 2


def test_loop_cannot_run_forever(monkeypatch):
    counts = make_running_graph(monkeypatch, confidence="low")
    # Completes without RecursionError and is bounded.
    result = graph_mod.build_research_graph().invoke({"query": "q"})
    assert result["research_rounds"] == 2
    assert counts["research"] == 3


def test_increment_rounds_node():
    state = {"research_rounds": 2}
    assert graph_mod._increment_rounds_node(state) == {"research_rounds": 3}
    assert state == {"research_rounds": 2}  # input not mutated
    assert graph_mod._increment_rounds_node({}) == {"research_rounds": 1}


# ── State flow & safety ──────────────────────────────────────────────────────

def test_execution_order_single_pass(monkeypatch):
    executed = []

    def recorder(name):
        def fake(state):
            executed.append(name)
            return {"confidence": "high"} if name == "confidence" else {}

        return fake

    for name in NODE_NAMES:
        monkeypatch.setattr(nodes, f"{name}_node", recorder(name))

    graph_mod.build_research_graph().invoke({"query": "q"})
    assert executed == NODE_NAMES


def test_invocation_passes_state_and_preserves_input(monkeypatch):
    for name in NODE_NAMES:
        update = {"confidence": "high"} if name == "confidence" else {}
        monkeypatch.setattr(nodes, f"{name}_node", make_fake(name, update))

    initial = {"query": "What are the latest developments in AI agents?"}
    before = copy.deepcopy(initial)
    result = graph_mod.build_research_graph().invoke(initial)

    assert result["query"] == initial["query"]
    assert initial == before  # input not unexpectedly mutated


def test_node_outputs_appear_in_final_state(monkeypatch):
    updates = {
        "plan": {"research_plan": {"research_angles": ["a"], "use_rag": False}},
        "research": {"search_results": "text", "sources": ["https://a.com"]},
        "evidence": {"evidence": [{"id": "E1", "source_type": "web", "text": "t", "title": "T", "score": 0.8}]},
        "claim_extraction": {"claims": ["claim one", "claim two"]},
        "fact_check": {"fact_checks": [{"claim": "claim one", "verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1"]}]},
        "citation": {"citations": [{"index": 1, "source_type": "web", "title": "T", "url": "https://a.com",
                                    "document_id": None, "page": None, "chunk_index": None}]},
        "confidence": {"confidence": "high"},
        "writer": {"report_draft": "draft"},
        "critic": {"critic_feedback": "Score: 8/10", "critic_score": 8},
    }
    for name in NODE_NAMES:
        monkeypatch.setattr(nodes, f"{name}_node", make_fake(name, updates[name]))

    result = graph_mod.build_research_graph().invoke({"query": "q"})

    assert result["research_plan"]["use_rag"] is False
    assert result["search_results"] == "text"
    assert result["sources"] == ["https://a.com"]
    assert result["evidence"][0]["id"] == "E1"
    assert result["claims"] == ["claim one", "claim two"]
    assert result["fact_checks"][0]["verdict"] == "supported"
    assert result["citations"][0]["index"] == 1
    assert result["confidence"] == "high"
    assert result["report_draft"] == "draft"
    assert result["critic_feedback"] == "Score: 8/10"
    assert result["critic_score"] == 8


def test_minimal_query_executes_with_fake_nodes(monkeypatch):
    for name in NODE_NAMES:
        update = {"confidence": "high"} if name == "confidence" else {}
        monkeypatch.setattr(nodes, f"{name}_node", make_fake(name, update))
    result = graph_mod.build_research_graph().invoke({"query": "q"})
    assert result["query"] == "q"
    assert result["confidence"] == "high"


def test_fact_checks_are_generated_from_extracted_claims(monkeypatch):
    # The real claim_extraction_node runs with a monkeypatched extractor.
    monkeypatch.setattr(nodes, "extract_claims", lambda research, evidence: ["extracted claim"])
    updates = {
        "evidence": {"evidence": [{"id": "E1", "source_type": "web", "text": "t", "title": "T", "score": 0.8}]},
        "fact_check": {"fact_checks": [{"claim": "extracted claim", "verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1"]}]},
        "confidence": {"confidence": "high"},
    }
    for name in NODE_NAMES:
        if name == "claim_extraction":
            continue  # keep the real node (uses the monkeypatched extractor)
        update = updates.get(name, {})
        monkeypatch.setattr(nodes, f"{name}_node", make_fake(name, update))

    result = graph_mod.build_research_graph().invoke({"query": "q"})

    assert result["claims"] == ["extracted claim"]
    assert result["fact_checks"][0]["claim"] == "extracted claim"


def test_node_errors_propagate_normally(monkeypatch):
    for name in NODE_NAMES:
        update = {"confidence": "high"} if name == "confidence" else {}
        monkeypatch.setattr(nodes, f"{name}_node", make_fake(name, update))

    def bad_evidence(state):
        raise RuntimeError("boom in evidence")

    monkeypatch.setattr(nodes, "evidence_node", bad_evidence)
    with pytest.raises(RuntimeError, match="boom in evidence"):
        graph_mod.build_research_graph().invoke({"query": "q"})
