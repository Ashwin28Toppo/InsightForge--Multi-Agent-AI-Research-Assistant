"""Web research tools: Tavily search + HTML page extraction.

Contains the two LangChain tools used by the search and reader agents,
plus small pure helpers (kept separate so they can be unit tested).
"""
from __future__ import annotations

import re
from functools import lru_cache

import requests
from bs4 import BeautifulSoup
from langchain.tools import tool
from tavily import TavilyClient

from backend.app.core.config import settings


@lru_cache(maxsize=1)
def _get_tavily_client() -> TavilyClient:
    return TavilyClient(api_key=settings.tavily_api_key)


# ── Tools ────────────────────────────────────────────────────────────────────

@tool
def web_search(query: str) -> str:
    """Search the web for up-to-date information on a given topic and return relevant titles, URLs, and summary snippets from search results."""
    results = _get_tavily_client().search(query=query, max_results=settings.tavily_max_results)
    return format_search_results(results["results"])


@tool
def scrape_url(url: str) -> str:
    """Scrape and return clean text content from a given URL for deeper reading."""
    try:
        html = fetch_url(url)
        return extract_clean_text(html, max_chars=settings.scrape_max_chars)
    except Exception as e:
        return f"Could not scrape URL: {str(e)}"


# ── Pure helpers (unit-testable) ─────────────────────────────────────────────

def format_search_results(results: list[dict]) -> str:
    """Format raw Tavily result dicts into a readable text block."""
    out = []
    for r in results:
        out.append(
            f"Title: {r['title']}\nURL: {r['url']}\n"
            f"Snippet: {r['content'][: settings.search_snippet_max_chars]}\n"
        )
    return "\n---\n".join(out)


def fetch_url(url: str, timeout: int | None = None) -> str:
    """Fetch the raw HTML for a URL. Raises on HTTP/network errors."""
    resp = requests.get(
        url,
        timeout=timeout or settings.scrape_timeout,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    resp.raise_for_status()
    return resp.text


def extract_clean_text(html: str, max_chars: int | None = None) -> str:
    """Parse raw HTML and return readable text, truncated to ``max_chars``."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return text[: max_chars or settings.scrape_max_chars]


_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")
_URL_TRAILING_CHARS = ".,;:!?)]}"


def extract_urls(text: str) -> list[str]:
    """Extract unique URLs (in order of appearance) from a text blob."""
    urls: list[str] = []
    for match in _URL_PATTERN.findall(text):
        cleaned = match.rstrip(_URL_TRAILING_CHARS)
        if cleaned not in urls:
            urls.append(cleaned)
    return urls
