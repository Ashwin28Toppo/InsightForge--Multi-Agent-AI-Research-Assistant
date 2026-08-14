"""Unit tests for page-aware chunking.

Local and deterministic — no external APIs, no network calls.
"""
from __future__ import annotations

import pytest

from backend.app.rag.chunking import chunk_document
from backend.app.rag.schemas import Chunk, DocumentContent, PageContent


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_document(
    text: str = "",
    source_type: str = "txt",
    source_name: str = "doc.txt",
    document_id: str = "doc-123",
    pages: list[PageContent] | None = None,
) -> DocumentContent:
    return DocumentContent(
        document_id=document_id,
        source_name=source_name,
        source_type=source_type,
        pages=pages if pages is not None else [PageContent(page_number=None, text=text)],
    )


def fingerprint(chunks: list[Chunk]) -> list[tuple]:
    """Everything except chunk_id (which is a UUID4)."""
    return [
        (
            c.document_id,
            c.source_name,
            c.source_type,
            c.chunk_index,
            c.total_chunks,
            c.page_number,
            c.text,
        )
        for c in chunks
    ]


# ── Basic behavior ───────────────────────────────────────────────────────────

def test_empty_document_returns_no_chunks():
    assert chunk_document(make_document(pages=[])) == []
    # whitespace-only page must not produce empty chunks either
    doc = make_document(text="   \n\n  ")
    assert chunk_document(doc, chunk_size=100, chunk_overlap=0) == []


def test_very_short_document_single_chunk():
    chunks = chunk_document(make_document(text="Short doc."), chunk_size=1000, chunk_overlap=150)
    assert len(chunks) == 1
    assert chunks[0].text == "Short doc."
    assert chunks[0].chunk_index == 0
    assert chunks[0].total_chunks == 1


def test_document_shorter_than_chunk_size_is_one_chunk():
    chunks = chunk_document(make_document(text="x" * 500), chunk_size=1000, chunk_overlap=150)
    assert len(chunks) == 1
    assert chunks[0].text == "x" * 500


def test_document_exactly_at_chunk_size_is_one_chunk():
    chunks = chunk_document(make_document(text="y" * 100), chunk_size=100, chunk_overlap=0)
    assert len(chunks) == 1
    assert chunks[0].text == "y" * 100


def test_long_document_produces_multiple_chunks():
    chunks = chunk_document(make_document(text="word " * 300), chunk_size=100, chunk_overlap=0)
    assert len(chunks) > 1
    assert all(c.text.strip() for c in chunks)  # no empty chunks


# ── Overlap behavior ─────────────────────────────────────────────────────────

def test_overlap_increases_chunk_count():
    text = "word " * 300
    no_overlap = chunk_document(make_document(text=text), chunk_size=100, chunk_overlap=0)
    with_overlap = chunk_document(make_document(text=text), chunk_size=100, chunk_overlap=20)
    assert len(with_overlap) > len(no_overlap)


def test_overlap_duplicates_content_across_chunks():
    text = "word " * 300
    no_overlap = chunk_document(make_document(text=text), chunk_size=100, chunk_overlap=0)
    with_overlap = chunk_document(make_document(text=text), chunk_size=100, chunk_overlap=20)
    total_no = sum(len(c.text) for c in no_overlap)
    total_with = sum(len(c.text) for c in with_overlap)
    # overlap re-introduces text, so the total character count grows
    assert total_with > total_no


# ── Page attribution ─────────────────────────────────────────────────────────

def test_pdf_page_numbers_preserved():
    pages = [
        PageContent(page_number=1, text="Content of page one."),
        PageContent(page_number=2, text="Content of page two."),
        PageContent(page_number=3, text="Content of page three."),
    ]
    chunks = chunk_document(
        make_document(source_type="pdf", source_name="a.pdf", pages=pages),
        chunk_size=1000,
        chunk_overlap=0,
    )
    assert [c.page_number for c in chunks] == [1, 2, 3]


def test_chunks_do_not_merge_across_pages():
    pages = [
        PageContent(page_number=1, text="A" * 200),
        PageContent(page_number=2, text="B" * 200),
    ]
    chunks = chunk_document(
        make_document(source_type="pdf", source_name="a.pdf", pages=pages),
        chunk_size=300,
        chunk_overlap=0,
    )
    assert len(chunks) == 2
    assert chunks[0].page_number == 1 and chunks[0].text == "A" * 200
    assert chunks[1].page_number == 2 and chunks[1].text == "B" * 200


def test_long_single_page_splits_into_multiple_chunks_same_page():
    pages = [PageContent(page_number=1, text="sentence one. " * 30)]
    chunks = chunk_document(
        make_document(source_type="pdf", source_name="a.pdf", pages=pages),
        chunk_size=80,
        chunk_overlap=10,
    )
    assert len(chunks) > 1
    assert {c.page_number for c in chunks} == {1}


def test_txt_and_docx_page_number_is_none():
    txt_chunks = chunk_document(make_document(text="word " * 60), chunk_size=100, chunk_overlap=10)
    docx_chunks = chunk_document(
        make_document(source_type="docx", source_name="a.docx", text="word " * 60),
        chunk_size=100,
        chunk_overlap=10,
    )
    assert all(c.page_number is None for c in txt_chunks)
    assert all(c.page_number is None for c in docx_chunks)


# ── Paragraph boundaries & content ───────────────────────────────────────────

def test_paragraph_boundaries_preserved():
    text = ("P" * 60) + "\n\n" + ("Q" * 60)
    chunks = chunk_document(make_document(text=text), chunk_size=100, chunk_overlap=0)
    assert len(chunks) == 2
    assert chunks[0].text == "P" * 60
    assert chunks[1].text == "Q" * 60


def test_unicode_text_preserved():
    text = "日本語のテキスト" * 40
    chunks = chunk_document(make_document(text=text), chunk_size=50, chunk_overlap=5)
    assert chunks
    assert all(c.text for c in chunks)  # no empty chunks
    assert all("\ufffd" not in c.text for c in chunks)  # no replacement chars
    allowed = set("日本語のテキスト")
    for c in chunks:
        assert set(c.text) <= allowed  # no mojibake / corruption


# ── Metadata, indexes, determinism ───────────────────────────────────────────

def test_metadata_preserved_on_all_chunks():
    chunks = chunk_document(
        make_document(
            document_id="meta-doc",
            source_name="report.pdf",
            source_type="pdf",
            pages=[PageContent(page_number=1, text="word " * 300)],
        ),
        chunk_size=100,
        chunk_overlap=20,
    )
    assert len(chunks) > 1
    for c in chunks:
        assert c.document_id == "meta-doc"
        assert c.source_name == "report.pdf"
        assert c.source_type == "pdf"
        assert c.chunk_index == c.chunk_index  # sanity
        assert c.total_chunks == len(chunks)


def test_indexes_are_zero_based_and_total_is_correct():
    chunks = chunk_document(make_document(text="word " * 300), chunk_size=100, chunk_overlap=20)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert all(c.total_chunks == len(chunks) for c in chunks)


def test_chunking_is_deterministic_except_chunk_id():
    doc = make_document(text="lorem ipsum dolor sit amet. " * 80)
    first = chunk_document(doc, chunk_size=120, chunk_overlap=20)
    second = chunk_document(doc, chunk_size=120, chunk_overlap=20)
    assert fingerprint(first) == fingerprint(second)
    assert [c.chunk_id for c in first] != [c.chunk_id for c in second]
    # chunk_id is a UUID4-style string
    assert all(len(c.chunk_id) == 36 for c in first)


def test_defaults_read_from_settings():
    # No explicit size/overlap -> uses settings.chunk_size / chunk_overlap.
    chunks = chunk_document(make_document(text="lorem ipsum " * 200))
    assert len(chunks) >= 2
    assert all(len(c.text) <= 1000 for c in chunks)  # settings.chunk_size == 1000
    assert all(c.total_chunks == len(chunks) for c in chunks)


# ── Configuration validation ─────────────────────────────────────────────────

def test_invalid_chunk_size_zero_raises():
    with pytest.raises(ValueError, match="chunk_size"):
        chunk_document(make_document(text="x" * 10), chunk_size=0, chunk_overlap=0)


def test_invalid_chunk_size_negative_raises():
    with pytest.raises(ValueError, match="chunk_size"):
        chunk_document(make_document(text="x" * 10), chunk_size=-5, chunk_overlap=0)


def test_invalid_chunk_overlap_negative_raises():
    with pytest.raises(ValueError, match="chunk_overlap"):
        chunk_document(make_document(text="x" * 10), chunk_size=100, chunk_overlap=-1)


def test_invalid_chunk_overlap_equals_chunk_size_raises():
    with pytest.raises(ValueError, match="chunk_overlap"):
        chunk_document(make_document(text="x" * 10), chunk_size=100, chunk_overlap=100)


def test_invalid_chunk_overlap_greater_than_chunk_size_raises():
    with pytest.raises(ValueError, match="chunk_overlap"):
        chunk_document(make_document(text="x" * 10), chunk_size=100, chunk_overlap=150)
