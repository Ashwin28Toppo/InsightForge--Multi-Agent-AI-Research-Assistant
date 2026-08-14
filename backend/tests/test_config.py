"""Unit tests for settings loading in ``backend.app.core.config``."""
from backend.app.core.config import Settings


def test_defaults_without_env_file():
    s = Settings(_env_file=None)
    assert s.llm_model == "llama-3.3-70b-versatile"
    assert s.llm_temperature == 0.0
    assert s.llm_max_retries == 2
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
