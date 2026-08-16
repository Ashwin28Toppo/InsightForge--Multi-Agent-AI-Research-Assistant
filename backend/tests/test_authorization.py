"""Ownership & authorization tests (Phase 2F Step 4).

The research endpoints now require authentication and are owner-scoped. These
tests use two distinct authenticated identities (User A, User B) whose JWTs are
signed with the same server secret — the research endpoints resolve the owner
from the verified token via ``get_current_user_id`` (no database needed), so
this suite runs without any DB fixture. Ownership is always derived from the
JWT; a client-supplied ``user_id`` is rejected.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

import backend.app.api as api
from backend.app.auth.security import create_access_token
from backend.app.core.config import settings

COOKIE = settings.auth_cookie_name
USER_A = uuid.uuid4()
USER_B = uuid.uuid4()

client = TestClient(api.app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _reset_cookies():
    client.cookies.clear()
    yield
    client.cookies.clear()


def _as(user_id):
    client.cookies.set(COOKIE, create_access_token(user_id))


def _seed(user_id, status="queued"):
    job_id = str(uuid.uuid4())
    api.store.create(
        job_id=job_id,
        query="q",
        user_id=user_id,
        status=status,
        result={"report": "Final report", "errors": []} if status == "completed" else None,
    )
    return job_id


def _post_research(query="q", **extra):
    payload = {"query": query, **extra}
    return client.post("/research", json=payload)


# ── Authentication required (401) ────────────────────────────────────────────


def test_unauthenticated_post_research_401():
    response = _post_research()
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_unauthenticated_get_status_401():
    response = client.get("/research/some-job-id")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_unauthenticated_get_progress_401():
    response = client.get("/research/some-job-id/progress")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_unauthenticated_get_stream_401():
    response = client.get("/research/some-job-id/stream")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


# ── Ownership matrix ─────────────────────────────────────────────────────────


def test_owner_a_reads_job_a_200():
    job_a = _seed(USER_A, status="completed")
    _as(USER_A)
    response = client.get(f"/research/{job_a}")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_owner_b_reads_job_b_200():
    job_b = _seed(USER_B, status="completed")
    _as(USER_B)
    response = client.get(f"/research/{job_b}")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_a_cannot_read_job_b_404():
    job_b = _seed(USER_B, status="completed")
    _as(USER_A)
    response = client.get(f"/research/{job_b}")
    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}


def test_b_cannot_read_job_a_404():
    job_a = _seed(USER_A, status="completed")
    _as(USER_B)
    response = client.get(f"/research/{job_a}")
    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}


def test_a_cannot_read_b_progress_404():
    job_b = _seed(USER_B)
    _as(USER_A)
    response = client.get(f"/research/{job_b}/progress")
    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}


def test_b_cannot_read_a_progress_404():
    job_a = _seed(USER_A)
    _as(USER_B)
    response = client.get(f"/research/{job_a}/progress")
    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}


def test_a_cannot_stream_b_404():
    job_b = _seed(USER_B)
    _as(USER_A)
    response = client.get(f"/research/{job_b}/stream")
    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}


def test_b_cannot_stream_a_404():
    job_a = _seed(USER_A)
    _as(USER_B)
    response = client.get(f"/research/{job_a}/stream")
    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}


def test_owner_can_stream_own_job():
    job_a = _seed(USER_A, status="completed")
    _as(USER_A)
    with client.stream("GET", f"/research/{job_a}/stream") as response:
        assert response.status_code == 200
        lines = [line for line in response.iter_lines() if line]
    assert "event: completed" in lines
    assert "job_id" in "\n".join(lines)


# ── Ownership derived from authentication ────────────────────────────────────


def test_post_creates_job_owned_by_authenticated_user(monkeypatch):
    monkeypatch.setattr(api, "_run_job", lambda job_id, query: None)
    _as(USER_A)

    response = _post_research()
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    record = api.store.get(job_id)
    assert record is not None
    assert record.user_id == USER_A


def test_forged_user_id_in_body_is_rejected(monkeypatch):
    """A client-supplied ``user_id`` is rejected by the schema (extra=forbid),
    so ownership can never be influenced by the request body."""
    monkeypatch.setattr(api, "_run_job", lambda job_id, query: None)
    _as(USER_A)

    response = _post_research(user_id=str(USER_B))
    assert response.status_code == 422  # unknown field rejected
    assert response.json()["detail"][0]["loc"][-1] == "user_id"


def test_two_users_create_isolated_owned_jobs(monkeypatch):
    monkeypatch.setattr(api, "_run_job", lambda job_id, query: None)
    _as(USER_A)
    job_a = _post_research().json()["job_id"]
    _as(USER_B)
    job_b = _post_research().json()["job_id"]

    assert api.store.get(job_a).user_id == USER_A
    assert api.store.get(job_b).user_id == USER_B
    # Cross access still blocked after creation.
    assert client.get(f"/research/{job_a}").status_code == 404  # as B
    _as(USER_A)
    assert client.get(f"/research/{job_a}").status_code == 200


# ── Nonexistent job is indistinguishable from another user's job ─────────────


def test_authenticated_nonexistent_job_404():
    _as(USER_A)
    response = client.get(f"/research/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}


def test_nonexistent_progress_and_stream_404():
    _as(USER_A)
    job_id = str(uuid.uuid4())
    assert client.get(f"/research/{job_id}/progress").status_code == 404
    assert client.get(f"/research/{job_id}/stream").status_code == 404


def test_cross_user_and_nonexistent_return_identical_404():
    job_b = _seed(USER_B)
    _as(USER_A)
    cross_user = client.get(f"/research/{job_b}")
    nonexistent = client.get(f"/research/{uuid.uuid4()}")
    assert cross_user.status_code == 404
    assert nonexistent.status_code == 404
    assert cross_user.json() == nonexistent.json() == {"detail": "job not found"}
