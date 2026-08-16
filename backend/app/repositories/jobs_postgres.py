"""PostgreSQL-backed ``JobStore`` (Phase 2F Step 5).

Implements the same ``JobStore`` interface as ``InMemoryJobStore`` using the
async SQLAlchemy session infrastructure (Step 2) and the ``ResearchJob`` ORM
model. Every job operation is persisted through the database, so jobs survive
backend restarts and are shared across workers that use the same database.

Interface note: ``JobStore`` is a synchronous interface (matching
``InMemoryJobStore`` and the API layer's synchronous endpoints/worker thread).
Database operations are async, so each call is bridged onto a dedicated event
loop (``_SyncBridge``) via ``asyncio.run_coroutine_threadsafe``. This is safe
both from synchronous contexts (FastAPI ``def`` endpoints, the background
worker thread) and from the async SSE generator, which runs on the server's
event loop — where ``asyncio.run`` would raise (nested loop).
"""
from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.core.config import settings
from backend.app.db.models import ResearchJob
from backend.app.db.session import get_sessionmaker
from backend.app.repositories.jobs import JobRecord, JobStore

# Mapping from the JobStore field names (update() kwargs) to ResearchJob
# columns. ``user_id`` is intentionally absent — ownership is immutable after
# creation (it is the owner-scope argument, never an updatable field).
_UPDATEABLE_COLUMNS: dict[str, str] = {
    "status": "status",
    "result": "result",
    "error": "error",
    "current_step": "current_step",
    "completed_steps": "completed_steps",
    "created_at": "created_at",
    "updated_at": "updated_at",
}


def _utcnow() -> datetime:
    """Timezone-aware current UTC time (default clock for the store)."""
    return datetime.now(timezone.utc)


class _SyncBridge:
    """Run async coroutines on a dedicated background event loop.

    Keeps the ``JobStore`` interface synchronous while the database layer is
    async. A single daemon thread owns the loop; ``call()`` schedules a
    coroutine on it and blocks until it completes. Because this is a separate
    loop, it never conflicts with an already-running event loop (e.g. the SSE
    generator on the server loop).
    """

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run,
            name="insightforge-db-bridge",
            daemon=True,
        )
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def call(self, coro) -> Any:
        """Run ``coro`` on the bridge loop and block for its result."""
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def close(self) -> None:
        """Stop the bridge loop (best-effort; daemon thread)."""
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)


class PostgresJobStore(JobStore):
    """``JobStore`` persisted through the async SQLAlchemy session.

    Each operation opens its own session from the injected session factory
    (defaults to the application's ``get_sessionmaker()``) and commits
    atomically, mirroring the exact semantics of ``InMemoryJobStore``:
    owner-scoped get/update/delete, lifecycle transitions, and TTL cleanup.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        if session_factory is not None:
            self._sessionmaker = session_factory
        elif settings.database_url:
            # Dedicated engine for the store. All store DB work runs on the
            # ``_SyncBridge`` background loop, and asyncpg connections are
            # bound to the loop that created them — so this pool must NEVER
            # be shared with the server event loop (the ``/auth/*`` endpoints
            # use ``get_sessionmaker()`` on the server loop). Sharing one
            # pool across the two loops raises "Future attached to a different
            # loop" on real PostgreSQL. Real PG validation (Phase 2F Step 8)
            # caught exactly that; a separate pool fixes it.
            self._engine = create_async_engine(
                settings.database_url,
                pool_pre_ping=True,
            )
            self._sessionmaker = async_sessionmaker(
                self._engine,
                expire_on_commit=False,
            )
        else:
            # No DATABASE_URL: defer to the shared sessionmaker, which raises
            # a clear error on first use.
            self._sessionmaker = get_sessionmaker()
        self._bridge = _SyncBridge()

    def _new_session(self):
        """Open a fresh session from the injected session factory."""
        return self._sessionmaker()

    # ── mapping helpers ────────────────────────────────────────────────────

    @staticmethod
    def _to_uuid(job_id: str) -> UUID:
        return UUID(job_id)

    @staticmethod
    def _record(row: ResearchJob) -> JobRecord:
        return JobRecord(
            job_id=str(row.id),
            query=row.query,
            user_id=row.user_id,
            status=row.status,
            result=row.result,
            error=row.error,
            current_step=row.current_step,
            completed_steps=list(row.completed_steps or []),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _now(now: datetime | None = None) -> datetime:
        return now if now is not None else _utcnow()

    # ── JobStore interface (sync facade over async internals) ─────────────

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
        return self._bridge.call(
            self._create(
                job_id=job_id,
                query=query,
                user_id=user_id,
                status=status,
                result=result,
                error=error,
                current_step=current_step,
                completed_steps=completed_steps,
                created_at=created_at,
                updated_at=updated_at,
            )
        )

    def get(self, job_id: str, user_id: UUID | None = None) -> JobRecord | None:
        return self._bridge.call(self._get(job_id, user_id=user_id))

    def update(
        self, job_id: str, user_id: UUID | None = None, **changes
    ) -> JobRecord | None:
        return self._bridge.call(self._update(job_id, user_id=user_id, changes=changes))

    def delete(self, job_id: str, user_id: UUID | None = None) -> bool:
        return self._bridge.call(self._delete(job_id, user_id=user_id))

    def list(self) -> list[JobRecord]:
        return self._bridge.call(self._list())

    def list_by_user(self, user_id: UUID) -> list[JobRecord]:
        return self._bridge.call(self._list_by_user(user_id))

    def cleanup_expired(
        self, ttl_seconds: int, now: datetime | None = None
    ) -> int:
        return self._bridge.call(self._cleanup_expired(ttl_seconds, now=now))

    def mark_running(self, job_id: str) -> JobRecord | None:
        return self._bridge.call(self._mark_running(job_id))

    def append_step(self, job_id: str, step: str) -> JobRecord | None:
        return self._bridge.call(self._append_step(job_id, step))

    def mark_completed(self, job_id: str, result: dict) -> JobRecord | None:
        return self._bridge.call(self._mark_completed(job_id, result))

    def mark_failed(self, job_id: str, error: str) -> JobRecord | None:
        return self._bridge.call(self._mark_failed(job_id, error))

    # ── async internals ────────────────────────────────────────────────────

    async def _create(
        self,
        *,
        job_id: str,
        query: str,
        user_id: UUID | None,
        status: str,
        result: dict | None,
        error: str | None,
        current_step: str | None,
        completed_steps: list[str] | None,
        created_at: datetime | None,
        updated_at: datetime | None,
    ) -> JobRecord:
        now = self._now(created_at)
        row = ResearchJob(
            id=self._to_uuid(job_id),
            query=query,
            user_id=user_id,
            status=status,
            result=result,
            error=error,
            current_step=current_step,
            completed_steps=list(completed_steps or []),
            created_at=now,
            updated_at=updated_at or now,
        )
        async with self._new_session() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return self._record(row)

    def _scoped_stmt(self, job_id: str, user_id: UUID | None = None):
        stmt = select(ResearchJob).where(ResearchJob.id == self._to_uuid(job_id))
        if user_id is not None:
            stmt = stmt.where(ResearchJob.user_id == user_id)
        return stmt

    async def _get(
        self, job_id: str, user_id: UUID | None = None
    ) -> JobRecord | None:
        async with self._new_session() as session:
            row = (
                await session.execute(self._scoped_stmt(job_id, user_id))
            ).scalar_one_or_none()
        return self._record(row) if row is not None else None

    async def _update(
        self, job_id: str, user_id: UUID | None = None, changes: dict | None = None
    ) -> JobRecord | None:
        changes = changes or {}
        unknown = set(changes) - set(_UPDATEABLE_COLUMNS)
        if unknown:
            raise ValueError(f"unknown job fields: {sorted(unknown)}")
        async with self._new_session() as session:
            row = (
                await session.execute(self._scoped_stmt(job_id, user_id))
            ).scalar_one_or_none()
            if row is None:
                return None
            for field, value in changes.items():
                setattr(row, _UPDATEABLE_COLUMNS[field], value)
            await session.commit()
            await session.refresh(row)
        return self._record(row)

    async def _delete(self, job_id: str, user_id: UUID | None = None) -> bool:
        stmt = delete(ResearchJob).where(ResearchJob.id == self._to_uuid(job_id))
        if user_id is not None:
            stmt = stmt.where(ResearchJob.user_id == user_id)
        async with self._new_session() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def _list(self) -> list[JobRecord]:
        async with self._new_session() as session:
            rows = (await session.execute(select(ResearchJob))).scalars().all()
        return [self._record(row) for row in rows]

    async def _list_by_user(self, user_id: UUID) -> list[JobRecord]:
        stmt = (
            select(ResearchJob)
            .where(ResearchJob.user_id == user_id)
            .order_by(ResearchJob.created_at.desc())
        )
        async with self._new_session() as session:
            rows = (await session.execute(stmt)).scalars().all()
        return [self._record(row) for row in rows]

    async def _cleanup_expired(
        self, ttl_seconds: int, now: datetime | None = None
    ) -> int:
        cutoff = self._now(now) - timedelta(seconds=ttl_seconds)
        stmt = delete(ResearchJob).where(
            ResearchJob.status.in_(("completed", "failed")),
            ResearchJob.updated_at < cutoff,
        )
        async with self._new_session() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount

    async def _mark_running(self, job_id: str) -> JobRecord | None:
        async with self._new_session() as session:
            row = (
                await session.execute(
                    select(ResearchJob).where(ResearchJob.id == self._to_uuid(job_id))
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            row.status = "running"
            row.current_step = None
            row.completed_steps = []
            row.updated_at = self._now()
            await session.commit()
            await session.refresh(row)
        return self._record(row)

    async def _append_step(self, job_id: str, step: str) -> JobRecord | None:
        async with self._new_session() as session:
            row = (
                await session.execute(
                    select(ResearchJob).where(ResearchJob.id == self._to_uuid(job_id))
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            row.current_step = step
            row.completed_steps = list(row.completed_steps or []) + [step]
            row.updated_at = self._now()
            await session.commit()
            await session.refresh(row)
        return self._record(row)

    async def _mark_completed(self, job_id: str, result: dict) -> JobRecord | None:
        async with self._new_session() as session:
            row = (
                await session.execute(
                    select(ResearchJob).where(ResearchJob.id == self._to_uuid(job_id))
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            row.status = "completed"
            row.result = result
            row.updated_at = self._now()
            await session.commit()
            await session.refresh(row)
        return self._record(row)

    async def _mark_failed(self, job_id: str, error: str) -> JobRecord | None:
        async with self._new_session() as session:
            row = (
                await session.execute(
                    select(ResearchJob).where(ResearchJob.id == self._to_uuid(job_id))
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            row.status = "failed"
            row.error = error
            row.updated_at = self._now()
            await session.commit()
            await session.refresh(row)
        return self._record(row)
