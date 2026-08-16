"""Focused tests for the InMemoryJobStore repository (Phase 2F Steps 2 & 4).

These cover the operations the API layer relies on (create/get/update/delete,
lifecycle transitions, TTL cleanup, concurrency, and owner-scoped lookups) so
the in-memory store — and, later, any PostgreSQL implementation behind the
same ``JobStore`` interface — is verified independently of the HTTP layer.
"""
import threading
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.repositories.jobs import InMemoryJobStore, JobRecord

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
USER_A = uuid.uuid4()
USER_B = uuid.uuid4()
REPRESENTATIVE_RESULT = {"query": "q", "report": "Final report", "errors": []}


def make_clock(start=T0):
    """Return a mutable clock list usable as ``now_fn`` for the store."""
    return [start]


def make_store(clock=None):
    now_fn = (lambda: clock[0]) if clock is not None else None
    return InMemoryJobStore(now_fn=now_fn)


# ── Creation / retrieval ─────────────────────────────────────────────────────


def test_create_and_get_preserves_id_and_query():
    store = make_store()
    created = store.create(job_id="job-1", query="mediterranean diet")

    assert isinstance(created, JobRecord)
    assert created.job_id == "job-1"
    assert created.query == "mediterranean diet"
    assert created.status == "queued"
    assert created.current_step is None
    assert created.completed_steps == []
    assert created.result is None
    assert created.error is None

    fetched = store.get("job-1")
    assert fetched is not None
    assert fetched.job_id == "job-1"
    assert fetched.query == "mediterranean diet"


def test_get_missing_job_returns_none():
    store = make_store()
    assert store.get("missing") is None


def test_create_sets_timestamps_from_clock():
    clock = make_clock()
    store = make_store(clock)
    created = store.create(job_id="job-1", query="q")

    assert created.created_at == T0
    assert created.updated_at == T0
    assert created.created_at.tzinfo is not None  # timezone-aware


def test_create_rejects_invalid_status():
    store = make_store()
    with pytest.raises(ValueError, match="invalid job status"):
        store.create(job_id="job-1", query="q", status="bogus")


# ── Lifecycle transitions ────────────────────────────────────────────────────


def test_mark_running_resets_progress_and_updates_timestamp():
    clock = make_clock()
    store = make_store(clock)
    store.create(job_id="job-1", query="q", status="queued")
    clock[0] += timedelta(seconds=1)

    running = store.mark_running("job-1")

    assert running is not None
    assert running.status == "running"
    assert running.current_step is None
    assert running.completed_steps == []
    assert running.updated_at == T0 + timedelta(seconds=1)


def test_append_step_records_current_and_completed():
    store = make_store()
    store.create(job_id="job-1", query="q")
    store.mark_running("job-1")

    store.append_step("job-1", "plan")
    store.append_step("job-1", "research")

    job = store.get("job-1")
    assert job.current_step == "research"
    assert job.completed_steps == ["plan", "research"]


def test_mark_completed_stores_result():
    store = make_store()
    store.create(job_id="job-1", query="q")
    store.mark_running("job-1")

    completed = store.mark_completed("job-1", dict(REPRESENTATIVE_RESULT))

    assert completed.status == "completed"
    assert completed.result == REPRESENTATIVE_RESULT
    assert store.get("job-1").status == "completed"


def test_mark_failed_stores_error():
    store = make_store()
    store.create(job_id="job-1", query="q")
    store.mark_running("job-1")

    failed = store.mark_failed("job-1", "RuntimeError: boom")

    assert failed.status == "failed"
    assert failed.error == "RuntimeError: boom"
    assert store.get("job-1").status == "failed"


def test_transitions_on_missing_job_return_none():
    store = make_store()
    assert store.mark_running("missing") is None
    assert store.append_step("missing", "plan") is None
    assert store.mark_completed("missing", {}) is None
    assert store.mark_failed("missing", "e") is None


# ── Generic update / deletion ────────────────────────────────────────────────


def test_update_applies_fields():
    store = make_store()
    store.create(job_id="job-1", query="q")

    updated = store.update(
        job_id="job-1",
        status="running",
        current_step="plan",
        completed_steps=["plan"],
    )

    assert updated.status == "running"
    assert updated.current_step == "plan"
    assert updated.completed_steps == ["plan"]


def test_update_rejects_unknown_field():
    store = make_store()
    store.create(job_id="job-1", query="q")

    with pytest.raises(ValueError, match="unknown job fields"):
        store.update(job_id="job-1", bogus=1)


def test_update_missing_job_returns_none():
    store = make_store()
    assert store.update("missing", status="running") is None


def test_delete_existing_job():
    store = make_store()
    store.create(job_id="job-1", query="q")

    assert store.delete("job-1") is True
    assert store.get("job-1") is None


def test_delete_missing_job_is_predictable():
    store = make_store()
    assert store.delete("missing") is False  # no error, just False


# ── Snapshots isolate progress state ─────────────────────────────────────────


def test_get_returns_independent_completed_steps_copy():
    store = make_store()
    store.create(job_id="job-1", query="q")
    store.mark_running("job-1")

    before = store.get("job-1")
    before.completed_steps.append("tampered")

    after = store.get("job-1")
    assert after.completed_steps == []  # snapshot mutation did not leak in


# ── Owner-scoped access (Phase 2F Step 4) ───────────────────────────────────


def test_create_owned_job_and_get_by_owner():
    store = make_store()
    created = store.create(job_id="job-a", query="q", user_id=USER_A)

    assert created.user_id == USER_A
    assert store.get("job-a", user_id=USER_A) is not None
    assert store.get("job-a", user_id=USER_A).query == "q"


def test_get_owned_wrong_owner_is_none():
    store = make_store()
    store.create(job_id="job-a", query="q", user_id=USER_A)

    # Indistinguishable from a missing job.
    assert store.get("job-a", user_id=USER_B) is None


def test_get_owned_missing_job_is_none():
    store = make_store()
    assert store.get("missing", user_id=USER_A) is None


def test_get_unscoped_returns_any_job_for_compat():
    store = make_store()
    store.create(job_id="job-a", query="q", user_id=USER_A)
    assert store.get("job-a") is not None  # no user_id = unscoped (worker/tests)
    assert store.get("job-a").user_id == USER_A


def test_create_without_user_id_keeps_none_for_compat():
    store = make_store()
    record = store.create(job_id="job-x", query="q")
    assert record.user_id is None


def test_owned_snapshot_isolates_progress_state():
    store = make_store()
    store.create(job_id="job-a", query="q", user_id=USER_A)
    store.mark_running("job-a")

    snapshot = store.get("job-a", user_id=USER_A)
    snapshot.completed_steps.append("tampered")

    assert store.get("job-a", user_id=USER_A).completed_steps == []


def test_update_owner_scoped():
    store = make_store()
    store.create(job_id="job-a", query="q", user_id=USER_A)

    updated = store.update("job-a", user_id=USER_A, status="running")
    assert updated.status == "running"
    # Wrong owner: treated as missing.
    assert store.update("job-a", user_id=USER_B, status="completed") is None
    assert store.get("job-a").status == "running"  # unchanged


def test_update_preserves_owner():
    store = make_store()
    store.create(job_id="job-a", query="q", user_id=USER_A)

    store.update("job-a", user_id=USER_A, status="running")

    # ``user_id`` is the owner-scope argument, never an updatable field:
    # ownership is immutable after creation.
    assert store.get("job-a").user_id == USER_A


def test_delete_owner_scoped():
    store = make_store()
    store.create(job_id="job-a", query="q", user_id=USER_A)

    assert store.delete("job-a", user_id=USER_B) is False  # wrong owner: no-op
    assert store.get("job-a") is not None
    assert store.delete("job-a", user_id=USER_A) is True
    assert store.get("job-a") is None


def test_delete_owner_scoped_missing_job_is_false():
    store = make_store()
    assert store.delete("missing", user_id=USER_A) is False


def test_lifecycle_transitions_preserve_owner():
    store = make_store()
    store.create(job_id="job-a", query="q", user_id=USER_A)
    store.mark_running("job-a")
    store.append_step("job-a", "plan")
    store.mark_completed("job-a", dict(REPRESENTATIVE_RESULT))

    final = store.get("job-a", user_id=USER_A)
    assert final.user_id == USER_A
    assert final.status == "completed"
    assert final.result == REPRESENTATIVE_RESULT


# ── Owner-scoped history / listing (Phase 2F Step 6) ────────────────────────


def test_list_by_user_returns_only_owned_jobs():
    store = make_store()
    store.create(job_id="job-a1", query="a1", user_id=USER_A)
    store.create(job_id="job-a2", query="a2", user_id=USER_A)
    store.create(job_id="job-b1", query="b1", user_id=USER_B)
    store.create(job_id="job-x", query="x")  # no owner

    for_a = store.list_by_user(USER_A)
    for_b = store.list_by_user(USER_B)

    assert sorted(j.job_id for j in for_a) == ["job-a1", "job-a2"]
    assert [j.job_id for j in for_b] == ["job-b1"]


def test_list_by_user_orders_newest_first():
    clock = make_clock()
    store = make_store(clock)
    store.create(job_id="oldest", query="oldest", user_id=USER_A)
    clock[0] += timedelta(seconds=10)
    store.create(job_id="middle", query="middle", user_id=USER_A)
    clock[0] += timedelta(seconds=10)
    store.create(job_id="newest", query="newest", user_id=USER_A)

    assert [j.job_id for j in store.list_by_user(USER_A)] == [
        "newest",
        "middle",
        "oldest",
    ]


def test_list_by_user_empty():
    store = make_store()
    assert store.list_by_user(USER_A) == []


# ── TTL cleanup ──────────────────────────────────────────────────────────────


def test_cleanup_removes_expired_terminal_jobs():
    clock = make_clock()
    store = make_store(clock)
    store.create(job_id="old-completed", query="q", status="completed")
    store.create(job_id="old-failed", query="q", status="failed", error="e")
    clock[0] += timedelta(seconds=7200)  # 2h > 3600s TTL

    removed = store.cleanup_expired(3600, now=clock[0])

    assert removed == 2
    assert store.get("old-completed") is None
    assert store.get("old-failed") is None


def test_cleanup_keeps_fresh_terminal_jobs():
    clock = make_clock()
    store = make_store(clock)
    store.create(job_id="fresh-completed", query="q", status="completed")
    store.create(job_id="fresh-failed", query="q", status="failed", error="e")
    clock[0] += timedelta(seconds=10)  # 10s < TTL

    removed = store.cleanup_expired(3600, now=clock[0])

    assert removed == 0
    assert store.get("fresh-completed") is not None
    assert store.get("fresh-failed") is not None


def test_cleanup_never_removes_queued_or_running():
    clock = make_clock()
    store = make_store(clock)
    store.create(job_id="old-queued", query="q", status="queued")
    store.create(job_id="old-running", query="q", status="running")
    clock[0] += timedelta(seconds=7200)

    removed = store.cleanup_expired(3600, now=clock[0])

    assert removed == 0
    assert store.get("old-queued") is not None
    assert store.get("old-running") is not None


def test_cleanup_uses_store_clock_when_now_omitted():
    clock = make_clock()
    store = make_store(clock)
    store.create(job_id="old", query="q", status="completed")
    clock[0] += timedelta(seconds=7200)

    removed = store.cleanup_expired(3600)

    assert removed == 1
    assert store.get("old") is None


# ── Concurrency ──────────────────────────────────────────────────────────────


def test_concurrent_transitions_are_safe():
    store = make_store()
    for i in range(20):
        store.create(job_id=f"job-{i}", query="q")

    errors = []

    def worker(seed):
        try:
            for i in range(50):
                job_id = f"job-{(seed + i) % 20}"
                store.mark_running(job_id)
                store.append_step(job_id, "plan")
                store.append_step(job_id, "research")
                store.mark_completed(job_id, {"report": "r"})
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    for i in range(20):
        job = store.get(f"job-{i}")
        assert job is not None
        assert job.status == "completed"
        # Never interleaved mid-write: progress and terminal state are coherent.
        assert job.completed_steps in ([], ["plan"], ["plan", "research"])
