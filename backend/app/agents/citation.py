"""Citation generation — deterministic, evidence-derived citations.

Converts :class:`EvidenceItem` (optionally guided by :class:`FactCheck`
references) into the :class:`Citation` schema from ``graph/state.py``.

This implementation is fully deterministic and NEVER calls an LLM: citation
metadata is copied directly from evidence, so an LLM would only be copying
data. ``chain`` / ``fallback_chain`` are accepted for API compatibility and
future LLM-assisted selection, but are unused here.
"""
from __future__ import annotations

from typing import Iterable

from backend.app.graph.state import Citation, EvidenceItem, FactCheck

DEFAULT_MAX_CITATIONS = 20

_VALID_SOURCE_TYPES = ("web", "rag")


# ── Public API ───────────────────────────────────────────────────────────────

def generate_citations(
    evidence: Iterable[EvidenceItem] | None,
    fact_checks: list[FactCheck] | None = None,
    max_citations: int | None = None,
    chain=None,
    fallback_chain=None,
) -> list[Citation]:
    """Generate deterministic citations from evidence (+ optional fact checks).

    Args:
        evidence: :class:`EvidenceItem` dicts. Empty/None yields ``[]``.
        fact_checks: Optional fact checks whose valid ``evidence_refs`` raise
            the priority of the referenced evidence.
        max_citations: Upper bound on returned citations (default 20).
        chain / fallback_chain: Reserved for future LLM-assisted selection;
            unused by the deterministic implementation.

    Returns:
        List of :class:`Citation` with sequential indexes starting at 1.

    Raises:
        ValueError: if ``max_citations`` is provided and not > 0.
    """
    limit = DEFAULT_MAX_CITATIONS if max_citations is None else max_citations
    if limit <= 0:
        raise ValueError(f"max_citations must be > 0, got {max_citations}")

    items = _normalize_evidence(evidence)
    if not items:
        return []

    support_ids, insufficient_ids = _fact_check_reference_sets(fact_checks)

    # Deduplicate by provenance, keeping the best item per source.
    best: dict[tuple, dict] = {}
    for item in items:
        key = _provenance_key(item)
        current = best.get(key)
        if current is None or _is_better(item, current):
            best[key] = item

    def _priority(item: dict) -> int:
        eid = item.get("id")
        if eid in support_ids:
            return 0
        if eid in insufficient_ids:
            return 1
        return 2

    ordered = sorted(
        best.values(),
        key=lambda it: (_priority(it), -_score(it), str(it.get("id", ""))),
    )
    selected = ordered[:limit]

    return [
        _to_citation(item, index=position)
        for position, item in enumerate(selected, start=1)
    ]


# ── Normalization & validation ───────────────────────────────────────────────

def _normalize_evidence(evidence: Iterable[EvidenceItem] | None) -> list[dict]:
    """Keep only usable evidence; consistently skip malformed entries."""
    normalized: list[dict] = []
    for item in evidence or []:
        if not isinstance(item, dict):
            continue  # malformed: not a dict
        if not item.get("id"):
            continue  # no id -> cannot be cited or referenced
        if item.get("source_type") not in _VALID_SOURCE_TYPES:
            continue  # invalid source type
        normalized.append(item)
    return normalized


def _fact_check_reference_sets(
    fact_checks: list[FactCheck] | None,
) -> tuple[set[str], set[str]]:
    """Collect referenced evidence IDs by verdict tier.

    Returns (supported_or_contradicted_ids, insufficient_ids). Hallucinated
    IDs are harmless: they can never match a real evidence id downstream.
    """
    support: set[str] = set()
    insufficient: set[str] = set()
    for fc in fact_checks or []:
        if not isinstance(fc, dict):
            continue
        refs = fc.get("evidence_refs")
        if not isinstance(refs, list):
            continue
        verdict = fc.get("verdict")
        if verdict in ("supported", "contradicted"):
            target = support
        elif verdict == "insufficient":
            target = insufficient
        else:
            continue
        target.update(r for r in refs if isinstance(r, str))
    return support, insufficient


# ── Provenance & ordering helpers ────────────────────────────────────────────

def _provenance_key(item: dict) -> tuple:
    """Deterministic identity of an evidence source (for deduplication).

    - web: the URL identifies the source (fall back to the evidence id when
      no URL is available so distinct items are not collapsed).
    - rag: (document_id, page, chunk_index) identifies the chunk. Two chunks
      with identical text but different provenance are NOT collapsed.
    """
    if item.get("source_type") == "web":
        url = item.get("url")
        if url:
            return ("web", url)
        return ("web", "__id__", item.get("id", ""))
    document_id = item.get("document_id")
    if document_id:
        return ("rag", document_id, item.get("page"), item.get("chunk_index"))
    return ("rag", "__id__", item.get("id", ""))


def _is_better(candidate: dict, current: dict) -> bool:
    """Prefer higher score; ties broken by lexicographically smaller id."""
    if _score(candidate) != _score(current):
        return _score(candidate) > _score(current)
    return str(candidate.get("id", "")) < str(current.get("id", ""))


def _score(item: dict) -> float:
    try:
        return float(item.get("score") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _to_citation(item: dict, index: int) -> Citation:
    """Build a Citation strictly from evidence metadata (never invented)."""
    if item.get("source_type") == "web":
        return Citation(
            index=index,
            source_type="web",
            title=item.get("title", ""),
            url=item.get("url") or None,
            document_id=None,
            page=None,
            chunk_index=None,
        )
    return Citation(
        index=index,
        source_type="rag",
        title=item.get("title", ""),
        url=None,
        document_id=item.get("document_id") or None,
        page=item.get("page"),
        chunk_index=item.get("chunk_index"),
    )
