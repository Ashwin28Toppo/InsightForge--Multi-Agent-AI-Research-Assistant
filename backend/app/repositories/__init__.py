"""Repository layer (Phase 2F Step 2).

``JobStore`` is the persistence abstraction for research jobs. The API layer
interacts ONLY with this interface — never with a concrete dictionary. The
current implementation is ``InMemoryJobStore`` (identical behavior to the
former module-level ``_jobs`` dict); a PostgreSQL-backed implementation will be
introduced in a later step without changing the API contract.
"""
