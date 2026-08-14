"""Unit tests for the pure helpers in ``backend.app.tools.web``."""
from backend.app.tools.web import extract_clean_text, extract_urls, format_search_results


def test_format_search_results_lists_titles_urls_and_snippets():
    results = [
        {"title": "Alpha", "url": "https://alpha.example.com", "content": "A" * 400},
        {"title": "Beta", "url": "https://beta.example.com", "content": "short"},
    ]
    out = format_search_results(results)

    assert "Title: Alpha" in out
    assert "URL: https://alpha.example.com" in out
    assert "Title: Beta" in out
    # snippet truncated to 300 chars
    assert "A" * 300 in out
    assert "A" * 301 not in out


def test_format_search_results_empty():
    assert format_search_results([]) == ""


def test_extract_clean_text_strips_noise():
    html = """
    <html><body>
      <script>var x = 1;</script>
      <style>.cls { color: red; }</style>
      <nav>Nav links</nav>
      <footer>Footer text</footer>
      <p>Hello <b>world</b></p>
    </body></html>
    """
    text = extract_clean_text(html, max_chars=500)
    assert "Hello world" in text
    assert "script" not in text.lower()
    assert "Nav links" not in text
    assert "Footer text" not in text


def test_extract_clean_text_truncates_to_max_chars():
    html = f"<html><body><p>{'x' * 100}</p></body></html>"
    assert len(extract_clean_text(html, max_chars=50)) <= 50


def test_extract_urls_unique_and_in_order():
    text = (
        "See https://a.example.com/1 and https://b.example.com/2, "
        "again https://a.example.com/1."
    )
    assert extract_urls(text) == [
        "https://a.example.com/1",
        "https://b.example.com/2",
    ]


def test_extract_urls_strips_trailing_punctuation():
    assert extract_urls("Check https://a.example.com/page?x=1! and (https://b.example.com).") == [
        "https://a.example.com/page?x=1",
        "https://b.example.com",
    ]


def test_extract_urls_empty():
    assert extract_urls("no urls here") == []
