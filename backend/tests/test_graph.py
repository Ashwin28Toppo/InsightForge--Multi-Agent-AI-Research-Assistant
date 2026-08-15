"""Unit tests for the linear research StateGraph (Phase 2C Step 2).

All tests are offline: graph execution uses fake node functions patched into
``backend.app.graph.nodes``, so no LLM/Tavily/Qdrant calls are made. The real
graph is only built (never executed) for topology inspection.
"""
import copy

import pytest

import backend.app.graph.graph as graph_mod
import backend.app.graph.nodes as nodes

NODE_NAMES = [
    "plan",
    "research",
    "evidence",
    "fact_check",
    "citation",
    "confidence",
    "writer",
    "critic",
]

LINEAR_EDGES = [
    ("__start__", "plan"),
    ("plan", "research"),
    ("research", "evidence"),
    ("evidence", "fact_check"),
    ("fact_check", "citation"),
    ("citation", "confidence"),
    ("confidence", "writer"),
    ("writer", "critic"),
    ("critic", "__end__"),
]


def edge_pairs(compiled):
    return [(e.source, e.target) for e in compiled.get_graph().edges]


def make_fake(name, update):
    def fake(state):
        return update

    fake.__name__ = name
    return fake


def patch_all_nodes(monkeypatch, updates=None):
    """Replace every node with a fake returning its (default) update."""
    executed = []
    defaults = {
        "plan": {"research_plan": {"research_angles": ["a"], "use_rag": False}},
        "research": {"search_results": "text", "sources": ["https://a.com"]},
        "evidence": [{"id": "E1", "source_type": "web", "text": "t", "title": "T", "score": 0.8}],
        "fact_check": [{"claim": "c", "verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1"]}],
        "citation": [{"index": 1, "source_type": "web", "title": "T", "url": "https://a.com",
                      "document_id": None, "page": None, "chunk_index": None}],
        "confidence": "high",
        "writer": "draft",
        "critic": ("Score: 8/10", 8),
    }
    updates = updates or {}

    def fake_for(name):
        update = updates.get(name, defaults[name])
        if name == "evidence":
            result = {"evidence": update}
        elif name == "fact_check":
            result = {"fact_checks": update}
        elif name == "citation":
            result = {"citations": update}
        elif name == "confidence":
            result = {"confidence": update}
        elif name == "writer":
            result = {"report_draft": update}
        elif name == "critic":
            result = {"critic_feedback": update[0], "critic_score": update[1]}
        else:  # plan, research
            result = update
        return make_fake(name, result)

    for name in NODE_NAMES:
        monkeypatch.setattr(nodes, f"{name}_node", fake_for(name))
    return executed


# ── Build & topology ─────────────────────────────────────────────────────────

def test_graph_builds_successfully():
    compiled = graph_mod.build_research_graph()
    assert hasattr(compiled, "invoke")
    assert compiled.get_graph() is not None


def test_all_expected_nodes_exist():
    compiled = graph_mod.build_research_graph()
    node_names = set(compiled.get_graph().nodes.keys())
    for name in NODE_NAMES:
        assert name in node_names


@pytest.mark.parametrize("source,target", LINEAR_EDGES)
def test_expected_edge_exists(source, target):
    edges = edge_pairs(graph_mod.build_research_graph())
    assert (source, target) in edges


def test_start_connects_to_plan():
    assert ("__start__", "plan") in edge_pairs(graph_mod.build_research_graph())


def test_critic_connects_to_end():
    assert ("critic", "__end__") in edge_pairs(graph_mod.build_research_graph())


def test_graph_is_linear_for_this_step():
    edges = edge_pairs(graph_mod.build_research_graph())
    # Exactly the linear chain — no extra edges, no branches.
    assert sorted(edges) == sorted(LINEAR_EDGES)


def test_compilation_is_deterministic():
    a = graph_mod.build_research_graph()
    b = graph_mod.build_research_graph()
    assert sorted(edge_pairs(a)) == sorted(edge_pairs(b))
    assert set(a.get_graph().nodes.keys()) == set(b.get_graph().nodes.keys())


def test_module_level_graph_exists():
    assert hasattr(graph_mod, "research_graph")
    assert hasattr(graph_mod.research_graph, "invoke")


# ── Execution (fake nodes, no network) ───────────────────────────────────────

def test_execution_order_is_correct(monkeypatch):
    executed = []
    for name in NODE_NAMES:
        def fake(state, _name=name):
            executed.append(_name)
            return {}

        fake.__name__ = name
        monkeypatch.setattr(nodes, f"{name}_node", fake)

    graph_mod.build_research_graph().invoke({"query": "q"})
    assert executed == NODE_NAMES


def test_invocation_passes_state_and_preserves_input(monkeypatch):
    for name in NODE_NAMES:
        monkeypatch.setattr(nodes, f"{name}_node", make_fake(name, {}))

    initial = {"query": "What are the latest developments in AI agents?"}
    before = copy.deepcopy(initial)
    result = graph_mod.build_research_graph().invoke(initial)

    assert result["query"] == "What are the latest developments in AI agents?"
    assert initial == before  # input not unexpectedly mutated


def test_node_outputs_appear_in_final_state(monkeypatch):
    patch_all_nodes(monkeypatch)
    result = graph_mod.build_research_graph().invoke({"query": "q"})

    assert result["research_plan"]["use_rag"] is False
    assert result["search_results"] == "text"
    assert result["sources"] == ["https://a.com"]
    assert result["evidence"][0]["id"] == "E1"
    assert result["fact_checks"][0]["verdict"] == "supported"
    assert result["citations"][0]["index"] == 1
    assert result["confidence"] == "high"
    assert result["report_draft"] == "draft"
    assert result["critic_feedback"] == "Score: 8/10"
    assert result["critic_score"] == 8


def test_minimal_query_executes_with_fake_nodes(monkeypatch):
    patch_all_nodes(monkeypatch)
    result = graph_mod.build_research_graph().invoke({"query": "q"})
    assert result["query"] == "q"
    assert "report_draft" in result


def test_route_research_is_not_used(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("route_research must not be part of this graph")

    monkeypatch.setattr("backend.app.agents.confidence.route_research", boom)
    patch_all_nodes(monkeypatch)
    # No exception: routing is never executed.
    graph_mod.build_research_graph().invoke({"query": "q"})


def test_node_errors_propagate_normally(monkeypatch):
    for name in NODE_NAMES:
        monkeypatch.setattr(nodes, f"{name}_node", make_fake(name, {}))

    def bad_evidence(state):
        raise RuntimeError("boom in evidence")

    monkeypatch.setattr(nodes, "evidence_node", bad_evidence)
    with pytest.raises(RuntimeError, match="boom in evidence"):
        graph_mod.build_research_graph().invoke({"query": "q"})
