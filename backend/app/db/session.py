"""Async SQLAlchemy engine/session infrastructure (Phase 2F Step 2).

Lazy by design: importing this module NEVER creates an engine or opens a
connection. The engine is created on first use via ``get_engine()`` and
requires ``DATABASE_URL`` to be configured. The application does not use the
database yet — this is the foundation for the later persistence steps.

FastAPI integration: ``get_db`` is the request-scoped dependency that yields
one ``AsyncSession`` per request. No endpoint consumes it yet, so the current
application (and its in-memory job store) is completely unaffected.
"""
from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.core.config import settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the shared async engine, creating it lazily on first use.

    Creating an async engine does not connect; the first actual connection
    happens when a session runs a statement. If ``DATABASE_URL`` is not
    configured, a clear error is raised instead of silently misbehaving.
    """
    global _engine
    if _engine is None:
        if not settings.database_url:
            raise RuntimeError(
                "DATABASE_URL is not configured. Set it (e.g. "
                "postgresql+asyncpg://user:password@host:5432/insightforge) "
                "before using the database."
            )
        _engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the shared async session factory, creating it lazily."""
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
        )
    return _sessionmaker


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yield one async session per request.

    The session is opened inside a context manager and closed automatically
    when the request finishes.
    """
    async with get_sessionmaker()() as session:
        yield session
