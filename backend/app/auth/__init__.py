"""Backend authentication (Phase 2F Step 3).

Argon2id password hashing, JWT access tokens transported via an HttpOnly
cookie, and the ``get_current_user`` dependency. This establishes the auth
surface (signup/login/logout/me) WITHOUT yet protecting the research API —
ownership enforcement lands in Phase 2F Step 4.
"""
