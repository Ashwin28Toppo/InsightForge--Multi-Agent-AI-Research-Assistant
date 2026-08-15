"""Unit tests for ``backend.app.main`` (LangGraph integration)."""
import pytest

import backend.app.main as main
from backend.app.main import build_research_context


class FakeGraph:
    """Minimal stand-in for the compiled research graph."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def invoke(self, inputs):
        self.calls.append(inputs)
        if self.error is not None:
            raise self.error
        return self.result


class _RaisingChain:
    def invoke(self, *args, **kwargs):
        raise AssertionError("must not call chain directly")


def test_build_research_context_combines_both_sections():
    out = build_research_context("SEARCH_BODY", "SCRAPE_BODY")
    assert "SEARCH RESULTS" in out
    assert "DETAILED SCRAPED CONTENT" in out
    assert "SEARCH_BODY" in out
    assert "SCRAPE_BODY" in out


def test_run_research_pipeline_invokes_research_graph(monkeypatch):
    graph = FakeGraph(result={
        "query": "q",
        "report_draft": "draft",
        "search_results": "results",
        "critic_feedback": "Score: 7/10",
    })
    monkeypatch.setattr(main, "research_graph", graph)

    result = main.run_research_pipeline("What is AI?")

    assert graph.calls == [{"query": "What is AI?"}]  # query reaches the graph
    assert result["search_results"] == "results"
    assert result["critic_feedback"] == "Score: 7/10"


def test_query_reaches_research_graph(monkeypatch):
    graph = FakeGraph(result={"query": "q"})
    monkeypatch.setattr(main, "research_graph", graph)

    main.run_research_pipeline("my topic")

    assert graph.calls[0]["query"] == "my topic"


def test_graph_result_mapped_to_application_contract(monkeypatch):
    state = {
        "query": "q",
        "report_draft": "final draft",
        "search_results": "results",
        "sources": ["https://a.com"],
        "citations": [{"index": 1, "source_type": "web", "title": "T", "url": "https://a.com"}],
        "confidence": "high",
        "critic_feedback": "Score: 8/10",
        "critic_score": 8,
    }
    monkeypatch.setattr(main, "research_graph", FakeGraph(result=state))

    result = main.run_research_pipeline("q")

    assert result["report"] == "final draft"         # report_draft -> report
    assert result["report_draft"] == "final draft"   # original key preserved
    assert result["sources"] == ["https://a.com"]
    assert result["citations"][0]["index"] == 1
    assert result["confidence"] == "high"
    assert result["critic_score"] == 8
    assert result["errors"] == []                    # contract default


def test_pipeline_does_not_manually_orchestrate_nodes(monkeypatch):
    # If run_research_pipeline called any node/chain directly, these would raise.
    def raise_builder(*args, **kwargs):
        raise AssertionError("must not build agents directly")

    monkeypatch.setattr(main, "build_search_agent", raise_builder)
    monkeypatch.setattr(main, "build_reader_agent", raise_builder)
    monkeypatch.setattr(main, "writer_chain", _RaisingChain())
    monkeypatch.setattr(main, "critic_chain", _RaisingChain())
    graph = FakeGraph(result={"query": "q", "report_draft": "d"})
    monkeypatch.setattr(main, "research_graph", graph)

    result = main.run_research_pipeline("q")

    assert result["report"] == "d"


def test_graph_exceptions_are_not_swallowed(monkeypatch):
    graph = FakeGraph(error=RuntimeError("graph boom"))
    monkeypatch.setattr(main, "research_graph", graph)

    with pytest.raises(RuntimeError, match="graph boom"):
        main.run_research_pipeline("q")


def test_on_step_parameter_accepted_for_compatibility(monkeypatch):
    monkeypatch.setattr(main, "research_graph", FakeGraph(result={"query": "q", "report_draft": "d"}))

    on_step_calls = []
    result = main.run_research_pipeline("q", on_step=on_step_calls.append)

    assert result["report"] == "d"
    # on_step is accepted (backward compatibility) but not driven by this module.
    assert on_step_calls == []
