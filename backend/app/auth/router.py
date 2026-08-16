"""Authentication endpoints (Phase 2F Step 3).

``POST /auth/signup``, ``POST /auth/login``, ``POST /auth/logout`` and
``GET /auth/me``. The JWT is transported EXCLUSIVELY through an HttpOnly cookie
— it is never returned in a JSON body, and password hashes are never returned.
The research API remains public; ownership enforcement is a later step.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import get_current_user
from backend.app.auth.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from backend.app.auth.users import create_user, get_user_by_email
from backend.app.core.config import settings
from backend.app.db.models import User
from backend.app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["authentication"])

_MAX_EMAIL_LENGTH = 320
_MAX_NAME_LENGTH = 120
_MAX_PASSWORD_LENGTH = 128


# ── Request / response schemas ───────────────────────────────────────────────


class SignupRequest(BaseModel):
    """Request body for ``POST /auth/signup``."""

    email: str = Field(min_length=1, max_length=_MAX_EMAIL_LENGTH)
    password: str = Field(min_length=1, max_length=_MAX_PASSWORD_LENGTH)
    name: str | None = Field(default=None, max_length=_MAX_NAME_LENGTH)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if not normalized:
            raise ValueError("email must not be blank")
        return normalized

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        if not value:
            raise ValueError("password must not be empty")
        if len(value) > _MAX_PASSWORD_LENGTH:
            raise ValueError("password must be at most 128 characters")
        return value


class LoginRequest(BaseModel):
    """Request body for ``POST /auth/login``."""

    email: str = Field(min_length=1, max_length=_MAX_EMAIL_LENGTH)
    password: str = Field(min_length=1, max_length=_MAX_PASSWORD_LENGTH)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if not normalized:
            raise ValueError("email must not be blank")
        return normalized


class UserResponse(BaseModel):
    """Safe public representation of a user.

    Never includes ``password_hash``, JWTs, or any internal auth data.
    """

    id: UUID
    email: str
    name: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Cookie helpers ───────────────────────────────────────────────────────────


def _set_auth_cookie(response: Response, token: str) -> None:
    """Set the HttpOnly access-token cookie (never exposed to JavaScript)."""
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=settings.auth_jwt_expire_minutes * 60,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    """Delete the access-token cookie using the same attributes as set."""
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user account",
    description=(
        "Registers a user, sets an HttpOnly JWT access cookie, and returns the "
        "safe public user representation. Duplicate (normalized) emails return "
        "``409``."
    ),
    responses={
        201: {"description": "User created; access cookie set."},
        409: {"description": "Email already registered."},
        422: {"description": "Validation error."},
        500: {"description": "Internal server error."},
    },
)
async def signup(
    payload: SignupRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Register a new user and start an authenticated session."""
    existing = await get_user_by_email(db, payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    password_hash = hash_password(payload.password)
    try:
        user = await create_user(
            db,
            email=payload.email,
            password_hash=password_hash,
            name=payload.name,
        )
    except IntegrityError:
        # Race condition: another request created the email between our check
        # and our insert — the DB unique index is the final authority.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    _set_auth_cookie(response, create_access_token(user.id))
    return user


@router.post(
    "/login",
    response_model=UserResponse,
    summary="Log in",
    description=(
        "Authenticates with email + password and sets an HttpOnly JWT access "
        "cookie. Invalid credentials return a single generic ``401``."
    ),
    responses={
        200: {"description": "Authenticated; access cookie set."},
        401: {"description": "Invalid email or password."},
        422: {"description": "Validation error."},
        500: {"description": "Internal server error."},
    },
)
async def login(
    payload: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Log a user in and start an authenticated session."""
    user = await get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        # One generic message — never reveals whether the email exists.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    _set_auth_cookie(response, create_access_token(user.id))
    return user


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Current user",
    description=(
        "Returns the authenticated user's safe public representation. This is "
        "the canonical way for clients to resolve the current session."
    ),
    responses={
        200: {"description": "Authenticated user."},
        401: {"description": "Not authenticated."},
        500: {"description": "Internal server error."},
    },
)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Return the current authenticated user (401 when not authenticated)."""
    return current_user


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out",
    description=(
        "Clears the HttpOnly access cookie, ending the browser session. Safe "
        "to call when already logged out (stateless JWT — no server-side "
        "invalidation in this step)."
    ),
    responses={
        204: {"description": "Access cookie cleared."},
        500: {"description": "Internal server error."},
    },
)
async def logout(response: Response) -> None:
    """Clear the access-token cookie (idempotent)."""
    _clear_auth_cookie(response)
