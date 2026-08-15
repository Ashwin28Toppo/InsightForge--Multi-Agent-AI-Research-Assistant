"""Offline tests for the FastAPI layer (Phase 2D Steps 1-2).

No external services are contacted: ``run_research_pipeline`` and/or the
background worker ``_run_job`` are monkeypatched, so nothing real executes.
The Starlette test client runs background tasks before ``post()`` returns,
which keeps every job lifecycle test deterministic.
"""
import pytest
from fastapi.testclient import TestClient

import backend.app.api as api

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


# ── GET /health ──────────────────────────────────────────────────────────────


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ── POST /research ───────────────────────────────────────────────────────────


def test_research_returns_202_and_runs_pipeline(monkeypatch):
    pipeline_calls = []
    monkeypatch.setattr(
        api,
        "run_research_pipeline",
        lambda query: pipeline_calls.append(query) or dict(REPRESENTATIVE_RESULT),
    )

    response = client.post("/research", json={"query": "test query"})

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"  # handler returned without waiting
    assert body["job_id"]
    assert pipeline_calls == ["test query"]  # exact query reached the pipeline


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
    monkeypatch.setattr(
        api, "run_research_pipeline", lambda query: dict(REPRESENTATIVE_RESULT)
    )

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


def test_get_failed_job_has_error(monkeypatch):
    def failing_pipeline(query):
        raise RuntimeError("pipeline exploded")

    monkeypatch.setattr(api, "run_research_pipeline", failing_pipeline)

    job_id = client.post("/research", json={"query": "boom"}).json()["job_id"]
    response = client.get(f"/research/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert "pipeline exploded" in body["error"]


def test_get_nonexistent_job_404():
    response = client.get("/research/does-not-exist")
    assert response.status_code == 404


# ── Non-blocking submission guarantee ────────────────────────────────────────


def test_research_does_not_run_pipeline_synchronously(monkeypatch):
    pipeline_calls = []
    background_calls = []
    monkeypatch.setattr(
        api,
        "run_research_pipeline",
        lambda query: pipeline_calls.append(query) or dict(REPRESENTATIVE_RESULT),
    )
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
