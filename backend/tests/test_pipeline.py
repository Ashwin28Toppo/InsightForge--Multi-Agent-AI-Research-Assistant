"""Unit tests for pure helpers in ``backend.app.main``."""
from backend.app.main import build_research_context


def test_build_research_context_combines_both_sections():
    out = build_research_context("SEARCH_BODY", "SCRAPE_BODY")
    assert "SEARCH RESULTS" in out
    assert "DETAILED SCRAPED CONTENT" in out
    assert "SEARCH_BODY" in out
    assert "SCRAPE_BODY" in out
