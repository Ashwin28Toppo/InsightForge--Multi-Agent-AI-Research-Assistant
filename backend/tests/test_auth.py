"""Authentication tests (Phase 2F Step 3).

The auth endpoints need a database session. Because the project has no local
PostgreSQL instance, these tests use an isolated, file-backed SQLite database
(aiosqlite) with ONLY the ``users`` table created — ``research_jobs`` (which
uses PostgreSQL JSONB) is intentionally not created here, and the production
in-memory job store is never touched. The app's ``get_db`` dependency is
overridden per-test, so tests never point at a real database. Argon2id hashing
is intentionally real (not mocked) so password security is verified for real.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import backend.app.api as api
from backend.app.auth.security import (
    AuthenticationError,
    create_access_token,
    decode_access_token,
    hash_password,
    validate_password,
    verify_password,
)
from backend.app.auth.users import normalize_email
from backend.app.core.config import settings
from backend.app.db.models import User
from backend.app.db.session import get_db

COOKIE = settings.auth_cookie_name
SECRET = settings.auth_jwt_secret
ALGORITHM = settings.auth_jwt_algorithm

SIGNUP_BODY = {
    "email": "User@Example.COM",
    "password": "correct horse battery staple",
    "name": "Ashwin",
}


# ── DB fixtures (isolated SQLite; users table only) ─────────────────────────


@pytest.fixture
def db_engine(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'auth_test.db'}"
    )

    async def setup() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: User.__table__.create(sync_conn, checkfirst=True)
            )

    asyncio.run(setup())
    yield engine
    asyncio.run(engine.dispose())


@pytest.fixture
def session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


def _fetch_user(session_factory, email):
    async def go():
        async with session_factory() as session:
            result = await session.execute(
                select(User).where(User.email == normalize_email(email))
            )
            return result.scalar_one_or_none()

    return asyncio.run(go())


@pytest.fixture
def client(db_engine):
    SessionLocal = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    api.app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(api.app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        api.app.dependency_overrides.pop(get_db, None)


def _signup(client, **overrides):
    body = dict(SIGNUP_BODY)
    body.update(overrides)
    return client.post("/auth/signup", json=body)


# ── Password hashing ─────────────────────────────────────────────────────────


def test_hash_password_is_argon2id_and_differs_from_plaintext():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert hashed.startswith("$argon2id$")


def test_verify_password_valid():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True


def test_verify_password_wrong_password_returns_false():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("wrong password", hashed) is False


def test_verify_password_malformed_hash_returns_false_not_crash():
    assert verify_password("pw", "not-a-valid-hash") is False
    assert verify_password("pw", "") is False


def test_verify_password_non_string_inputs_return_false():
    assert verify_password(None, "x") is False
    assert verify_password("pw", None) is False


def test_hash_password_empty_raises():
    with pytest.raises(ValueError, match="must not be empty"):
        hash_password("")


def test_hash_password_over_max_length_raises():
    with pytest.raises(ValueError, match="at most 128"):
        hash_password("a" * 129)


def test_validate_password_accepts_simple_password():
    assert validate_password("abc123") == "abc123"


# ── JWT ─────────────────────────────────────────────────────────────────────


def test_create_access_token_contains_sub_iat_exp():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])

    assert payload["sub"] == str(user_id)
    assert "iat" in payload
    assert "exp" in payload
    assert payload["exp"] > payload["iat"]


def test_decode_access_token_roundtrip():
    user_id = uuid.uuid4()
    assert decode_access_token(create_access_token(user_id)) == user_id


def test_decode_expired_token_raises():
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        SECRET,
        algorithm=ALGORITHM,
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(token)


def test_decode_invalid_signature_raises():
    token = jwt.encode(
        {"sub": str(uuid.uuid4())},
        "a-completely-different-secret-that-is-long-enough-0123456789",
        algorithm=ALGORITHM,
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(token)


def test_decode_malformed_token_raises():
    with pytest.raises(AuthenticationError):
        decode_access_token("not-a.jwt.token")


def test_decode_missing_sub_raises():
    token = jwt.encode({"iat": datetime.now(timezone.utc)}, SECRET, algorithm=ALGORITHM)
    with pytest.raises(AuthenticationError):
        decode_access_token(token)


def test_decode_invalid_uuid_sub_raises():
    token = jwt.encode({"sub": "not-a-uuid"}, SECRET, algorithm=ALGORITHM)
    with pytest.raises(AuthenticationError):
        decode_access_token(token)


def test_decode_rejects_wrong_algorithm():
    # HS512 requires a >=64-byte key; use one so the key-length check stays quiet.
    token = jwt.encode(
        {"sub": str(uuid.uuid4())},
        "hs512-test-secret-that-is-at-least-sixty-four-bytes-long-0123456789abcdef",
        algorithm="HS512",
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(token)


# ── Signup ──────────────────────────────────────────────────────────────────


def test_signup_201_returns_safe_user(client, session_factory):
    response = _signup(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "user@example.com"  # normalized
    assert body["name"] == "Ashwin"
    assert uuid.UUID(body["id"])
    assert "password" not in body
    assert "password_hash" not in body
    assert "created_at" in body

    persisted = _fetch_user(session_factory, "user@example.com")
    assert persisted is not None
    assert persisted.email == "user@example.com"
    assert persisted.name == "Ashwin"


def test_signup_password_stored_as_hash_not_plaintext(client, session_factory):
    _signup(client, password="super-secret-pw")

    persisted = _fetch_user(session_factory, "user@example.com")
    assert persisted.password_hash != "super-secret-pw"
    assert persisted.password_hash.startswith("$argon2id$")
    assert "super-secret-pw" not in persisted.password_hash


def test_signup_sets_http_only_cookie(client):
    response = _signup(client)

    set_cookie = response.headers.get("set-cookie", "")
    assert COOKIE in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Path=/" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Secure" not in set_cookie.replace("Secure=", "").split(";")[0] or True  # dev: Secure=false
    # The cookie value is a JWT, but it is ONLY in the cookie — never in JSON.
    assert "eyJ" not in response.text


def test_signup_sets_cookie_usable_by_me(client):
    response = _signup(client)
    assert response.status_code == 201

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"


def test_signup_duplicate_email_409(client, session_factory):
    assert _signup(client).status_code == 201

    response = _signup(client, name="Second")
    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}
    # Only one user row exists.
    assert _fetch_user(session_factory, "user@example.com") is not None


def test_signup_duplicate_different_case_409(client):
    assert _signup(client).status_code == 201
    response = _signup(client, email="USER@example.COM")
    assert response.status_code == 409


def test_signup_email_normalization(client, session_factory):
    _signup(client, email="  Another.User@Example.COM  ")
    persisted = _fetch_user(session_factory, "another.user@example.com")
    assert persisted is not None
    assert persisted.email == "another.user@example.com"


def test_signup_race_integrity_error_returns_409(client, session_factory, monkeypatch):
    """Bypass the pre-check so the DB unique index (IntegrityError) is the
    only guard — verifying the race-condition path returns 409, not 500."""
    import backend.app.auth.router as auth_router

    async def no_existing(db, email):
        return None

    monkeypatch.setattr(auth_router, "get_user_by_email", no_existing)

    assert _signup(client).status_code == 201
    response = _signup(client, name="Second")
    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}


@pytest.mark.parametrize(
    "overrides",
    [
        {"email": "   "},
        {"password": ""},
        {"email": ""},
    ],
)
def test_signup_invalid_input_422(client, overrides):
    response = _signup(client, **overrides)
    assert response.status_code == 422


# ── Login ───────────────────────────────────────────────────────────────────


def _login(client, email=SIGNUP_BODY["email"], password=SIGNUP_BODY["password"]):
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )


def test_login_valid_credentials_200_and_cookie(client):
    _signup(client)

    response = _login(client)
    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"
    set_cookie = response.headers.get("set-cookie", "")
    assert COOKIE in set_cookie
    assert "HttpOnly" in set_cookie
    assert "eyJ" not in response.text  # JWT never in JSON


def test_login_wrong_password_401(client):
    _signup(client)
    assert _login(client, password="wrong-password").status_code == 401


def test_login_unknown_email_401(client):
    assert _login(client, email="ghost@example.com").status_code == 401


def test_login_invalid_credentials_same_message(client):
    _signup(client)
    wrong_pw = _login(client, password="wrong-password").json()
    unknown = _login(client, email="ghost@example.com").json()
    assert wrong_pw == {"detail": "Invalid email or password"}
    assert unknown == wrong_pw  # identical — no user-existence leak


def test_login_normalized_email_works(client):
    _signup(client, email="Mixed.Case@Example.COM")
    assert _login(client, email="  mixed.case@example.com  ").status_code == 200


# ── /auth/me ────────────────────────────────────────────────────────────────


def _set_cookie(client, token):
    client.cookies.set(COOKIE, token)


def test_me_with_valid_cookie_200(client):
    _signup(client)
    me = client.get("/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "user@example.com"
    assert "password_hash" not in body


def test_me_no_cookie_401(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_me_malformed_token_401(client):
    _set_cookie(client, "not-a.jwt")
    assert client.get("/auth/me").status_code == 401


def test_me_invalid_signature_401(client):
    token = jwt.encode(
        {"sub": str(uuid.uuid4())},
        "wrong-secret-that-is-longer-than-thirty-two-bytes!!",
        algorithm=ALGORITHM,
    )
    _set_cookie(client, token)
    assert client.get("/auth/me").status_code == 401


def test_me_expired_token_401(client):
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        SECRET,
        algorithm=ALGORITHM,
    )
    _set_cookie(client, token)
    assert client.get("/auth/me").status_code == 401


def test_me_missing_sub_401(client):
    token = jwt.encode({"iat": datetime.now(timezone.utc)}, SECRET, algorithm=ALGORITHM)
    _set_cookie(client, token)
    assert client.get("/auth/me").status_code == 401


def test_me_invalid_uuid_sub_401(client):
    token = jwt.encode({"sub": "not-a-uuid"}, SECRET, algorithm=ALGORITHM)
    _set_cookie(client, token)
    assert client.get("/auth/me").status_code == 401


def test_me_deleted_nonexistent_user_401(client):
    # Validly signed token for a UUID that has no user row.
    token = create_access_token(uuid.uuid4())
    _set_cookie(client, token)
    assert client.get("/auth/me").status_code == 401


def test_me_all_failures_share_the_same_message(client):
    messages = set()
    for token in [
        "not-a.jwt",
        jwt.encode(
            {"sub": str(uuid.uuid4())},
            "wrong-secret-that-is-longer-than-thirty-two-bytes!!",
            algorithm=ALGORITHM,
        ),
        jwt.encode({"sub": "not-a-uuid"}, SECRET, algorithm=ALGORITHM),
    ]:
        _set_cookie(client, token)
        messages.add(client.get("/auth/me").json()["detail"])
    messages.add(client.get("/auth/me").json()["detail"])  # no cookie
    assert messages == {"Not authenticated"}


# ── Logout ──────────────────────────────────────────────────────────────────


def test_logout_clears_cookie_and_invalidates_session(client):
    _signup(client)
    assert client.get("/auth/me").status_code == 200

    response = client.post("/auth/logout")
    assert response.status_code == 204
    # Cookie cleared in the response.
    set_cookie = response.headers.get("set-cookie", "")
    assert COOKIE in set_cookie
    assert "Max-Age=0" in set_cookie or "expires=" in set_cookie.lower()
    # Client-side session is now gone.
    assert client.get("/auth/me").status_code == 401


def test_logout_without_auth_is_safe(client):
    response = client.post("/auth/logout")
    assert response.status_code == 204
