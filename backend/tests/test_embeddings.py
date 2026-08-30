"""Unit tests for the embedding factory (no network/API calls)."""
import pytest

from backend.app.rag.embeddings import get_embeddings


class FakeSettings:
    """Minimal stand-in for config settings used by embeddings.py."""

    embedding_provider = "google"
    embedding_model = "gemini-embedding-2"
    embedding_dim = 768
    google_api_key = ""


def test_unsupported_provider_raises_value_error(monkeypatch):
    monkeypatch.setattr("backend.app.rag.embeddings.settings", FakeSettings())
    with pytest.raises(ValueError, match="provider"):
        get_embeddings(provider="unknown-provider")


def test_google_provider_requires_api_key(monkeypatch):
    monkeypatch.setattr("backend.app.rag.embeddings.settings", FakeSettings())
    with pytest.raises(ValueError, match="google_api_key"):
        get_embeddings(provider="google")


def test_google_provider_requires_non_empty_model(monkeypatch):
    class NoModel(FakeSettings):
        embedding_model = ""

    monkeypatch.setattr("backend.app.rag.embeddings.settings", NoModel())
    with pytest.raises(ValueError, match="embedding_model"):
        get_embeddings(provider="google", api_key="fake-key")


def test_google_provider_validates_embedding_dim(monkeypatch):
    class BadDim(FakeSettings):
        embedding_dim = 0

    monkeypatch.setattr("backend.app.rag.embeddings.settings", BadDim())
    with pytest.raises(ValueError, match="embedding_dim"):
        get_embeddings(provider="google", api_key="fake-key")


def test_google_provider_constructs_with_api_key_override_no_network(monkeypatch):
    monkeypatch.setattr("backend.app.rag.embeddings.settings", FakeSettings())
    emb = get_embeddings(provider="google", api_key="fake-key")

    # Verifies config is wired correctly without any API call.
    assert emb.model == "gemini-embedding-2"
    assert emb.task_type == "RETRIEVAL_DOCUMENT"
    assert emb.output_dimensionality == 768


def test_default_provider_read_from_settings(monkeypatch):
    monkeypatch.setattr("backend.app.rag.embeddings.settings", FakeSettings())
    emb = get_embeddings(api_key="fake-key")  # provider from settings
    assert emb.model == "gemini-embedding-2"
