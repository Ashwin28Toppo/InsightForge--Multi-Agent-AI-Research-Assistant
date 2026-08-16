"""Database package (Phase 2F Step 2).

Declarative base, async session infrastructure, and the initial ORM models.
Nothing in this package opens a connection at import time; connectivity is
only established when the session layer is actually used (and requires
``DATABASE_URL`` to be configured).
"""
