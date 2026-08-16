"""Offline tests for the FastAPI layer (Phase 2D Steps 1-3).

No external services are contacted: the async pipeline entry point
(``arun_research_pipeline``) and/or the background worker ``_run_job`` are
monkeypatched, so nothing real executes. The Starlette test client runs
background tasks before ``post()`` returns, which keeps every job lifecycle
test deterministic.
"""
import asyncio
import json
import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone

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


STAGE_UPDATES = [
    ("plan", {"research_plan": {"research_angles": ["a"], "use_rag": False}}),
    ("research", {"search_results": "s", "sources": ["https://a.com"]}),
    ("evidence", {"evidence": [{"id": "E1", "source_type": "web"}]}),
    ("claim_extraction", {"claims": ["c"]}),
    ("fact_check", {"fact_checks": [{"claim": "c", "verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1"]}]}),
    ("citation", {"citations": [{"index": 1, "url": "https://a.com"}]}),
    ("confidence", {"confidence": "high"}),
    ("writer", {"report_draft": "Final research report"}),
    ("critic", {"critic_feedback": "Score: 9/10", "critic_score": 9}),
]


class FakeAsyncStreamingGraph:
    """Fake graph that streams node updates via ``astream`` (like the real graph).

    ``updates`` is a list of ``(node, update)``; ``error_at`` makes the graph
    raise while streaming that node, simulating a mid-pipeline failure.
    """

    def __init__(self, updates=None, error_at=None):
        self.updates = updates or []
        self.error_at = error_at
        self.astream_calls = []

    async def astream(self, inputs, **kwargs):
        self.astream_calls.append((inputs, kwargs))
        for node, update in self.updates:
            if node == self.error_at:
                raise RuntimeError(f"boom at {node}")
            yield {node: update}


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
    # No second graph: every entry point references the same compiled graph.
    assert (
        main_mod.arun_research_pipeline.__globals__["research_graph"]
        is main_mod.research_graph
    )
    assert (
        main_mod.arun_research_pipeline_streaming.__globals__["research_graph"]
        is main_mod.research_graph
    )
    assert (
        main_mod.run_research_pipeline.__globals__["research_graph"]
        is main_mod.research_graph
    )


# ── Application streaming entry point (main.arun_research_pipeline_streaming) ─


def test_arun_streaming_reports_stages_in_order(monkeypatch):
    graph = FakeAsyncStreamingGraph(updates=STAGE_UPDATES)
    monkeypatch.setattr(main_mod, "research_graph", graph)

    events = []
    result = asyncio.run(
        main_mod.arun_research_pipeline_streaming("q", on_step=events.append)
    )

    assert graph.astream_calls[0][0] == {"query": "q"}
    assert events == [
        "plan", "research", "evidence", "claim_extraction", "fact_check",
        "citation", "confidence", "writer", "critic",
    ]
    assert result["report"] == "Final research report"  # result mapping intact
    assert result["errors"] == []


def test_arun_streaming_reports_repeated_research_rounds(monkeypatch):
    # Second round triggered by the conditional research loop (research re-runs
    # without plan; increment_rounds bookkeeping is not surfaced).
    loop_updates = list(STAGE_UPDATES) + [
        ("research", {"search_results": "s2", "sources": ["https://b.com"]}),
        ("evidence", {"evidence": [{"id": "E2", "source_type": "web"}]}),
        ("claim_extraction", {"claims": ["c2"]}),
        ("fact_check", {"fact_checks": [{"claim": "c2", "verdict": "supported", "confidence": 0.8, "evidence_refs": ["E2"]}]}),
        ("citation", {"citations": [{"index": 2, "url": "https://b.com"}]}),
        ("confidence", {"confidence": "high"}),
        ("writer", {"report_draft": "Final research report"}),
        ("critic", {"critic_feedback": "Score: 9/10", "critic_score": 9}),
    ]
    graph = FakeAsyncStreamingGraph(updates=loop_updates)
    monkeypatch.setattr(main_mod, "research_graph", graph)

    events = []
    result = asyncio.run(
        main_mod.arun_research_pipeline_streaming("q", on_step=events.append)
    )

    assert events.count("research") == 2  # repeated research represented safely
    assert events.count("plan") == 1
    assert events[-1] == "critic"
    assert result["report"] == "Final research report"  # final result unchanged


def test_arun_streaming_raises_when_graph_raises(monkeypatch):
    graph = FakeAsyncStreamingGraph(updates=STAGE_UPDATES, error_at="fact_check")
    monkeypatch.setattr(main_mod, "research_graph", graph)

    with pytest.raises(RuntimeError, match="boom at fact_check"):
        asyncio.run(main_mod.arun_research_pipeline_streaming("q"))


# ── POST /research ───────────────────────────────────────────────────────────


def test_research_returns_202_and_runs_async_pipeline(monkeypatch):
    pipeline_calls = []

    async def fake_pipeline(query, on_step=None):
        pipeline_calls.append(query)
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", fake_pipeline)

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
    async def fake_pipeline(query, on_step=None):
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", fake_pipeline)

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
    async def failing_pipeline(query, on_step=None):
        raise RuntimeError("async boom")

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", failing_pipeline)

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


# ── GET /research/{job_id}/progress ──────────────────────────────────────────


def test_progress_unknown_job_404():
    response = client.get("/research/does-not-exist/progress")
    assert response.status_code == 404


def test_progress_queued_job(monkeypatch):
    monkeypatch.setattr(api, "_run_job", lambda job_id, query: None)

    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]
    response = client.get(f"/research/{job_id}/progress")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["status"] == "queued"
    assert body["current_step"] is None
    assert body["completed_steps"] == []


def test_progress_running_job_exposes_current_step(monkeypatch):
    def mark_running(job_id, query):
        with api._lock:
            api._jobs[job_id]["status"] = "running"
            api._jobs[job_id]["current_step"] = "fact_check"
            api._jobs[job_id]["completed_steps"] = [
                "plan", "research", "evidence", "claim_extraction",
            ]

    monkeypatch.setattr(api, "_run_job", mark_running)

    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]
    response = client.get(f"/research/{job_id}/progress")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert body["current_step"] == "fact_check"
    assert body["completed_steps"] == ["plan", "research", "evidence", "claim_extraction"]


def test_progress_completed_job_reflects_stream(monkeypatch):
    stages = [
        "plan", "research", "evidence", "claim_extraction", "fact_check",
        "citation", "confidence", "writer", "critic",
    ]

    async def fake_streaming(query, on_step=None):
        for step in stages:
            if on_step:
                on_step(step)
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", fake_streaming)

    job_id = client.post("/research", json={"query": "test query"}).json()["job_id"]
    progress = client.get(f"/research/{job_id}/progress").json()
    status = client.get(f"/research/{job_id}").json()

    assert progress["status"] == "completed"
    assert progress["current_step"] == "critic"
    assert progress["completed_steps"] == stages
    # Status/result contract is unchanged.
    assert status["status"] == "completed"
    assert status["result"]["report"] == "Final research report"


def test_progress_failed_job_exposes_steps(monkeypatch, caplog):
    async def failing_streaming(query, on_step=None):
        if on_step:
            on_step("plan")
            on_step("research")
        raise RuntimeError("boom at claim_extraction")

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", failing_streaming)

    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]
    progress = client.get(f"/research/{job_id}/progress").json()

    assert progress["status"] == "failed"
    assert progress["current_step"] == "research"
    assert progress["completed_steps"] == ["plan", "research"]
    assert any("research job" in record.message for record in caplog.records)


# ── Non-blocking submission guarantee ────────────────────────────────────────


def test_research_does_not_run_pipeline_synchronously(monkeypatch):
    pipeline_calls = []
    background_calls = []

    async def fake_pipeline(query, on_step=None):
        pipeline_calls.append(query)
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", fake_pipeline)
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


# ── GET /research/{job_id}/stream (SSE) ──────────────────────────────────────

ALL_STAGES = [
    "plan", "research", "evidence", "claim_extraction", "fact_check",
    "citation", "confidence", "writer", "critic",
]


def _seed_job(status="queued", current_step=None, completed_steps=None, error=None):
    """Insert a job directly into the in-memory store (offline)."""
    job_id = str(uuid.uuid4())
    now = api._utcnow()
    with api._lock:
        api._jobs[job_id] = {
            "job_id": job_id,
            "query": "q",
            "status": status,
            "result": None,
            "error": error,
            "current_step": current_step,
            "completed_steps": list(completed_steps or []),
            "created_at": now,
            "updated_at": now,
        }
    return job_id


def _backdate_job(job_id: str, seconds: int) -> None:
    """Rewind a job's ``updated_at`` so it appears older (for TTL tests)."""
    with api._lock:
        api._jobs[job_id]["updated_at"] = api._utcnow() - timedelta(seconds=seconds)


def _parse_sse_data(event: str) -> dict:
    """Parse the ``data:`` line of an SSE event into a dict."""
    for line in event.splitlines():
        if line.startswith("data: "):
            return json.loads(line[len("data: "):])
    raise AssertionError(f"no data line in event: {event!r}")


def test_stream_unknown_job_404():
    response = client.get("/research/does-not-exist/stream")
    assert response.status_code == 404


def test_stream_completed_job_terminates(monkeypatch):
    async def fake_streaming(query, on_step=None):
        for step in ALL_STAGES:
            if on_step:
                on_step(step)
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", fake_streaming)
    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]

    with client.stream("GET", f"/research/{job_id}/stream") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        lines = [line for line in response.iter_lines() if line]

    assert "event: completed" in lines
    payload = _parse_sse_data("\n".join(lines))
    assert payload["status"] == "completed"
    assert payload["current_step"] == "critic"
    assert payload["completed_steps"] == ALL_STAGES


def test_stream_failed_job_terminates(monkeypatch, caplog):
    async def failing_streaming(query, on_step=None):
        if on_step:
            on_step("plan")
            on_step("research")
        raise RuntimeError("boom at claim_extraction")

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", failing_streaming)
    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]

    with client.stream("GET", f"/research/{job_id}/stream") as response:
        assert response.status_code == 200
        lines = [line for line in response.iter_lines() if line]

    assert "event: failed" in lines
    payload = _parse_sse_data("\n".join(lines))
    assert payload["status"] == "failed"
    assert "boom at claim_extraction" in payload["error"]


def test_stream_queued_event(monkeypatch):
    monkeypatch.setattr(api, "_POLL_INTERVAL_SECONDS", 0)
    job_id = _seed_job(status="queued")

    async def first_event():
        gen = api._job_event_stream(job_id)
        return await gen.__anext__()

    event = asyncio.run(first_event())
    assert event.startswith("event: queued\n")
    payload = _parse_sse_data(event)
    assert payload["status"] == "queued"
    assert payload["current_step"] is None
    assert payload["completed_steps"] == []


def test_stream_running_progress_event(monkeypatch):
    monkeypatch.setattr(api, "_POLL_INTERVAL_SECONDS", 0)
    job_id = _seed_job(
        status="running",
        current_step="fact_check",
        completed_steps=["plan", "research", "evidence", "claim_extraction"],
    )

    async def first_event():
        gen = api._job_event_stream(job_id)
        return await gen.__anext__()

    event = asyncio.run(first_event())
    assert event.startswith("event: progress\n")
    payload = _parse_sse_data(event)
    assert payload["status"] == "running"
    assert payload["current_step"] == "fact_check"
    assert payload["completed_steps"] == [
        "plan", "research", "evidence", "claim_extraction",
    ]


def test_stream_event_sequence_and_termination(monkeypatch):
    monkeypatch.setattr(api, "_POLL_INTERVAL_SECONDS", 0)
    job_id = _seed_job(status="queued")

    async def drive():
        gen = api._job_event_stream(job_id)
        events = [await gen.__anext__()]  # queued
        with api._lock:
            job = api._jobs[job_id]
            job["status"] = "running"
            job["current_step"] = "evidence"
            job["completed_steps"] = ["plan", "research", "evidence"]
        events.append(await gen.__anext__())  # progress
        with api._lock:
            job = api._jobs[job_id]
            job["status"] = "completed"
            job["current_step"] = "critic"
            job["completed_steps"] = list(ALL_STAGES)
        events.append(await gen.__anext__())  # completed
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()  # stream terminated after completed
        return events

    events = asyncio.run(drive())
    assert events[0].startswith("event: queued\n")
    assert events[1].startswith("event: progress\n")
    assert events[2].startswith("event: completed\n")
    assert "\"current_step\": \"evidence\"" in events[1]
    assert "\"current_step\": \"critic\"" in events[2]


def test_stream_does_not_execute_pipeline(monkeypatch):
    pipeline_calls = []

    async def fake_streaming(query, on_step=None):
        pipeline_calls.append(query)
        for step in ALL_STAGES:
            if on_step:
                on_step(step)
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", fake_streaming)
    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]
    assert pipeline_calls == ["q"]  # POST's background run

    # Opening the SSE stream must NOT invoke the pipeline again.
    with client.stream("GET", f"/research/{job_id}/stream") as response:
        assert response.status_code == 200
        lines = [line for line in response.iter_lines() if line]

    assert "event: completed" in lines
    assert pipeline_calls == ["q"]  # still exactly one invocation (from POST)


# ── Error-handling hardening (Phase 2D Step 6) ──────────────────────────────


def test_unexpected_exception_returns_structured_500(monkeypatch):
    # Force an unexpected exception inside the POST handler: the global
    # handler must return a safe structured 500 (never a traceback).
    class _BoomResponse:
        def __init__(self, **kwargs):
            raise RuntimeError("response construction boom")

    monkeypatch.setattr(api, "ResearchJobResponse", _BoomResponse)
    monkeypatch.setattr(api, "_run_job", lambda job_id, query: None)

    response = client.post("/research", json={"query": "q"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "Traceback" not in response.text
    assert "boom" not in response.text  # internal message not leaked


def test_validation_error_returns_structured_detail():
    response = client.post("/research", json={"query": "   "})
    assert response.status_code == 422
    # Default FastAPI validation shape: a structured detail list, no traceback.
    assert isinstance(response.json()["detail"], list)
    assert "Traceback" not in response.text


def test_failed_job_error_is_safe_and_contains_no_traceback(monkeypatch, caplog):
    async def failing_pipeline(query, on_step=None):
        raise ValueError("secret failure detail")

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", failing_pipeline)

    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]
    body = client.get(f"/research/{job_id}").json()

    assert body["status"] == "failed"
    assert body["error"] == "ValueError: secret failure detail"
    assert "Traceback" not in body["error"]
    assert any("research job" in record.message for record in caplog.records)


def test_stream_failed_event_contains_no_traceback(monkeypatch):
    async def failing_streaming(query, on_step=None):
        raise RuntimeError("boom in stream")

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", failing_streaming)

    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]
    with client.stream("GET", f"/research/{job_id}/stream") as response:
        lines = [line for line in response.iter_lines() if line]

    event_text = "\n".join(lines)
    assert "event: failed" in event_text
    assert "boom in stream" in event_text
    assert "Traceback" not in event_text


# ── Job TTL / timestamps / cleanup (Phase 2D Step 8) ─────────────────────────


def test_new_job_contains_timestamps(monkeypatch):
    monkeypatch.setattr(api, "_run_job", lambda job_id, query: None)
    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]

    with api._lock:
        job = dict(api._jobs[job_id])

    assert isinstance(job["created_at"], datetime)
    assert isinstance(job["updated_at"], datetime)
    assert job["created_at"].tzinfo is not None  # timezone-aware UTC
    assert job["updated_at"] >= job["created_at"]


def test_updated_at_tracks_lifecycle_transitions(monkeypatch):
    clock = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
    monkeypatch.setattr(api, "_utcnow", lambda: clock[0])
    job_id = _seed_job(status="queued")
    created = api._jobs[job_id]["updated_at"]
    snapshots = {}

    clock[0] += timedelta(seconds=1)  # queued -> running happens here

    async def fake_streaming(query, on_step=None):
        with api._lock:
            snapshots["running"] = dict(api._jobs[job_id])  # running (T1)
        clock[0] += timedelta(seconds=1)  # progress
        if on_step:
            on_step("plan")
        with api._lock:
            snapshots["progress"] = dict(api._jobs[job_id])  # progress (T2)
        clock[0] += timedelta(seconds=1)  # running -> completed
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", fake_streaming)
    api._run_job(job_id, "q")

    final = api._jobs[job_id]
    assert snapshots["running"]["status"] == "running"
    assert snapshots["running"]["updated_at"] > created  # queued -> running
    assert (
        snapshots["progress"]["updated_at"] > snapshots["running"]["updated_at"]
    )  # progress
    assert final["status"] == "completed"
    assert final["updated_at"] > snapshots["progress"]["updated_at"]  # -> completed


def test_updated_at_tracks_failure_transition(monkeypatch):
    clock = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
    monkeypatch.setattr(api, "_utcnow", lambda: clock[0])
    job_id = _seed_job(status="queued")
    created = api._jobs[job_id]["updated_at"]
    snapshots = {}

    clock[0] += timedelta(seconds=1)

    async def failing_streaming(query, on_step=None):
        with api._lock:
            snapshots["running"] = dict(api._jobs[job_id])  # running (T1)
        clock[0] += timedelta(seconds=1)  # running -> failed
        raise RuntimeError("boom")

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", failing_streaming)
    api._run_job(job_id, "q")

    final = api._jobs[job_id]
    assert final["status"] == "failed"
    assert snapshots["running"]["updated_at"] > created  # queued -> running
    assert final["updated_at"] > snapshots["running"]["updated_at"]  # -> failed


def test_cleanup_removes_expired_completed():
    job_id = _seed_job(status="completed")
    _backdate_job(job_id, 7200)  # 2 hours > 3600s TTL

    api._cleanup_expired_jobs()

    with api._lock:
        assert job_id not in api._jobs


def test_cleanup_removes_expired_failed():
    job_id = _seed_job(status="failed", error="RuntimeError: x")
    _backdate_job(job_id, 7200)

    api._cleanup_expired_jobs()

    with api._lock:
        assert job_id not in api._jobs


def test_cleanup_keeps_queued_even_if_old():
    job_id = _seed_job(status="queued")
    _backdate_job(job_id, 7200)

    api._cleanup_expired_jobs()

    with api._lock:
        assert job_id in api._jobs


def test_cleanup_keeps_running_even_if_old():
    job_id = _seed_job(status="running", current_step="research", completed_steps=["plan"])
    _backdate_job(job_id, 7200)

    api._cleanup_expired_jobs()

    with api._lock:
        assert job_id in api._jobs


def test_cleanup_keeps_fresh_completed_and_failed():
    fresh_completed = _seed_job(status="completed")
    fresh_failed = _seed_job(status="failed", error="RuntimeError: x")
    _backdate_job(fresh_completed, 10)  # 10s < TTL
    _backdate_job(fresh_failed, 10)

    api._cleanup_expired_jobs()

    with api._lock:
        assert fresh_completed in api._jobs
        assert fresh_failed in api._jobs


def test_expired_job_status_returns_404():
    job_id = _seed_job(status="completed")
    _backdate_job(job_id, 7200)

    response = client.get(f"/research/{job_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}


def test_expired_job_progress_returns_404():
    job_id = _seed_job(status="completed")
    _backdate_job(job_id, 7200)

    response = client.get(f"/research/{job_id}/progress")

    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}


def test_expired_job_stream_returns_404():
    job_id = _seed_job(status="completed")
    _backdate_job(job_id, 7200)

    response = client.get(f"/research/{job_id}/stream")

    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}


def test_cleanup_does_not_execute_pipeline(monkeypatch):
    pipeline_calls = []

    async def fake_streaming(query, on_step=None):
        pipeline_calls.append(query)
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", fake_streaming)

    job_id = _seed_job(status="completed")
    _backdate_job(job_id, 7200)
    api._cleanup_expired_jobs()

    assert pipeline_calls == []
    with api._lock:
        assert job_id not in api._jobs


def test_cleanup_is_safe_with_the_lock():
    completed_ids = []
    active_ids = []
    for _ in range(5):
        completed_ids.append(_seed_job(status="completed"))
        active_ids.append(_seed_job(status="queued"))
    for job_id in completed_ids:
        _backdate_job(job_id, 7200)

    errors = []

    def run_cleanup():
        try:
            api._cleanup_expired_jobs()
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=run_cleanup) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    with api._lock:
        for job_id in completed_ids:
            assert job_id not in api._jobs
        for job_id in active_ids:
            assert job_id in api._jobs


# ── CORS (Phase 2D Step 7) ───────────────────────────────────────────────────


def test_cors_allowed_origin_localhost():
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_allowed_origin_127():
    response = client.get("/health", headers={"Origin": "http://127.0.0.1:3000"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"


def test_cors_disallowed_origin_not_granted():
    response = client.get("/health", headers={"Origin": "http://evil.example.com"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight_for_post_research():
    response = client.options(
        "/research",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "POST" in response.headers.get("access-control-allow-methods", "")


def test_cors_sse_stream_allowed(monkeypatch):
    async def fake_streaming(query, on_step=None):
        for step in ALL_STAGES:
            if on_step:
                on_step(step)
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", fake_streaming)
    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]

    with client.stream(
        "GET",
        f"/research/{job_id}/stream",
        headers={"Origin": "http://localhost:3000"},
    ) as response:
        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://localhost:3000"
        )
        lines = [line for line in response.iter_lines() if line]

    assert "event: completed" in lines


# ── Request ID / observability (Phase 2D Step 9) ─────────────────────────────


def _completion_records(caplog):
    """The 'request completed' observability log records for the request."""
    return [
        r
        for r in caplog.records
        if r.name == "backend.app.api" and "request completed" in r.message
    ]


def test_health_contains_generated_request_id():
    response = client.get("/health")
    assert response.status_code == 200
    rid = response.headers.get("x-request-id")
    assert rid
    uuid.UUID(rid)  # generated IDs are valid UUIDs


def test_valid_request_id_is_echoed():
    response = client.get("/health", headers={"X-Request-ID": "manual-test-123"})
    assert response.headers.get("x-request-id") == "manual-test-123"


def test_invalid_request_id_with_newline_is_replaced():
    response = client.get("/health", headers={"X-Request-ID": "bad\nid"})
    rid = response.headers.get("x-request-id")
    assert rid != "bad\nid"
    uuid.UUID(rid)


def test_invalid_request_id_with_carriage_return_is_replaced():
    response = client.get("/health", headers={"X-Request-ID": "bad\rid"})
    rid = response.headers.get("x-request-id")
    assert rid != "bad\rid"
    uuid.UUID(rid)


def test_overlong_request_id_is_replaced():
    response = client.get("/health", headers={"X-Request-ID": "a" * 200})
    rid = response.headers.get("x-request-id")
    assert rid != "a" * 200
    uuid.UUID(rid)


def test_is_valid_request_id_rules():
    assert api._is_valid_request_id("abc-123")
    assert api._is_valid_request_id("a" * 128)
    assert not api._is_valid_request_id("")
    assert not api._is_valid_request_id("a" * 129)
    assert not api._is_valid_request_id("bad\nid")
    assert not api._is_valid_request_id("bad\rid")


def test_post_research_response_contains_request_id(monkeypatch):
    monkeypatch.setattr(api, "_run_job", lambda job_id, query: None)
    response = client.post("/research", json={"query": "q"})
    assert response.status_code == 202
    assert response.headers.get("x-request-id")


def test_404_response_contains_request_id():
    response = client.get("/research/does-not-exist")
    assert response.status_code == 404
    assert response.headers.get("x-request-id")


def test_422_response_contains_request_id():
    response = client.post("/research", json={"query": ""})
    assert response.status_code == 422
    assert response.headers.get("x-request-id")


def test_500_response_contains_request_id(monkeypatch):
    class _BoomResponse:
        def __init__(self, **kwargs):
            raise RuntimeError("response construction boom")

    monkeypatch.setattr(api, "ResearchJobResponse", _BoomResponse)
    monkeypatch.setattr(api, "_run_job", lambda job_id, query: None)

    response = client.post("/research", json={"query": "q"})

    assert response.status_code == 500
    assert response.headers.get("x-request-id")


def test_progress_response_contains_request_id(monkeypatch):
    monkeypatch.setattr(api, "_run_job", lambda job_id, query: None)
    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]

    response = client.get(f"/research/{job_id}/progress")

    assert response.status_code == 200
    assert response.headers.get("x-request-id")


def test_sse_response_contains_request_id(monkeypatch):
    async def fake_streaming(query, on_step=None):
        for step in ALL_STAGES:
            if on_step:
                on_step(step)
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", fake_streaming)
    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]

    with client.stream("GET", f"/research/{job_id}/stream") as response:
        assert response.status_code == 200
        assert response.headers.get("x-request-id")
        lines = [line for line in response.iter_lines() if line]

    assert "event: completed" in lines


def test_request_log_contains_all_fields(caplog):
    with caplog.at_level(logging.INFO, logger="backend.app.api"):
        response = client.get("/health")

    records = _completion_records(caplog)
    assert records
    message = records[0].message
    assert f"request_id={response.headers['x-request-id']}" in message
    assert "method=GET" in message
    assert "path=/health" in message
    assert "status=200" in message
    assert "duration_ms=" in message
    duration = message.split("duration_ms=")[1].split()[0]
    assert float(duration) >= 0  # numeric and non-negative, no exact timing


def test_post_research_completion_log_contains_job_id(monkeypatch, caplog):
    monkeypatch.setattr(api, "_run_job", lambda job_id, query: None)
    with caplog.at_level(logging.INFO, logger="backend.app.api"):
        response = client.post("/research", json={"query": "q"})
    job_id = response.json()["job_id"]

    records = _completion_records(caplog)
    assert records
    assert f"job_id={job_id}" in records[-1].message
    assert "method=POST" in records[-1].message
    assert "status=202" in records[-1].message


def test_job_status_completion_log_contains_job_id(monkeypatch, caplog):
    monkeypatch.setattr(api, "_run_job", lambda job_id, query: None)
    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]

    with caplog.at_level(logging.INFO, logger="backend.app.api"):
        client.get(f"/research/{job_id}")

    records = _completion_records(caplog)
    assert records
    assert f"job_id={job_id}" in records[-1].message
    assert "method=GET" in records[-1].message
    assert f"path=/research/{job_id}" in records[-1].message


def test_health_log_has_no_job_id(caplog):
    with caplog.at_level(logging.INFO, logger="backend.app.api"):
        client.get("/health")

    records = _completion_records(caplog)
    assert records
    assert "job_id=" not in records[0].message


def test_request_observability_does_not_execute_pipeline(monkeypatch, caplog):
    pipeline_calls = []

    async def fake_streaming(query, on_step=None):
        pipeline_calls.append(query)
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", fake_streaming)
    monkeypatch.setattr(api, "_run_job", lambda job_id, query: None)

    with caplog.at_level(logging.INFO, logger="backend.app.api"):
        client.get("/health")
        client.get("/research/unknown")
        client.get("/research/unknown/progress")
        client.get("/research/unknown/stream")

    assert pipeline_calls == []  # logging/headers never execute the pipeline
    assert len(_completion_records(caplog)) == 4  # but every request was logged


def test_sse_event_bodies_unchanged(monkeypatch):
    async def fake_streaming(query, on_step=None):
        for step in ALL_STAGES:
            if on_step:
                on_step(step)
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", fake_streaming)
    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]

    with client.stream("GET", f"/research/{job_id}/stream") as response:
        lines = [line for line in response.iter_lines() if line]

    text = "\n".join(lines)
    # Event bodies are unchanged: exact payload shape, and no observability
    # data (request_id) ever leaks into the SSE event JSON.
    assert "request_id" not in text
    assert text.startswith("event: ")
    assert "event: completed" in text
    payload = _parse_sse_data(text)
    assert set(payload) == {"job_id", "status", "current_step", "completed_steps"}
    assert payload["status"] == "completed"


def test_request_ids_do_not_leak_between_requests():
    r1 = client.get("/health", headers={"X-Request-ID": "request-one"})
    r2 = client.get("/health", headers={"X-Request-ID": "request-two"})
    assert r1.headers.get("x-request-id") == "request-one"
    assert r2.headers.get("x-request-id") == "request-two"

    # A headerless request gets its own fresh generated ID, not a stale one.
    generated = client.get("/health").headers.get("x-request-id")
    assert generated and generated not in ("request-one", "request-two")
    uuid.UUID(generated)
    # Two headerless requests get distinct generated IDs.
    second = client.get("/health").headers.get("x-request-id")
    assert second != generated


def test_cors_allows_x_request_id_header():
    response = client.options(
        "/research",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-request-id, content-type",
        },
    )
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin")
        == "http://localhost:3000"
    )
    allowed = response.headers.get("access-control-allow-headers", "").lower()
    assert "x-request-id" in allowed
    # The observability middleware is outermost, so preflight also gets an ID.
    assert response.headers.get("x-request-id")


# ── API contract / OpenAPI (Phase 2D Step 10) ────────────────────────────────


def _openapi() -> dict:
    return client.get("/openapi.json").json()


def _is_nullable_schema(schema: dict) -> bool:
    """True if an OpenAPI 3.1 schema allows null.

    Handles ``nullable: true`` (3.0), ``type: "null"`` and ``type: [...]``
    (3.1), and the ``anyOf``-with-null form Pydantic v2 emits.
    """
    if schema.get("nullable"):
        return True
    if schema.get("type") == "null":
        return True
    if isinstance(schema.get("type"), list):
        return "null" in schema["type"]
    if "anyOf" in schema:
        return any(_is_nullable_schema(item) for item in schema["anyOf"])
    return False


def test_openapi_lists_all_endpoints_and_methods():
    spec = _openapi()
    assert spec["openapi"].startswith("3.1")
    assert set(spec["paths"]) == {
        "/health",
        "/research",
        "/research/{job_id}",
        "/research/{job_id}/progress",
        "/research/{job_id}/stream",
    }
    assert list(spec["paths"]["/health"]) == ["get"]
    assert list(spec["paths"]["/research"]) == ["post"]
    assert list(spec["paths"]["/research/{job_id}"]) == ["get"]
    assert list(spec["paths"]["/research/{job_id}/progress"]) == ["get"]
    assert list(spec["paths"]["/research/{job_id}/stream"]) == ["get"]


def _resolve_ref(spec: dict, schema: dict) -> dict:
    """Resolve a ``$ref`` to the referenced component schema (if any)."""
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return spec["components"]["schemas"][name]
    return schema


def test_openapi_health_response_schema():
    spec = _openapi()
    schema = _resolve_ref(
        spec,
        spec["paths"]["/health"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"],
    )
    assert set(schema["properties"]) == {"status"}
    assert schema["properties"]["status"]["type"] == "string"


def test_openapi_post_research_request_schema():
    spec = _openapi()
    op = spec["paths"]["/research"]["post"]
    body = op["requestBody"]
    assert body["required"] is True
    assert (
        body["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ResearchRequest"
    )
    props = spec["components"]["schemas"]["ResearchRequest"]["properties"]
    assert set(props) == {"query"}
    assert props["query"]["type"] == "string"
    assert props["query"]["minLength"] == 1
    assert "422" in op["responses"]  # validation error documented


def test_openapi_post_research_response_schema():
    spec = _openapi()
    schema = spec["components"]["schemas"]["ResearchJobResponse"]
    assert set(schema["properties"]) == {"job_id", "status"}
    assert schema["properties"]["status"]["const"] == "queued"
    op = spec["paths"]["/research"]["post"]
    ref = op["responses"]["202"]["content"]["application/json"]["schema"]["$ref"]
    assert ref.endswith("ResearchJobResponse")


def test_openapi_status_schema_matches_contract():
    spec = _openapi()
    schema = spec["components"]["schemas"]["ResearchStatusResponse"]
    props = schema["properties"]
    assert set(props) == {"job_id", "status", "result", "error"}
    assert set(props["status"]["enum"]) == {
        "queued", "running", "completed", "failed",
    }
    assert _is_nullable_schema(props["result"])
    assert _is_nullable_schema(props["error"])


def test_openapi_progress_schema_nullable_current_step():
    spec = _openapi()
    schema = spec["components"]["schemas"]["ResearchProgressResponse"]
    props = schema["properties"]
    assert set(props) == {"job_id", "status", "current_step", "completed_steps"}
    assert _is_nullable_schema(props["current_step"])  # accurately nullable
    assert props["completed_steps"]["type"] == "array"
    assert props["completed_steps"]["items"]["type"] == "string"


def test_openapi_stream_documented_as_text_event_stream():
    spec = _openapi()
    op = spec["paths"]["/research/{job_id}/stream"]["get"]
    content = op["responses"]["200"]["content"]
    assert "text/event-stream" in content
    assert "application/json" not in content  # no misleading JSON media type
    assert "404" in op["responses"]


def test_openapi_documents_expected_errors():
    spec = _openapi()
    status_op = spec["paths"]["/research/{job_id}"]["get"]
    assert "404" in status_op["responses"]
    assert "500" in status_op["responses"]
    assert "404" in spec["paths"]["/research/{job_id}/progress"]["get"]["responses"]
    assert "404" in spec["paths"]["/research/{job_id}/stream"]["get"]["responses"]
    assert "500" in spec["paths"]["/health"]["get"]["responses"]


def test_contract_post_research_response_schema(monkeypatch):
    monkeypatch.setattr(api, "_run_job", lambda job_id, query: None)
    response = client.post("/research", json={"query": "q"})
    assert response.status_code == 202
    assert set(response.json()) == {"job_id", "status"}
    assert response.json()["status"] == "queued"


def test_contract_job_status_schema_queued(monkeypatch):
    monkeypatch.setattr(api, "_run_job", lambda job_id, query: None)
    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]
    body = client.get(f"/research/{job_id}").json()
    assert set(body) == {"job_id", "status"}  # no result/error while queued


def test_contract_job_status_schema_completed(monkeypatch):
    async def fake_streaming(query, on_step=None):
        return dict(REPRESENTATIVE_RESULT)

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", fake_streaming)
    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]
    body = client.get(f"/research/{job_id}").json()
    assert set(body) == {"job_id", "status", "result"}
    assert body["status"] == "completed"
    assert body["result"]["report"] == "Final research report"


def test_contract_job_status_schema_failed(monkeypatch):
    async def failing_streaming(query, on_step=None):
        raise RuntimeError("contract boom")

    monkeypatch.setattr(api, "arun_research_pipeline_streaming", failing_streaming)
    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]
    body = client.get(f"/research/{job_id}").json()
    assert set(body) == {"job_id", "status", "error"}
    assert body["status"] == "failed"
    assert "contract boom" in body["error"]


def test_contract_progress_schema(monkeypatch):
    monkeypatch.setattr(api, "_run_job", lambda job_id, query: None)
    job_id = client.post("/research", json={"query": "q"}).json()["job_id"]
    body = client.get(f"/research/{job_id}/progress").json()
    assert set(body) == {"job_id", "status", "current_step", "completed_steps"}
    assert body["current_step"] is None
    assert body["completed_steps"] == []
