"""Unit tests for settings loading in ``backend.app.core.config``."""
from backend.app.core.config import Settings


def test_defaults_without_env_file():
    s = Settings(_env_file=None)
    assert s.llm_model == "llama-3.1-8b-instant"
    assert s.llm_temperature == 0.0
    assert s.llm_max_retries == 2
    assert s.llm_rate_limit_retries == 5
    assert s.research_loop_max_rounds == 0
    assert s.llm_max_tokens == 1536
    assert s.evidence_max_chars == 300
    assert s.search_snippet_max_chars == 150
    assert s.run_critic is False
    assert s.tavily_max_results == 5
    assert s.scrape_max_chars == 3000


def test_tavily_key_reads_existing_typo_key_name(monkeypatch):
    monkeypatch.setenv("TAVILY_KEY_KEY", "fake-key")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    s = Settings(_env_file=None)
    assert s.tavily_api_key == "fake-key"


def test_tavily_key_reads_canonical_name(monkeypatch):
    monkeypatch.delenv("TAVILY_KEY_KEY", raising=False)
    monkeypatch.setenv("TAVILY_API_KEY", "canonical-key")
    s = Settings(_env_file=None)
    assert s.tavily_api_key == "canonical-key"


def test_rag_defaults_without_env_file(monkeypatch):
    # Make the test independent of any real API keys in the environment/.env.
    for key in ("GOOGLE_API_KEY", "GROQ_API_KEY", "TAVILY_API_KEY", "TAVILY_KEY_KEY"):
        monkeypatch.delenv(key, raising=False)
    s = Settings(_env_file=None)
    assert s.google_api_key == ""
    assert s.embedding_provider == "google"
    assert s.embedding_model == "gemini-embedding-2"
    assert s.embedding_dim == 768
    assert s.qdrant_path == "./qdrant_storage"
    assert s.qdrant_collection == "insightforge_documents"
    assert s.chunk_size == 1000
    assert s.chunk_overlap == 150
    assert s.retrieval_top_k == 5
    assert s.retrieval_score_threshold == 0.5
    assert s.document_storage_dir == "./data/documents"


def test_settings_instantiate_without_qdrant_url(monkeypatch):
    # Local Qdrant must not require QDRANT_URL to be configured.
    monkeypatch.delenv("QDRANT_URL", raising=False)
    s = Settings(_env_file=None)
    assert s.qdrant_url is None
    assert s.qdrant_path == "./qdrant_storage"


def test_embedding_settings_read_from_env(monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL", "gemini-embedding-001")
    monkeypatch.setenv("EMBEDDING_DIM", "1536")
    s = Settings(_env_file=None)
    assert s.embedding_model == "gemini-embedding-001"
    assert s.embedding_dim == 1536
