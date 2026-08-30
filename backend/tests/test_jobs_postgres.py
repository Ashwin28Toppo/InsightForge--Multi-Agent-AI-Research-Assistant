"""Tests for the PostgreSQL-backed JobStore (Phase 2F Step 5).

``PostgresJobStore`` talks to any SQLAlchemy async database. With no local
PostgreSQL instance available, these tests exercise it against an isolated,
file-backed SQLite database whose ``users``/``research_jobs`` tables are created
from metadata copies with PostgreSQL-specific ``server_default`` casts removed
(SQLite has no ``now()``/``'[]'::jsonb`` defaults) and ``JSONB`` compiled to
``JSON``. This verifies the store's persistence, ownership, and lifecycle
behavior; the identical suite runs against a real PostgreSQL once one is
available (documented limitation).
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import MetaData
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from backend.app.db.models import ResearchJob, User
from backend.app.repositories.jobs_postgres import PostgresJobStore


@compiles(JSONB, "sqlite")
def _compile_jsonb_as_json(type_, compiler, **kw):
    return "JSON"


USER_A = uuid.uuid4()
USER_B = uuid.uuid4()
JOB_1 = "11111111-1111-4111-8111-111111111111"


def _strip_pg_defaults(meta: MetaData) -> None:
    users = meta.tables["users"]
    jobs = meta.tables["research_jobs"]
    for col in (
        users.c.created_at,
        users.c.updated_at,
        jobs.c.status,
        jobs.c.completed_steps,
        jobs.c.created_at,
        jobs.c.updated_at,
    ):
        col.server_default = None


def _build_store(engine):
    return PostgresJobStore(
        session_factory=async_sessionmaker(engine, expire_on_commit=False)
    )


def _create_schema(engine) -> None:
    meta = MetaData()
    User.__table__.to_metadata(meta)
    ResearchJob.__table__.to_metadata(meta)
    _strip_pg_defaults(meta)

    async def setup() -> None:
        async with engine.begin() as conn:
            for table in (meta.tables["users"], meta.tables["research_jobs"]):
                await conn.run_sync(
                    lambda sc, t=table: t.create(sc, checkfirst=True)
                )

    asyncio.run(setup())


@pytest.fixture
def store(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'jobs.db'}"
    )
    _create_schema(engine)
    yield _build_store(engine)
    asyncio.run(engine.dispose())


# ── Create / get / ownership ─────────────────────────────────────────────────


def test_create_and_get_owned_job(store):
    record = store.create(JOB_1, "q", user_id=USER_A)

    got = store.get(record.job_id, user_id=USER_A)
    assert got is not None
    assert got.job_id == JOB_1
    assert got.query == "q"
    assert got.user_id == USER_A
    assert got.status == "queued"
    assert got.completed_steps == []


def test_get_wrong_owner_is_none(store):
    record = store.create(JOB_1, "q", user_id=USER_A)
    assert store.get(record.job_id, user_id=USER_B) is None


def test_get_missing_job_is_none(store):
    assert (
        store.get("00000000-0000-4000-8000-000000000000", user_id=USER_A) is None
    )


# ── Lifecycle transitions persist ────────────────────────────────────────────


def test_lifecycle_transitions_persist(store):
    record = store.create(JOB_1, "q", user_id=USER_A)
    store.mark_running(record.job_id)
    store.append_step(record.job_id, "plan")
    store.append_step(record.job_id, "research")
    store.mark_completed(record.job_id, {"report": "r", "errors": []})

    final = store.get(record.job_id, user_id=USER_A)
    assert final.status == "completed"
    assert final.current_step == "research"
    assert final.completed_steps == ["plan", "research"]
    assert final.result == {"report": "r", "errors": []}
    assert final.user_id == USER_A


def test_mark_failed_persists(store):
    record = store.create(JOB_1, "q", user_id=USER_A)
    store.mark_running(record.job_id)
    store.mark_failed(record.job_id, "RuntimeError: boom")

    final = store.get(record.job_id, user_id=USER_A)
    assert final.status == "failed"
    assert final.error == "RuntimeError: boom"


# ── Owner-scoped update / delete ─────────────────────────────────────────────


def test_update_is_owner_scoped(store):
    record = store.create(JOB_1, "q", user_id=USER_A)

    assert store.update(record.job_id, user_id=USER_A, status="running") is not None
    # Wrong owner: treated as missing, nothing changes.
    assert store.update(record.job_id, user_id=USER_B, status="completed") is None
    assert store.get(record.job_id, user_id=USER_A).status == "running"


def test_update_rejects_unknown_field(store):
    record = store.create(JOB_1, "q", user_id=USER_A)
    with pytest.raises(ValueError, match="unknown job fields"):
        store.update(record.job_id, user_id=USER_A, bogus=1)


def test_delete_is_owner_scoped(store):
    record = store.create(JOB_1, "q", user_id=USER_A)

    assert store.delete(record.job_id, user_id=USER_B) is False
    assert store.get(record.job_id) is not None
    assert store.delete(record.job_id, user_id=USER_A) is True
    assert store.get(record.job_id) is None


# ── TTL cleanup ──────────────────────────────────────────────────────────────


def test_cleanup_expired_only_removes_old_terminal(store):
    old_completed = store.create(JOB_1, "q", user_id=USER_A, status="completed")
    old_queued = store.create(
        "22222222-2222-4222-8222-222222222222", "q", user_id=USER_A, status="queued"
    )
    old_failed = store.create(
        "33333333-3333-4333-8333-333333333333",
        "q",
        user_id=USER_A,
        status="failed",
        error="e",
    )
    now = datetime.now(timezone.utc)
    for job_id in (old_completed.job_id, old_queued.job_id, old_failed.job_id):
        store.update(job_id, user_id=USER_A, updated_at=now - timedelta(hours=2))

    removed = store.cleanup_expired(3600, now=now)

    assert removed == 2
    assert store.get(old_completed.job_id, user_id=USER_A) is None
    assert store.get(old_failed.job_id, user_id=USER_A) is None
    assert store.get(old_queued.job_id, user_id=USER_A) is not None


# ── Persistence across restarts ──────────────────────────────────────────────


def test_persists_across_store_instances(store, tmp_path):
    """Data written through one store is visible through a brand-new engine +
    store on the same database file — the core of PostgreSQL persistence."""
    record = store.create(JOB_1, "q", user_id=USER_A)
    store.mark_completed(record.job_id, {"report": "r", "errors": []})

    engine2 = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'jobs.db'}"
    )
    store2 = _build_store(engine2)
    try:
        got = store2.get(record.job_id, user_id=USER_A)
        assert got is not None
        assert got.status == "completed"
        assert got.result == {"report": "r", "errors": []}
        assert got.user_id == USER_A
    finally:
        asyncio.run(engine2.dispose())


# ── Owner-scoped history (Phase 2F Step 6) ───────────────────────────────────


def test_list_by_user_returns_only_owned_jobs(store):
    store.create(JOB_1, "a1", user_id=USER_A)
    store.create("22222222-2222-4222-8222-222222222222", "a2", user_id=USER_A)
    store.create("33333333-3333-4333-8333-333333333333", "b1", user_id=USER_B)

    for_a = store.list_by_user(USER_A)
    for_b = store.list_by_user(USER_B)

    assert len(for_a) == 2
    assert all(j.user_id == USER_A for j in for_a)
    assert {j.job_id for j in for_b} == {"33333333-3333-4333-8333-333333333333"}


def test_list_by_user_orders_newest_first(store):
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store.create(JOB_1, "oldest", user_id=USER_A, created_at=base)
    store.create(
        "22222222-2222-4222-8222-222222222222",
        "newest",
        user_id=USER_A,
        created_at=base + timedelta(seconds=30),
    )
    store.create(
        "33333333-3333-4333-8333-333333333333",
        "middle",
        user_id=USER_A,
        created_at=base + timedelta(seconds=15),
    )

    assert [j.query for j in store.list_by_user(USER_A)] == [
        "newest",
        "middle",
        "oldest",
    ]


def test_list_by_user_empty(store):
    assert store.list_by_user(USER_A) == []
