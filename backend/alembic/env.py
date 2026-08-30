"""Alembic migration environment.

The migration URL comes from the application settings (``DATABASE_URL``) so
there is a single source of truth. Imports register the ORM models on
``Base.metadata`` so ``autogenerate`` (and this project's hand-written initial
migration) reflect the real schema.
"""
from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Make the repo root importable so `backend.app.*` resolves no matter where
# Alembic is invoked from (repo root or backend/).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.core.config import settings  # noqa: E402
from backend.app.db.base import Base  # noqa: E402
import backend.app.db.models  # noqa: E402,F401  (register models on Base.metadata)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Prefer DATABASE_URL from the app settings over anything in alembic.ini.
if settings.database_url:
    config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a live database)."""
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        # No DATABASE_URL configured. Fall back to a placeholder PostgreSQL URL
        # purely so offline SQL rendering (``alembic upgrade head --sql``) can
        # select the PostgreSQL dialect without connecting. It is never used to
        # reach a real database.
        url = "postgresql+asyncpg://localhost/insightforge"
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    """Run migrations against an async engine (asyncpg driver)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=None,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (against the configured database)."""
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
