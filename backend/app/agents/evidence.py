"""Evidence layer: web + RAG evidence conversion, retrieval, and merging.

Produces :class:`EvidenceItem` dicts (the schema from ``graph/state.py``) so
the output can be stored directly in ``ResearchState["evidence"]``.

No LLM is used here — the merger is pure and fully deterministic.
"""
from __future__ import annotations

import hashlib
from typing import Iterable

from backend.app.graph.state import EvidenceItem
from backend.app.rag.vectorstore import RetrievedChunk, search_knowledge_base

# Sensible default bound for the merged evidence list (callers can override).
DEFAULT_MAX_EVIDENCE_ITEMS = 20


# ── Deterministic IDs ────────────────────────────────────────────────────────

def _evidence_id(*parts) -> str:
    """Build a deterministic, stable evidence id from provenance parts."""
    raw = "|".join("" if p is None else str(p) for p in parts)
    return "E" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _score(item: dict) -> float:
    """Coerce an item's score to float, defaulting to 0.0 when absent/invalid."""
    try:
        return float(item.get("score") or 0.0)
    except (TypeError, ValueError):
        return 0.0


# ── Web evidence conversion ──────────────────────────────────────────────────

def web_results_to_evidence(results: Iterable[dict]) -> list[EvidenceItem]:
    """Convert raw web/search result dicts into web :class:`EvidenceItem` s.

    Expected input shape (Tavily-style): ``{"title", "url", "content", "score"}``.
    Nothing is invented: missing title/url become empty/None, and a missing
    score becomes ``0.0``. Entries that are not dicts, or have no extractable
    text, are skipped.
    """
    items: list[EvidenceItem] = []
    for r in results:
        if not isinstance(r, dict):
            continue
        text = str(r.get("content") or r.get("snippet") or "").strip()
        if not text:
            continue
        url = r.get("url")
        items.append(
            EvidenceItem(
                id=_evidence_id("web", url, text),
                source_type="web",
                text=text,
                title=str(r.get("title") or ""),
                url=url,
                document_id=None,
                page=None,
                chunk_index=None,
                score=_score(r),
            )
        )
    return items


# ── RAG evidence conversion ──────────────────────────────────────────────────

def rag_chunk_to_evidence(chunk: RetrievedChunk) -> EvidenceItem:
    """Convert a RAG retrieval result into a rag :class:`EvidenceItem`.

    Preserves all provenance: source_name -> title, document_id, page
    (page_number), chunk_index, and the similarity score.
    """
    return EvidenceItem(
        id=_evidence_id(
            "rag", chunk.document_id, chunk.chunk_index, chunk.page_number
        ),
        source_type="rag",
        text=chunk.text,
        title=chunk.source_name,
        url=None,
        document_id=chunk.document_id,
        page=chunk.page_number,
        chunk_index=chunk.chunk_index,
        score=float(chunk.score),
    )


# ── RAG retrieval helper ─────────────────────────────────────────────────────

def retrieve_rag_evidence(
    query: str,
    top_k: int | None = None,
    score_threshold: float | None = None,
    document_id: str | None = None,
    vector_store=None,
) -> list[EvidenceItem]:
    """Retrieve RAG evidence for a query via the existing vector store.

    Delegates to ``search_knowledge_base`` (no duplicated embedding/vector
    logic). ``vector_store`` may be injected for tests. Returns ``[]`` when
    nothing relevant is found (RAG is never mandatory).

    Raises:
        ValueError: if the query is empty/blank.
    """
    if not query or not query.strip():
        raise ValueError("query must not be empty")

    results = search_knowledge_base(
        query,
        top_k=top_k,
        score_threshold=score_threshold,
        document_id=document_id,
        vector_store=vector_store,
    )
    return [rag_chunk_to_evidence(r) for r in results]


# ── Evidence merging ─────────────────────────────────────────────────────────

def merge_evidence(
    web_evidence: Iterable[EvidenceItem] | None = None,
    rag_evidence: Iterable[EvidenceItem] | None = None,
    max_items: int | None = None,
) -> list[EvidenceItem]:
    """Combine web + RAG evidence into one deterministic, ranked list.

    - Preserves source_type and all provenance fields (dicts are not rebuilt).
    - Assigns a deterministic id to items that lack one.
    - Removes exact duplicates by id (first occurrence wins).
    - Never removes two different chunks just because their text is similar
      (distinct provenance yields distinct ids).
    - Orders by score (descending, ties broken by id) — fully deterministic.
    - Truncates to ``max_items`` (defaults to a sensible bounded limit).

    Raises:
        ValueError: if ``max_items`` is provided and not > 0.
    """
    limit = DEFAULT_MAX_EVIDENCE_ITEMS if max_items is None else max_items
    if limit <= 0:
        raise ValueError(f"max_items must be > 0, got {max_items}")

    merged: dict[str, EvidenceItem] = {}
    for item in list(web_evidence or []) + list(rag_evidence or []):
        if not isinstance(item, dict):
            continue  # ignore malformed entries
        if not str(item.get("text") or "").strip():
            continue  # ignore empty evidence
        evidence_id = item.get("id") or _evidence_id(
            item.get("source_type", "web"),
            item.get("url"),
            item.get("document_id"),
            item.get("page"),
            item.get("chunk_index"),
            item.get("text"),
        )
        if evidence_id not in merged:
            normalized = dict(item)
            if not item.get("id"):
                normalized["id"] = evidence_id
            merged[evidence_id] = normalized

    ordered = sorted(
        merged.values(),
        key=lambda it: (-_score(it), str(it.get("id", ""))),
    )
    return ordered[:limit]
