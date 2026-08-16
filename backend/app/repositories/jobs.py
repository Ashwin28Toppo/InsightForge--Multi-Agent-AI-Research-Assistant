"""Job persistence abstraction and its in-memory implementation.

The API layer (``backend/app/api.py``) interacts only with the ``JobStore``
interface — it no longer touches a raw job dictionary. ``InMemoryJobStore``
reproduces the exact runtime behavior of the previous module-level ``_jobs``
dict (including its ``threading.Lock`` semantics and TTL cleanup) so nothing
about the running application changes. A PostgreSQL-backed store will be
introduced in a later phase by implementing the same interface.
"""
from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID

_JOB_STATUSES = ("queued", "running", "completed", "failed")

# Fields the generic ``update`` operation may modify. ``created_at`` is
# included so tests/seeding can backdate records; it is not otherwise touched.
_UPDATEABLE_FIELDS = (
    "status",
    "result",
    "error",
    "current_step",
    "completed_steps",
    "created_at",
    "updated_at",
)


def _utcnow() -> datetime:
    """Timezone-aware current UTC time (the default store clock)."""
    return datetime.now(timezone.utc)


@dataclass
class JobRecord:
    """A single research job in a normalized, typed form.

    This mirrors the former in-memory job dictionary exactly (same field set)
    so the API layer can be migrated without changing any behavior. The
    ``result`` dict is the opaque pipeline output and is treated as immutable
    once written.
    """

    job_id: str
    query: str
    user_id: UUID | None = None
    status: str = "queued"
    result: dict | None = None
    error: str | None = None
    current_step: str | None = None
    completed_steps: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def copy(self) -> "JobRecord":
        """Return a shallow copy with an independent ``completed_steps`` list.

        ``result`` is intentionally shared (it is never mutated in place), so
        copies stay cheap while callers cannot mutate progress state through a
        snapshot.
        """
        return JobRecord(
            job_id=self.job_id,
            query=self.query,
            user_id=self.user_id,
            status=self.status,
            result=self.result,
            error=self.error,
            current_step=self.current_step,
            completed_steps=list(self.completed_steps),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class JobStore(ABC):
    """Persistence abstraction for research jobs.

    Implementations must be safe for concurrent readers/writers (the API runs
    background worker threads and streaming readers against the same store).
    All operations are atomic; records are returned as snapshots.
    """

    @abstractmethod
    def create(
        self,
        job_id: str,
        query: str,
        *,
        user_id: UUID | None = None,
        status: str = "queued",
        result: dict | None = None,
        error: str | None = None,
        current_step: str | None = None,
        completed_steps: list[str] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> JobRecord:
        """Create and store a job, returning a snapshot of it."""

    @abstractmethod
    def get(
        self, job_id: str, user_id: UUID | None = None
    ) -> JobRecord | None:
        """Return a snapshot of the job, or ``None`` if it does not exist.

        When ``user_id`` is provided the lookup is owner-scoped: a job owned
        by a different user is indistinguishable from a missing job.
        """

    @abstractmethod
    def update(
        self, job_id: str, user_id: UUID | None = None, **changes
    ) -> JobRecord | None:
        """Apply field updates atomically; returns the updated snapshot.

        When ``user_id`` is provided the update is owner-scoped (a different
        owner is treated as a missing job). Only known fields are accepted
        (``ValueError`` otherwise); ``updated_at`` only changes when passed.
        ``user_id`` itself is not updatable — ownership is immutable after
        creation.
        """

    @abstractmethod
    def delete(self, job_id: str, user_id: UUID | None = None) -> bool:
        """Delete a job; owner-scoped when ``user_id`` is provided.

        Returns ``True`` if it existed (and the owner matched), ``False``
        otherwise.
        """

    @abstractmethod
    def list(self) -> list[JobRecord]:
        """Return snapshots of all jobs (iteration for cleanup/scanning)."""

    @abstractmethod
    def cleanup_expired(self, ttl_seconds: int, now: datetime | None = None) -> int:
        """Remove terminal jobs older than ``ttl_seconds``; return count removed.

        ``queued`` and ``running`` jobs are never removed.
        """

    # ── Lifecycle transitions used by the background worker ────────────────
    # Each returns ``None`` when the job no longer exists (mirrors the former
    # ``if job is not None`` guards) so callers can safely no-op.

    @abstractmethod
    def mark_running(self, job_id: str) -> JobRecord | None:
        """queued -> running; resets progress fields."""

    @abstractmethod
    def append_step(self, job_id: str, step: str) -> JobRecord | None:
        """Record one completed stage (updates ``current_step`` + ``completed_steps``)."""

    @abstractmethod
    def mark_completed(self, job_id: str, result: dict) -> JobRecord | None:
        """running -> completed with the final result."""

    @abstractmethod
    def mark_failed(self, job_id: str, error: str) -> JobRecord | None:
        """running -> failed with a safe error string."""


class InMemoryJobStore(JobStore):
    """Thread-safe in-memory ``JobStore`` (dictionary + lock).

    Reproduces the exact behavior of the former module-level ``_jobs`` dict:
    same field set, same locking semantics, same TTL cleanup rules. The clock
    is injectable (``now_fn``) for deterministic tests.
    """

    def __init__(self, now_fn: Callable[[], datetime] | None = None) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.Lock()
        self.now_fn: Callable[[], datetime] = now_fn or _utcnow

    # ── internals ──────────────────────────────────────────────────────────

    def _now(self, now: datetime | None = None) -> datetime:
        return now if now is not None else self.now_fn()

    def _snapshot(self, record: JobRecord) -> JobRecord:
        return record.copy()

    # ── JobStore interface ─────────────────────────────────────────────────

    def create(
        self,
        job_id: str,
        query: str,
        *,
        user_id: UUID | None = None,
        status: str = "queued",
        result: dict | None = None,
        error: str | None = None,
        current_step: str | None = None,
        completed_steps: list[str] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> JobRecord:
        if status not in _JOB_STATUSES:
            raise ValueError(f"invalid job status: {status!r}")
        ts = self._now(created_at)
        record = JobRecord(
            job_id=job_id,
            query=query,
            user_id=user_id,
            status=status,
            result=result,
            error=error,
            current_step=current_step,
            completed_steps=list(completed_steps or []),
            created_at=ts,
            updated_at=ts if updated_at is None else updated_at,
        )
        with self._lock:
            self._jobs[job_id] = record
        return self._snapshot(record)

    def get(self, job_id: str, user_id: UUID | None = None) -> JobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            if user_id is not None and record.user_id != user_id:
                return None
            return self._snapshot(record)

    def update(
        self, job_id: str, user_id: UUID | None = None, **changes
    ) -> JobRecord | None:
        unknown = set(changes) - set(_UPDATEABLE_FIELDS)
        if unknown:
            raise ValueError(f"unknown job fields: {sorted(unknown)}")
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            if user_id is not None and record.user_id != user_id:
                return None
            for field_name, value in changes.items():
                setattr(record, field_name, value)
            return self._snapshot(record)

    def delete(self, job_id: str, user_id: UUID | None = None) -> bool:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return False
            if user_id is not None and record.user_id != user_id:
                return False
            del self._jobs[job_id]
            return True

    def list(self) -> list[JobRecord]:
        with self._lock:
            return [self._snapshot(r) for r in self._jobs.values()]

    def cleanup_expired(
        self, ttl_seconds: int, now: datetime | None = None
    ) -> int:
        ts = self._now(now)
        removed = 0
        with self._lock:
            expired = [
                job_id
                for job_id, record in self._jobs.items()
                if record.status in ("completed", "failed")
                and record.updated_at is not None
                and (ts - record.updated_at).total_seconds() > ttl_seconds
            ]
            for job_id in expired:
                del self._jobs[job_id]
                removed += 1
        return removed

    # ── lifecycle transitions ──────────────────────────────────────────────

    def mark_running(self, job_id: str) -> JobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            record.status = "running"
            record.current_step = None
            record.completed_steps = []
            record.updated_at = self._now()
            return self._snapshot(record)

    def append_step(self, job_id: str, step: str) -> JobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            record.current_step = step
            record.completed_steps = list(record.completed_steps) + [step]
            record.updated_at = self._now()
            return self._snapshot(record)

    def mark_completed(self, job_id: str, result: dict) -> JobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            record.status = "completed"
            record.result = result
            record.updated_at = self._now()
            return self._snapshot(record)

    def mark_failed(self, job_id: str, error: str) -> JobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            record.status = "failed"
            record.error = error
            record.updated_at = self._now()
            return self._snapshot(record)
