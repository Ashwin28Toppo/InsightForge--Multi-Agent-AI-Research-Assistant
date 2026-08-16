"""FastAPI authentication dependency (Phase 2F Step 3).

``get_current_user`` resolves the current session from the HttpOnly JWT cookie
and loads the user from the database. Every failure — missing token, malformed
token, expired token, bad signature, unknown user — returns the SAME 401 with
``{"detail": "Not authenticated"}`` so nothing about the failure mode leaks.

The token check lives in its own dependency (``get_current_user_id``) that runs
FIRST: FastAPI short-circuits when it raises, so an unauthenticated request
returns 401 without ever constructing a database session. This matters for the
no-``DATABASE_URL`` dev state (a missing/bad cookie must 401, not 500).

NOTE: no research endpoint depends on this yet; ownership enforcement lands in
Phase 2F Step 4.
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.security import AuthenticationError, decode_access_token
from backend.app.auth.users import get_user_by_id
from backend.app.core.config import settings
from backend.app.db.models import User
from backend.app.db.session import get_db


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


async def get_current_user_id(
    access_token: Annotated[
        str | None,
        Cookie(alias=settings.auth_cookie_name),
    ] = None,
) -> UUID:
    """Validate the access cookie and return the user UUID.

    Runs before any database work; raises the single 401 when the cookie is
    missing or the token is invalid/expired.
    """
    if not access_token:
        raise _unauthorized()
    try:
        return decode_access_token(access_token)
    except AuthenticationError:
        raise _unauthorized()


async def get_current_user(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Resolve and return the authenticated user (401 on any failure)."""
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise _unauthorized()
    return user
