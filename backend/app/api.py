"""FastAPI transport layer for the InsightForge research pipeline.

Thin transport layer (Phase 2D Steps 1-2). Research execution is delegated to
``backend.app.main.run_research_pipeline``; this module only owns job lifecycle
management over an in-memory job store (queued -> running -> completed | failed).

Endpoints:
    GET  /health             - liveness probe (never runs the pipeline).
    POST /research           - create an async research job (HTTP 202 + job_id).
    GET  /research/{job_id}  - current job status/result.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.app.main import arun_research_pipeline_streaming

logger = logging.getLogger(__name__)

app = FastAPI(
    title="InsightForge API",
    description=(
        "Multi-Agent AI Research Assistant — exposes the existing LangGraph "
        "research pipeline over HTTP. Thin transport layer only."
    ),
    version="0.2.0",
)


# ── In-memory job store (by design; jobs are lost on restart) ────────────────

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


class ResearchRequest(BaseModel):
    """Request body for ``POST /research``."""

    query: str

    @field_validator("query")
    @classmethod
    def _query_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must not be empty or whitespace-only")
        return stripped


class ResearchJobResponse(BaseModel):
    """Response returned immediately when a research job is submitted."""

    job_id: str
    status: str


class ResearchStatusResponse(BaseModel):
    """Current status of a research job (result only when completed)."""

    job_id: str
    status: str
    result: dict | None = None
    error: str | None = None


class ResearchProgressResponse(BaseModel):
    """Live progress of a research job (status/result live on the other endpoint)."""

    job_id: str
    status: str
    current_step: str | None = None
    completed_steps: list[str] = Field(default_factory=list)


def _run_job(job_id: str, query: str) -> None:
    """Background worker: run the async streaming pipeline and store the outcome.

    Lifecycle: queued -> running -> completed, or -> failed on exception.

    The async pipeline (``research_graph.astream`` via
    ``arun_research_pipeline_streaming``) runs in a dedicated event loop inside
    this worker thread (``asyncio.run``), so the server's event loop is never
    blocked by the long-running research. Each completed logical stage is
    recorded on the job (``current_step`` + ``completed_steps``) through the
    ``on_step`` callback. Exceptions are never swallowed silently — they are
    logged and surfaced on the job record as a safe error string.
    """
    with _lock:
        job = _jobs.get(job_id)
        if job is not None:
            job["status"] = "running"
            job["current_step"] = None
            job["completed_steps"] = []

    def on_step(step: str) -> None:
        with _lock:
            current = _jobs.get(job_id)
            if current is None:
                return
            current["current_step"] = step
            current["completed_steps"] = list(current["completed_steps"]) + [step]

    try:
        result = asyncio.run(
            arun_research_pipeline_streaming(query, on_step=on_step)
        )
    except Exception as exc:
        logger.exception("research job %s failed", job_id)
        with _lock:
            if job is not None:
                job["status"] = "failed"
                job["error"] = f"{type(exc).__name__}: {exc}"
        return

    with _lock:
        if job is not None:
            job["status"] = "completed"
            job["result"] = result


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Does not execute the research pipeline."""
    return {"status": "ok"}


@app.post("/research", status_code=202, response_model=ResearchJobResponse)
def research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
) -> ResearchJobResponse:
    """Submit a research job and return immediately with its job id.

    The pipeline runs in the background via ``BackgroundTasks``; the client
    polls ``GET /research/{job_id}`` for the outcome.
    """
    job_id = str(uuid4())
    with _lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "query": request.query,
            "status": "queued",
            "result": None,
            "error": None,
            "current_step": None,
            "completed_steps": [],
        }
    background_tasks.add_task(_run_job, job_id, request.query)
    return ResearchJobResponse(job_id=job_id, status="queued")


@app.get(
    "/research/{job_id}",
    response_model=ResearchStatusResponse,
    response_model_exclude_none=True,
)
def research_status(job_id: str) -> ResearchStatusResponse:
    """Return the current status/result of a research job (404 if unknown)."""
    with _lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    payload: dict = {"job_id": job["job_id"], "status": job["status"]}
    if job["status"] == "completed":
        payload["result"] = job["result"]
    elif job["status"] == "failed":
        payload["error"] = job["error"]
    return ResearchStatusResponse(**payload)


@app.get("/research/{job_id}/progress", response_model=ResearchProgressResponse)
def research_progress(job_id: str) -> ResearchProgressResponse:
    """Return the live progress of a research job (404 if unknown).

    ``current_step`` is the most recent logical stage reported as completed by
    the graph; ``completed_steps`` is an ordered event list (stages may repeat
    when the conditional research loop re-runs research).
    """
    with _lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return ResearchProgressResponse(
        job_id=job["job_id"],
        status=job["status"],
        current_step=job.get("current_step"),
        completed_steps=list(job.get("completed_steps") or []),
    )
