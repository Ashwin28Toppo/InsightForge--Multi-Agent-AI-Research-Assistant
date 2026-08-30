"""Embedding factory — provider-swappable.

Providers are created lazily (never at module import time) and no network
calls happen at construction; they only occur when embeddings are computed.

The design is intentionally small so a provider can be added later by
extending ``get_embeddings``.
"""
from __future__ import annotations

from langchain_core.embeddings import Embeddings

from backend.app.core.config import settings

SUPPORTED_PROVIDERS = ("google",)


def get_embeddings(
    provider: str | None = None,
    api_key: str | None = None,
) -> Embeddings:
    """Return an embeddings instance for the configured provider.

    Args:
        provider: Overrides ``settings.embedding_provider`` (case-insensitive).
        api_key: Optional API-key override for the provider.

    Returns:
        A LangChain ``Embeddings`` instance (constructed lazily).

    Raises:
        ValueError: for unsupported providers or missing/invalid configuration.
    """
    provider = (provider or settings.embedding_provider).lower()
    if provider == "google":
        return _get_google_embeddings(api_key=api_key)
    raise ValueError(
        f"Unsupported embedding provider '{provider}'. "
        f"Supported providers: {', '.join(SUPPORTED_PROVIDERS)}"
    )


def _get_google_embeddings(api_key: str | None = None) -> Embeddings:
    key = api_key or settings.google_api_key
    if not key:
        raise ValueError(
            "google_api_key is not configured. Set GOOGLE_API_KEY in your "
            "environment or .env file."
        )
    if not settings.embedding_model:
        raise ValueError("embedding_model must not be empty")
    if settings.embedding_dim <= 0:
        raise ValueError(f"embedding_dim must be > 0, got {settings.embedding_dim}")

    # Imported lazily so module import stays cheap and provider-agnostic.
    # langchain-google-genai 4.x names the API-key field `google_api_key` and
    # the dimensionality field `output_dimensionality`.
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        task_type="RETRIEVAL_DOCUMENT",
        google_api_key=key,
        output_dimensionality=settings.embedding_dim,
    )
