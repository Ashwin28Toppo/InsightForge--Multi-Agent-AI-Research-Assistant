"""Offline tests for the FastAPI layer (Phase 2D Steps 1-3).

No external services are contacted: the async pipeline entry point
(``arun_research_pipeline``) and/or the background worker ``_run_job`` are
monkeypatched, so nothing real executes. The Starlette test client runs
background tasks before ``post()`` returns, which keeps every job lifecycle
test deterministic.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

import backend.app.api as api
import backend.app.main as main_mod

# raise_server_exceptions=False ensures server exceptions surface as responses
# instead of being re-raised through the test client.
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


class FakeAsyncGraph:
    """Minimal stand-in for the compiled graph exposing the async contract."""

    def __init__(self, state=None, error=None):
        self.state = state or {}
        self.error = error
        self.ainvoke_calls = []

    async def ainvoke(self, inputs):
        self.ainvoke_calls.append(inputs)
        if self.error is not None:
            raise self.error
        return dict(self.state)


# ── GET /health ──────────────────────────────────────────────────────────────


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ── Application async entry point (main.arun_research_pipeline) ──────────────


def test_arun_research_pipeline_invokes_graph_with_ainvoke(monkeypatch):
    graph = FakeAsyncGraph(
        state={"query": "q", "report_draft": "draft", "search_results": "s"}
    )
    monkeypatch.setattr(main_mod, "research_graph", graph)

    result = asyncio.run(main_mod.arun_research_pipeline("q"))

    assert graph.ainvoke_calls == [{"query": "q"}]  # exact query reached the graph
    assert result["report"] == "draft"              # _to_application_result mapping
    assert result["report_draft"] == "draft"
    assert result["search_results"] == "s"
    assert result["errors"] == []


def test_arun_research_pipeline_raises_when_graph_raises(monkeypatch):
    graph = FakeAsyncGraph(error=RuntimeError("graph boom"))
    monkeypatch.setattr(main_mod, "research_graph", graph)

    with pytest.raises(RuntimeError, match="graph boom"):
        asyncio.run(main_mod.arun_research_pipeline("q"))


def test_sync_and_async_entry_points_share_one_graph():
    # No second graph: both entry points reference the same compiled graph.
    assert (
        main_mod.arun_research_pipeline.__globals__["research_graph"]
        is main_mod.research_graph
    )
    assert (
        main_mod.run_research_pipeline.__globals__["research_graph"]
        is main_mod.research_graph
    )


# ── POST /research ───────────────────────────────────────────────────────────


def test_research_returns_202_and_runs_async_pipeline(monkeypatch):
    pipeline_calls = []

    async def fake_pipeline(query):
        pipeline_calls.append(query)
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "arun_research_pipeline", fake_pipeline)

    response = client.post("/research", json={"query": "test query"})

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"  # handler returned without waiting
    assert body["job_id"]
    assert pipeline_calls == ["test query"]  # exact query reached the async pipeline

    # The (fast) background worker completes the job before the client returns.
    status = client.get(f"/research/{body['job_id']}")
    assert status.status_code == 200
    assert status.json()["status"] == "completed"


@pytest.mark.parametrize("payload", [{"query": ""}, {"query": "   "}])
def test_research_blank_query_rejected(payload):
    response = client.post("/research", json=payload)
    assert response.status_code == 422


def test_research_missing_query_rejected():
    response = client.post("/research", json={})
    assert response.status_code == 422


def test_research_strips_surrounding_whitespace(monkeypatch):
    captured = {}

    def fake_job(job_id, query):
        captured["query"] = query

    monkeypatch.setattr(api, "_run_job", fake_job)

    response = client.post("/research", json={"query": "  padded  "})

    assert response.status_code == 202
    assert captured["query"] == "padded"


# ── GET /research/{job_id} ───────────────────────────────────────────────────


def test_get_queued_job(monkeypatch):
    # A no-op background worker leaves the job in its initial "queued" state.
    monkeypatch.setattr(api, "_run_job", lambda job_id, query: None)

    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]
    response = client.get(f"/research/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["status"] == "queued"
    assert "result" not in body
    assert "error" not in body


def test_get_running_job(monkeypatch):
    def mark_running(job_id, query):
        with api._lock:
            api._jobs[job_id]["status"] = "running"

    monkeypatch.setattr(api, "_run_job", mark_running)

    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]
    response = client.get(f"/research/{job_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_get_completed_job_preserves_result(monkeypatch):
    async def fake_pipeline(query):
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "arun_research_pipeline", fake_pipeline)

    job_id = client.post("/research", json={"query": "test query"}).json()["job_id"]
    response = client.get(f"/research/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["result"]["report"] == "Final research report"
    assert body["result"]["search_results"] == "search summary"
    assert body["result"]["sources"] == ["https://example.com"]
    assert body["result"]["citations"][0]["url"] == "https://example.com"
    assert body["result"]["confidence"] == "high"
    assert body["result"]["errors"] == []


def test_get_failed_job_has_error_and_is_logged(monkeypatch, caplog):
    async def failing_pipeline(query):
        raise RuntimeError("async boom")

    monkeypatch.setattr(api, "arun_research_pipeline", failing_pipeline)

    job_id = client.post("/research", json={"query": "boom"}).json()["job_id"]
    response = client.get(f"/research/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert "async boom" in body["error"]
    # The exception is logged, not silently swallowed.
    assert any("research job" in record.message for record in caplog.records)


def test_get_nonexistent_job_404():
    response = client.get("/research/does-not-exist")
    assert response.status_code == 404


# ── Non-blocking submission guarantee ────────────────────────────────────────


def test_research_does_not_run_pipeline_synchronously(monkeypatch):
    pipeline_calls = []
    background_calls = []

    async def fake_pipeline(query):
        pipeline_calls.append(query)
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "arun_research_pipeline", fake_pipeline)
    monkeypatch.setattr(
        api,
        "_run_job",
        lambda job_id, query: background_calls.append((job_id, query)),
    )

    response = client.post("/research", json={"query": "test query"})

    assert response.status_code == 202
    # The handler returned "queued" without executing the pipeline itself.
    assert response.json()["status"] == "queued"
    assert pipeline_calls == []  # not run synchronously in the handler
    assert background_calls and background_calls[0][1] == "test query"
