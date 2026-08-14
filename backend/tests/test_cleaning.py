"""Unit tests for deterministic text cleaning (no external APIs)."""
from backend.app.rag.cleaning import clean_pages, clean_text
from backend.app.rag.schemas import PageContent


def test_clean_text_empty_string():
    assert clean_text("") == ""


def test_clean_text_whitespace_only():
    assert clean_text("   \n\t  ") == ""


def test_clean_text_none():
    assert clean_text(None) == ""  # type: ignore[arg-type]


def test_clean_text_normalizes_unicode():
    # "e" + combining acute accent -> composed "é" via NFKC
    assert clean_text("cafe\u0301") == "café"


def test_clean_text_replaces_non_breaking_space():
    assert clean_text("a\u00a0b") == "a b"


def test_clean_text_drops_zero_width_space():
    assert clean_text("a\u200bb") == "ab"


def test_clean_text_removes_control_characters():
    assert clean_text("a\x00b\x07c") == "abc"


def test_clean_text_normalizes_line_endings():
    assert clean_text("line1\r\nline2\rline3") == "line1\nline2\nline3"


def test_clean_text_collapses_excessive_blank_lines():
    assert clean_text("para1\n\n\n\npara2") == "para1\n\npara2"


def test_clean_text_preserves_paragraph_boundaries():
    assert clean_text("para1\n\npara2") == "para1\n\npara2"


def test_clean_text_collapses_repeated_spaces():
    assert clean_text("a    b   c") == "a b c"


def test_clean_text_tabs_to_single_space():
    assert clean_text("a\t\tb") == "a b"


def test_clean_text_strips_outer_whitespace():
    assert clean_text("  hello  ") == "hello"


def test_clean_text_preserves_punctuation():
    assert clean_text("Hello, world! (test) [x]: 42%") == "Hello, world! (test) [x]: 42%"


def test_clean_pages_preserves_page_numbers():
    pages = [
        PageContent(page_number=1, text="  page   one  "),
        PageContent(page_number=None, text="no page"),
    ]
    cleaned = clean_pages(pages)
    assert [p.page_number for p in cleaned] == [1, None]
    assert cleaned[0].text == "page one"
    assert cleaned[1].text == "no page"
