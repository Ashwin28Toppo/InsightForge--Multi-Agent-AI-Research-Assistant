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
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import AsyncIterator
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.core.config import settings
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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler: never leak Python tracebacks to API clients.

    The full exception is logged server-side; the client only ever receives a
    safe, structured ``{"detail": "Internal server error"}`` response. More
    specific handlers (e.g. ``HTTPException`` for 404, Pydantic validation for
    422) keep taking precedence over this one.

    This handler runs at the outermost ``ServerErrorMiddleware`` level (which
    owns the ``Exception``/500 handler), so it attaches the request-scoped
    ``X-Request-ID`` itself — the observability middleware never sees this
    response.
    """
    logger.exception(
        "unhandled exception on %s %s", request.method, request.url.path
    )
    response = JSONResponse(
        status_code=500, content={"detail": "Internal server error"}
    )
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        response.headers[_REQUEST_ID_HEADER] = request_id
    return response


# ── Request ID / observability (Phase 2D Step 9) ─────────────────────────────
# Every response carries an ``X-Request-ID``: the client-supplied value when it
# is safe, otherwise a fresh UUID. The ID is request-scoped (kept on
# ``request.state`` — i.e. in the per-request ASGI scope — never a global), so
# concurrent requests, background workers, asyncio and SSE are unaffected.

_REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_MAX_LENGTH = 128


def _is_valid_request_id(value: str) -> bool:
    """A safe request ID is 1-128 characters with no control characters.

    Rejecting control characters (including ``\r`` and ``\n``) prevents
    header/log injection while keeping the API usable — an invalid incoming
    value is simply replaced, never rejected with a 400.
    """
    if not 1 <= len(value) <= _REQUEST_ID_MAX_LENGTH:
        return False
    return not any(ord(ch) < 32 or ord(ch) == 127 for ch in value)


def _resolve_request_id(request: Request) -> str:
    """Return the validated incoming ``X-Request-ID``, or a fresh UUID."""
    incoming = request.headers.get(_REQUEST_ID_HEADER)
    if incoming is not None and _is_valid_request_id(incoming):
        return incoming
    return str(uuid4())


def _log_request_completion(
    request: Request, status_code: int, duration_ms: float
) -> None:
    """One structured key=value log line per completed HTTP request.

    ``job_id`` is included only for requests that involve one: ``POST
    /research`` records it on ``request.state``, while the job endpoints read
    it from the path params. No job_id is added where none exists.
    """
    job_id = getattr(request.state, "job_id", None)
    if job_id is None:
        job_id = request.path_params.get("job_id")
    fields = [
        f"request_id={getattr(request.state, 'request_id', '-')}",
        f"method={request.method}",
        f"path={request.url.path}",
        f"status={status_code}",
        f"duration_ms={duration_ms:.2f}",
    ]
    if job_id:
        fields.append(f"job_id={job_id}")
    logger.info("request completed %s", " ".join(fields))


async def request_observability_middleware(
    request: Request, call_next
) -> Response:
    """Attach an ``X-Request-ID`` to every response and log its completion.

    Lightweight by design: only a monotonic clock read, header bookkeeping and
    one log line — no network, storage, database or pipeline access. When an
    unhandled exception escapes to the outermost ``ServerErrorMiddleware``,
    the completion is logged here (status=500) before re-raising; the 500
    response itself gets its ``X-Request-ID`` from the exception handler,
    which runs at that same outermost level.
    """
    start = time.perf_counter()
    request_id = _resolve_request_id(request)
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000.0
        _log_request_completion(request, 500, duration_ms)
        raise
    response.headers[_REQUEST_ID_HEADER] = request_id
    duration_ms = (time.perf_counter() - start) * 1000.0
    _log_request_completion(request, response.status_code, duration_ms)
    return response


# ── CORS (API transport concern only — no auth, no secrets) ─────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# Registered AFTER CORS (Starlette middleware order: last added = outermost),
# so the observability middleware wraps CORS and even CORS preflight responses
# carry an ``X-Request-ID``. The outermost ``ServerErrorMiddleware``'s 500
# responses are covered by the exception handler above.
app.add_middleware(
    BaseHTTPMiddleware, dispatch=request_observability_middleware
)


# ── In-memory job store (by design; jobs are lost on restart) ────────────────

_jobs: dict[str, dict] = {}
_lock = threading.Lock()

# How often the SSE stream polls the job store for changes — keeps the stream
# responsive without busy-spinning the CPU.
_POLL_INTERVAL_SECONDS = 0.5


def _utcnow() -> datetime:
    """Timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


def _cleanup_expired_jobs() -> None:
    """Remove terminal jobs older than ``settings.job_ttl_seconds``.

    Only ``completed``/``failed`` jobs are ever deleted; ``queued`` and
    ``running`` jobs are never touched. Runs under the existing job lock (a
    single acquisition), is idempotent, and never executes the pipeline.
    """
    ttl = settings.job_ttl_seconds
    now = _utcnow()
    with _lock:
        expired = [
            job_id
            for job_id, job in _jobs.items()
            if job.get("status") in ("completed", "failed")
            and isinstance(job.get("updated_at"), datetime)
            and (now - job["updated_at"]).total_seconds() > ttl
        ]
        for job_id in expired:
            del _jobs[job_id]


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
            job["updated_at"] = _utcnow()

    def on_step(step: str) -> None:
        with _lock:
            current = _jobs.get(job_id)
            if current is None:
                return
            current["current_step"] = step
            current["completed_steps"] = list(current["completed_steps"]) + [step]
            current["updated_at"] = _utcnow()

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
                job["updated_at"] = _utcnow()
        return

    with _lock:
        if job is not None:
            job["status"] = "completed"
            job["result"] = result
            job["updated_at"] = _utcnow()


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Does not execute the research pipeline."""
    return {"status": "ok"}


@app.post("/research", status_code=202, response_model=ResearchJobResponse)
def research(
    request: Request,
    payload: ResearchRequest,
    background_tasks: BackgroundTasks,
) -> ResearchJobResponse:
    """Submit a research job and return immediately with its job id.

    The pipeline runs in the background via ``BackgroundTasks``; the client
    polls ``GET /research/{job_id}`` for the outcome. The new job id is
    recorded on ``request.state`` so the observability middleware can
    correlate this request's completion log with the job.
    """
    _cleanup_expired_jobs()
    job_id = str(uuid4())
    request.state.job_id = job_id
    now = _utcnow()
    with _lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "query": payload.query,
            "status": "queued",
            "result": None,
            "error": None,
            "current_step": None,
            "completed_steps": [],
            "created_at": now,
            "updated_at": now,
        }
    background_tasks.add_task(_run_job, job_id, payload.query)
    return ResearchJobResponse(job_id=job_id, status="queued")


@app.get(
    "/research/{job_id}",
    response_model=ResearchStatusResponse,
    response_model_exclude_none=True,
)
def research_status(job_id: str) -> ResearchStatusResponse:
    """Return the current status/result of a research job (404 if unknown)."""
    _cleanup_expired_jobs()
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
    _cleanup_expired_jobs()
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


# ── SSE progress stream (observes only — never runs the pipeline) ────────────


def _format_sse(event: str, data: dict) -> str:
    """Format one Server-Sent Event (``event`` line + JSON ``data`` block)."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _progress_payload(job: dict) -> dict:
    """The progress payload shared by all SSE events."""
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "current_step": job.get("current_step"),
        "completed_steps": list(job.get("completed_steps") or []),
    }


def _sse_event_for(job: dict) -> str | None:
    """Map a job's current state to an SSE event string (None if unknown)."""
    status = job["status"]
    payload = _progress_payload(job)
    if status == "queued":
        return _format_sse("queued", payload)
    if status == "running":
        return _format_sse("progress", payload)
    if status == "completed":
        return _format_sse("completed", payload)
    if status == "failed":
        # Only the safe error string — never stack traces or internals.
        payload["error"] = job.get("error")
        return _format_sse("failed", payload)
    return None


async def _job_event_stream(job_id: str) -> AsyncIterator[str]:
    """Observe a job and yield SSE events as its state changes.

    This generator NEVER executes the research pipeline — it only reads the
    in-memory job store (under the job lock) and emits ``queued`` /
    ``progress`` / ``completed`` / ``failed`` events. The terminal check is
    performed on a fresh poll at the top of every loop, so a job that reaches
    ``completed``/``failed`` while an event is being sent is still reported
    before the stream terminates. A small sleep between polls avoids
    busy-spinning.
    """
    last_signature: tuple | None = None
    while True:
        with _lock:
            job = _jobs.get(job_id)
        if job is None:
            return

        # Terminal state: emit the final event once, then stop.
        if job["status"] in ("completed", "failed"):
            event = _sse_event_for(job)
            if event is not None:
                yield event
            return

        signature = (
            job["status"],
            job.get("current_step"),
            tuple(job.get("completed_steps") or []),
        )
        if signature != last_signature:
            last_signature = signature
            event = _sse_event_for(job)
            if event is not None:
                yield event
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)


@app.get("/research/{job_id}/stream")
async def research_stream(job_id: str) -> StreamingResponse:
    """Stream Server-Sent Events for a research job (404 if unknown).

    The stream only observes the existing job state — it never runs the
    research pipeline. The final ``completed``/``failed`` event signals the end
    of the stream; the full result is available via
    ``GET /research/{job_id}``.
    """
    _cleanup_expired_jobs()
    with _lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return StreamingResponse(
        _job_event_stream(job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
