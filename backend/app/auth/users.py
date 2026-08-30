"""User database access (Phase 2F Step 3).

A small, focused data-access layer for the auth flow, built on the Step 2
SQLAlchemy infrastructure — there is deliberately no second session system.
Emails are normalized (strip + lowercase) at the application layer because
``citext`` was intentionally deferred in Step 2; the unique index on
``users.email`` still enforces uniqueness at the database level.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import User


def normalize_email(email: str) -> str:
    """Normalize an email address: strip surrounding whitespace, lowercase."""
    return (email or "").strip().lower()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Find a user by normalized email (case-insensitive via normalization)."""
    result = await db.execute(
        select(User).where(User.email == normalize_email(email))
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    """Find a user by primary key."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password_hash: str,
    name: str | None = None,
) -> User:
    """Create and commit a new user.

    ``created_at``/``updated_at`` are set explicitly so inserts work across
    database backends (SQLite has no ``now()``); the server_default remains as
    a safety net for direct SQL inserts on PostgreSQL.
    """
    now = datetime.now(timezone.utc)
    user = User(
        email=normalize_email(email),
        password_hash=password_hash,
        name=name,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
