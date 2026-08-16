"""Tests for GET /research/history (Phase 2F Step 6).

Covers: authenticated retrieval, newest-first ordering, owner isolation
(user A cannot see user B's jobs), 401 for unauthenticated callers, empty
history, and the guarantee that ``user_id`` is never exposed. The PostgreSQL
path is covered in ``test_jobs_postgres.py`` via the same SQLite-backed store
strategy used for the rest of the persistence suite.

Each test swaps in a fresh ``InMemoryJobStore`` so seeds never leak between
tests. The module-level client is authenticated as TEST_USER (same pattern as
``test_api.py``).
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import backend.app.api as api
from backend.app.auth.security import create_access_token
from backend.app.core.config import settings
from backend.app.repositories.jobs import InMemoryJobStore

TEST_USER_ID = uuid.uuid4()
OTHER_USER_ID = uuid.uuid4()

client = TestClient(api.app, raise_server_exceptions=False)
client.cookies.set(
    settings.auth_cookie_name,
    create_access_token(TEST_USER_ID),
)

anon_client = TestClient(api.app, raise_server_exceptions=False)

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _fresh_store(monkeypatch):
    store = InMemoryJobStore()
    monkeypatch.setattr(api, "store", store)
    return store


def _seed(
    store,
    job_id,
    query,
    *,
    user_id=TEST_USER_ID,
    created_at=None,
    status="completed",
    result=None,
    error=None,
):
    created_at = created_at or BASE
    store.create(
        job_id=job_id,
        query=query,
        user_id=user_id,
        status=status,
        result=result,
        error=error,
        created_at=created_at,
        updated_at=created_at,
    )


def _assert_no_user_id(payload):
    """``user_id`` must never leak anywhere in the history payload."""
    def walk(node):
        if isinstance(node, dict):
            assert "user_id" not in node, "user_id leaked into response"
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)


# ── Authenticated retrieval ─────────────────────────────────────────────────


def test_history_returns_authenticated_users_jobs(monkeypatch):
    store = _fresh_store(monkeypatch)
    _seed(store, "job-1", "first query", result={"report": "r1"})
    _seed(store, "job-2", "second query", status="failed", error="boom")

    resp = client.get("/research/history")

    assert resp.status_code == 200
    payload = resp.json()
    assert set(payload) == {"jobs"}
    by_id = {job["job_id"]: job for job in payload["jobs"]}
    assert set(by_id) == {"job-1", "job-2"}
    assert by_id["job-1"]["query"] == "first query"
    assert by_id["job-1"]["status"] == "completed"
    assert by_id["job-1"]["result"] == {"report": "r1"}
    assert by_id["job-2"]["status"] == "failed"
    assert by_id["job-2"]["error"] == "boom"
    assert "created_at" in by_id["job-1"]
    assert "updated_at" in by_id["job-1"]
    _assert_no_user_id(payload)


def test_history_orders_newest_first(monkeypatch):
    store = _fresh_store(monkeypatch)
    _seed(store, "job-old", "oldest", created_at=BASE)
    _seed(store, "job-new", "newest", created_at=BASE + timedelta(seconds=30))
    _seed(store, "job-mid", "middle", created_at=BASE + timedelta(seconds=15))

    resp = client.get("/research/history")

    assert resp.status_code == 200
    assert [job["job_id"] for job in resp.json()["jobs"]] == [
        "job-new",
        "job-mid",
        "job-old",
    ]


# ── Owner isolation ──────────────────────────────────────────────────────────


def test_history_hides_other_users_jobs(monkeypatch):
    store = _fresh_store(monkeypatch)
    _seed(store, "mine-1", "my query")
    _seed(store, "theirs-1", "their query", user_id=OTHER_USER_ID)
    _seed(store, "theirs-2", "their other query", user_id=OTHER_USER_ID)

    resp = client.get("/research/history")

    assert resp.status_code == 200
    assert [job["job_id"] for job in resp.json()["jobs"]] == ["mine-1"]


# ── Authentication ──────────────────────────────────────────────────────────


def test_history_requires_authentication():
    resp = anon_client.get("/research/history")

    assert resp.status_code == 401


# ── Empty history ───────────────────────────────────────────────────────────


def test_history_empty_for_user_with_no_jobs(monkeypatch):
    _fresh_store(monkeypatch)

    resp = client.get("/research/history")

    assert resp.status_code == 200
    assert resp.json() == {"jobs": []}
