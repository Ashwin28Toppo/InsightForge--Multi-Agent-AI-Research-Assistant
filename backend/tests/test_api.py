"""Offline tests for the FastAPI layer (Phase 2D Step 1).

No external services are contacted: ``run_research_pipeline`` is monkeypatched
so the underlying pipeline (LLM/Tavily/Qdrant) never executes.
"""
import pytest
from fastapi.testclient import TestClient

import backend.app.api as api

# raise_server_exceptions=False lets a pipeline exception surface as an HTTP 500
# (instead of being re-raised through the test client), which is exactly what
# the error-propagation test needs to observe.
client = TestClient(api.app, raise_server_exceptions=False)

REPRESENTATIVE_RESULT = {
    "query": "test query",
    "report": "Final research report",
    "report_draft": "Final research report",
    "search_results": "search summary",
    "sources": ["https://example.com"],
    "citations": [
        {
            "index": 1,
            "source_type": "web",
            "title": "Example",
            "url": "https://example.com",
            "document_id": None,
            "page": None,
            "chunk_index": None,
        }
    ],
    "confidence": "high",
    "critic_feedback": "Score: 8/10",
    "critic_score": 8,
    "errors": [],
}


# ── GET /health ──────────────────────────────────────────────────────────────


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ── POST /research ───────────────────────────────────────────────────────────


def test_research_valid_query_calls_pipeline(monkeypatch):
    captured = {}

    def fake_pipeline(query):
        captured["query"] = query
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "run_research_pipeline", fake_pipeline)

    response = client.post("/research", json={"query": "test query"})

    assert response.status_code == 200
    body = response.json()
    assert captured["query"] == "test query"  # exact query reached the pipeline
    assert body["report"] == "Final research report"
    assert body["report_draft"] == "Final research report"
    assert body["search_results"] == "search summary"
    assert body["sources"] == ["https://example.com"]
    assert body["citations"][0]["url"] == "https://example.com"
    assert body["confidence"] == "high"
    assert body["critic_feedback"] == "Score: 8/10"
    assert body["errors"] == []


@pytest.mark.parametrize("payload", [{"query": ""}, {"query": "   "}])
def test_research_blank_query_rejected(monkeypatch, payload):
    def boom(query):
        raise AssertionError("pipeline must not be called for a blank query")

    monkeypatch.setattr(api, "run_research_pipeline", boom)

    response = client.post("/research", json=payload)

    assert response.status_code == 422


def test_research_missing_query_rejected():
    response = client.post("/research", json={})
    assert response.status_code == 422


def test_research_pipeline_exception_propagates(monkeypatch):
    def failing_pipeline(query):
        raise RuntimeError("pipeline exploded")

    monkeypatch.setattr(api, "run_research_pipeline", failing_pipeline)

    response = client.post("/research", json={"query": "boom"})

    # The API must not mask a pipeline failure with a fake success.
    assert response.status_code == 500


def test_research_strips_surrounding_whitespace(monkeypatch):
    captured = {}

    def fake_pipeline(query):
        captured["query"] = query
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "run_research_pipeline", fake_pipeline)

    response = client.post("/research", json={"query": "  padded  "})

    assert response.status_code == 200
    assert captured["query"] == "padded"
