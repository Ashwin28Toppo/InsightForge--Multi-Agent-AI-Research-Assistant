"""Password hashing (Argon2id) and JWT access-token helpers.

Pure functions — no HTTP, no database. All authentication failures funnel into
a single internal ``AuthenticationError`` so the API layer can respond with one
consistent 401 without leaking which part of the check failed.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Warn once at import time when the JWT secret is the known dev placeholder.
if not settings.auth_jwt_secret or settings.auth_jwt_secret.startswith(
    "change-me-in-development"
):
    logger.warning(
        "AUTH_JWT_SECRET is unset or using the development placeholder; "
        "set a strong random secret before deploying to production."
    )

# Argon2id hasher with the argon2-cffi defaults (argon2id, 64 MB, 3 passes).
_hasher = PasswordHasher()

# Password bounds (deliberately non-restrictive per project requirements).
MIN_PASSWORD_LENGTH = 1
MAX_PASSWORD_LENGTH = 128


class AuthenticationError(Exception):
    """Raised on any invalid/expired/malformed authentication input."""


# ── Passwords ────────────────────────────────────────────────────────────────


def validate_password(password: str) -> str:
    """Validate and return a password (raises ``ValueError`` when invalid).

    Rules are intentionally minimal: non-empty and a sensible maximum length
    to prevent abuse. No character-class requirements.
    """
    if not isinstance(password, str):
        raise ValueError("password must be a string")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError("password must not be empty")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError("password must be at most 128 characters")
    return password


def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2id. Never reversible."""
    validate_password(password)
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against an Argon2id hash.

    Any verification failure (wrong password, malformed hash) returns ``False``
    — it never raises and never leaks details.
    """
    if not isinstance(password, str) or not isinstance(password_hash, str):
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# ── JWT ──────────────────────────────────────────────────────────────────────


def _secret() -> str:
    secret = settings.auth_jwt_secret
    if not secret:
        # Never silently fall back to a hardcoded secret.
        raise RuntimeError("AUTH_JWT_SECRET is not configured")
    return secret


def create_access_token(user_id: UUID) -> str:
    """Create a signed JWT access token for a user.

    Claims: ``sub`` (user UUID string), ``iat``, ``exp`` (configured lifetime).
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.auth_jwt_expire_minutes),
    }
    return jwt.encode(payload, _secret(), algorithm=settings.auth_jwt_algorithm)


def decode_access_token(token: str) -> UUID:
    """Verify and decode a JWT, returning the user UUID from ``sub``.

    Rejects malformed tokens, invalid signatures, expired tokens, missing
    ``sub``, and non-UUID ``sub`` values — all surfaced as a single
    ``AuthenticationError`` (no internal JWT exceptions leak out).
    """
    try:
        payload = jwt.decode(
            token,
            _secret(),
            algorithms=[settings.auth_jwt_algorithm],
            options={"require": ["sub"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("invalid token") from exc

    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise AuthenticationError("token missing sub")
    try:
        return UUID(sub)
    except (ValueError, AttributeError) as exc:
        raise AuthenticationError("invalid sub") from exc
