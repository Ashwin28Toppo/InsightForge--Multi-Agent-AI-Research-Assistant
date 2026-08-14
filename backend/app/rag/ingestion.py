"""Document ingestion: PDF/DOCX/TXT -> normalized, page-aware text.

Pure, deterministic pipeline (no external APIs). Callers should catch
:class:`IngestionError` (and its subclasses) to handle bad documents
without crashing the application.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

from backend.app.rag.cleaning import clean_pages, clean_text
from backend.app.rag.schemas import DocumentContent, PageContent

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class IngestionError(Exception):
    """Base error for document ingestion failures."""


class UnsupportedExtensionError(IngestionError, ValueError):
    """Raised when the file extension is not a supported document type."""


class DocumentNotFoundError(IngestionError, FileNotFoundError):
    """Raised when the input path does not exist or is not a file."""


def ingest_document(path: str | Path) -> DocumentContent:
    """Extract normalized, page-aware text from a PDF, DOCX, or TXT file.

    Args:
        path: Path to the document.

    Returns:
        :class:`DocumentContent` with a fresh UUID4 ``document_id`` and
        cleaned, page-aware ``pages``.

    Raises:
        DocumentNotFoundError: if the file does not exist or is not a file.
        UnsupportedExtensionError: if the extension is not supported.
        IngestionError: if the document cannot be read/extracted.
    """
    path = Path(path)
    _validate_file(path)

    ext = path.suffix.lower()
    document_id = str(uuid.uuid4())
    source_name = path.name

    if ext == ".pdf":
        pages = _ingest_pdf(path)
        source_type = "pdf"
    elif ext == ".docx":
        pages = _ingest_docx(path)
        source_type = "docx"
    else:  # .txt
        pages = _ingest_txt(path)
        source_type = "txt"

    return DocumentContent(
        document_id=document_id,
        source_name=source_name,
        source_type=source_type,
        pages=pages,
    )


def _validate_file(path: Path) -> None:
    if not path.exists():
        raise DocumentNotFoundError(f"Document not found: {path}")
    if not path.is_file():
        raise DocumentNotFoundError(f"Not a file: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise UnsupportedExtensionError(
            f"Unsupported file extension '{path.suffix}'. "
            f"Supported extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )


def _ingest_pdf(path: Path) -> list[PageContent]:
    try:
        reader = PdfReader(str(path))
    except Exception as e:
        raise IngestionError(f"Could not read PDF '{path.name}': {e}") from e

    pages: list[PageContent] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            # Pages with no extractable text must not crash the pipeline.
            text = ""
        pages.append(PageContent(page_number=index, text=clean_text(text)))
    return pages


def _ingest_docx(path: Path) -> list[PageContent]:
    try:
        document = DocxDocument(str(path))
    except Exception as e:
        raise IngestionError(f"Could not read DOCX '{path.name}': {e}") from e

    # DOCX has no reliable native page boundaries, so represent the whole
    # document as a single pageless page. Paragraph ordering is preserved
    # by joining paragraphs with a blank line.
    paragraph_text = "\n\n".join(p.text for p in document.paragraphs)
    return [PageContent(page_number=None, text=clean_text(paragraph_text))]


def _ingest_txt(path: Path) -> list[PageContent]:
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise IngestionError(f"Could not decode '{path.name}' as UTF-8: {e}") from e
    except OSError as e:
        raise IngestionError(f"Could not read '{path.name}': {e}") from e
    return [PageContent(page_number=None, text=clean_text(raw))]
