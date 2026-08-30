"""Page-aware document chunking.

Converts cleaned :class:`DocumentContent` into overlapping, metadata-rich
chunks ready for embedding and vector storage.

Deterministic for a given input and configuration: the same document and
settings always produce the same number/order/text/metadata of chunks.
Only ``chunk_id`` differs between runs (it uses UUID4).
"""
from __future__ import annotations

import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.app.core.config import settings
from backend.app.rag.schemas import Chunk, DocumentContent

# Preferred break points, in order: paragraphs, lines, sentences, words, chars.
_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def _validate_chunk_config(chunk_size: int, chunk_overlap: int) -> None:
    """Raise a clear ``ValueError`` for invalid chunking configuration."""
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be greater than 0, got {chunk_size}")
    if chunk_overlap < 0:
        raise ValueError(f"chunk_overlap must be non-negative, got {chunk_overlap}")
    if chunk_overlap >= chunk_size:
        raise ValueError(
            f"chunk_overlap ({chunk_overlap}) must be smaller than "
            f"chunk_size ({chunk_size})"
        )


def chunk_document(
    document: DocumentContent,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """Split a cleaned document into overlapping, page-aware chunks.

    Args:
        document: Cleaned extracted content from :func:`ingest_document`.
        chunk_size: Max characters per chunk; falls back to settings.
        chunk_overlap: Characters of overlap between consecutive chunks;
            falls back to settings.

    Returns:
        List of :class:`Chunk` with deterministic zero-based ``chunk_index``
        in document order and correct ``total_chunks``.

    Raises:
        ValueError: if the chunk size/overlap configuration is invalid.
    """
    if chunk_size is None:
        chunk_size = settings.chunk_size
    if chunk_overlap is None:
        chunk_overlap = settings.chunk_overlap
    _validate_chunk_config(chunk_size, chunk_overlap)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=_SEPARATORS,
    )

    # Page-aware splitting: PDF pages are chunked independently so a chunk
    # never spans two pages (preserving reliable page attribution). TXT/DOCX
    # use page_number=None and chunk as a single pageless unit.
    raw_chunks: list[tuple[int | None, str]] = []
    for page in document.pages:
        if not page.text.strip():
            continue  # never produce empty chunks
        for piece in splitter.split_text(page.text):
            if piece.strip():
                raw_chunks.append((page.page_number, piece))

    total = len(raw_chunks)
    return [
        Chunk(
            chunk_id=str(uuid.uuid4()),
            document_id=document.document_id,
            source_name=document.source_name,
            source_type=document.source_type,
            chunk_index=index,
            total_chunks=total,
            page_number=page_number,
            text=text,
        )
        for index, (page_number, text) in enumerate(raw_chunks)
    ]
