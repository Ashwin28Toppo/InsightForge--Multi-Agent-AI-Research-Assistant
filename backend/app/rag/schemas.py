"""Typed structures for extracted document content.

Deliberately limited to extraction output for now — no embedding or
vector-store structures yet (those arrive in later steps).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PageContent:
    """Extracted text for a single page.

    ``page_number`` is ``None`` for documents without reliable native page
    boundaries (DOCX, TXT).
    """

    page_number: int | None
    text: str


@dataclass
class DocumentContent:
    """Extracted content for one ingested document.

    ``document_id`` is a UUID4 string generated at ingestion time.
    """

    document_id: str
    source_name: str
    source_type: str
    pages: list[PageContent] = field(default_factory=list)


@dataclass
class Chunk:
    """A single embeddable chunk produced from a :class:`DocumentContent`.

    Carries the metadata needed later for retrieval and citations:
    source document/filename, page, chunk index, and text.
    """

    chunk_id: str
    document_id: str
    source_name: str
    source_type: str
    chunk_index: int
    total_chunks: int
    page_number: int | None
    text: str
