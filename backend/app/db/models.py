"""Initial ORM models (Phase 2F Step 2).

These mirror the Phase 2F Step 1 audit schema. The ``ResearchJob`` row id
corresponds exactly to the API's ``job_id``, and ``result`` is kept as a JSONB
column (the opaque dict produced by the pipeline) — there is deliberately no
separate ``research_results`` table.

Design notes:
- IDs are UUIDs (``sqlalchemy.Uuid`` renders ``UUID`` on PostgreSQL).
- ``completed_steps`` / ``result`` are JSONB (PostgreSQL-compatible).
- ``status`` is a plain String + CHECK constraint rather than a PostgreSQL
  enum type, keeping migrations and cross-dialect behavior flexible.
- ``email`` uses a plain String(320) with a unique index instead of ``citext``
  — ``citext`` is PostgreSQL-specific and would complicate cross-dialect
  testing; case-insensitive uniqueness can be layered on later if needed.
- ``user_id`` exists on the model but ownership/auth enforcement is NOT
  introduced in this step (it is nullable so the current anonymous in-memory
  behavior has a clear migration path).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

_JOB_STATUSES = ("queued", "running", "completed", "failed")


class User(Base):
    """A registered application user (authentication lands in a later step)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(320), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    research_jobs: Mapped[list["ResearchJob"]] = relationship(
        back_populates="user"
    )


class ResearchJob(Base):
    """A research job; ``id`` equals the API's ``job_id``."""

    __tablename__ = "research_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_research_jobs_status",
        ),
        Index("ix_research_jobs_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'queued'")
    )
    current_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_steps: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(16), nullable=True)
    report_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User | None] = relationship(back_populates="research_jobs")
