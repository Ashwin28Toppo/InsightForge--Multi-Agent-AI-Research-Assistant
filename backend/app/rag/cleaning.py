"""Deterministic text cleaning (no LLM, no external calls)."""
from __future__ import annotations

import re
import unicodedata

from backend.app.rag.schemas import PageContent

# Control characters to drop (keeps \t \n \r).
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Three or more consecutive newlines -> a single blank line (paragraph break).
_EXCESSIVE_BLANK_LINES = re.compile(r"\n{3,}")
# Runs of two or more spaces within a line.
_MULTIPLE_SPACES = re.compile(r" {2,}")
# Trailing spaces/tabs at the end of a line.
_LINE_TRAILING_WHITESPACE = re.compile(r"[ \t]+$")


def clean_text(text: str) -> str:
    """Normalize a block of text deterministically.

    - Normalizes Unicode (NFKC)
    - Replaces non-breaking spaces; drops zero-width and BOM characters
    - Removes control characters
    - Normalizes line endings to ``\\n``
    - Collapses excessive blank lines while preserving paragraph breaks
    - Collapses repeated spaces and trims each line
    - Returns ``""`` for empty or whitespace-only input

    Punctuation and meaningful content are preserved.
    """
    if not text:
        return ""

    # 1. Unicode normalization.
    text = unicodedata.normalize("NFKC", text)
    # 2. Replace non-breaking spaces; drop zero-width and BOM characters.
    text = (
        text.replace("\u00a0", " ")
        .replace("\u200b", "")
        .replace("\ufeff", "")
    )
    # 3. Drop control characters (keep \t \n \r).
    text = _CONTROL_CHARS.sub("", text)
    # 4. Normalize line endings to \n.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 5. Collapse 3+ newlines into a single blank line (paragraph boundary).
    text = _EXCESSIVE_BLANK_LINES.sub("\n\n", text)
    # 6. Per-line cleanup: tabs -> space, collapse repeated spaces, trim.
    lines = []
    for line in text.split("\n"):
        line = _LINE_TRAILING_WHITESPACE.sub("", line)
        line = _MULTIPLE_SPACES.sub(" ", line.replace("\t", " "))
        lines.append(line.strip())
    text = "\n".join(lines).strip()

    return text


def clean_pages(pages: list[PageContent]) -> list[PageContent]:
    """Apply :func:`clean_text` to every page, preserving page numbers."""
    return [
        PageContent(page_number=page.page_number, text=clean_text(page.text))
        for page in pages
    ]
