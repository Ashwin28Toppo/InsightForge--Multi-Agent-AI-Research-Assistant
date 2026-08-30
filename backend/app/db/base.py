"""SQLAlchemy 2.x declarative base for all InsightForge ORM models."""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for the application's ORM models (SQLAlchemy 2.x).

    ``Base.metadata`` is the single metadata registry consumed by Alembic
    migrations (see ``backend/alembic/env.py``).
    """

