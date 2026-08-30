"""Thin LangGraph-compatible node wrappers around the Phase 2B components.

Each node:
- accepts a ``ResearchState``-compatible dict,
- calls exactly one existing component,
- returns ONLY a partial state update (never mutates the incoming state),
- contains no graph edges / routing / loop logic (those arrive in a later step).

Compatibility notes (deliberately not redesigned here):
- ``research_node`` wraps the existing string-based web research; RAG is only
  invoked when ``research_plan["use_rag"]`` is true.
- The current web research persists only a prose summary + source URL list, so
  ``evidence_node`` builds web evidence from ``sources`` with the available
  extracted/search text (per-source raw text is not retained).
- ``ResearchState`` has no dedicated claims field yet (claim extraction is a
  later step), so ``fact_check_node`` accepts claims explicitly and returns an
  empty list when none are supplied.
"""
from __future__ import annotations

import re

from backend.app.core.config import settings
from backend.app.agents.citation import generate_citations
from backend.app.agents.claim_extractor import extract_claims
from backend.app.agents.confidence import calculate_confidence
from backend.app.agents.critic import critic_chain
from backend.app.agents.evidence import merge_evidence, rag_chunk_to_evidence
from backend.app.agents.fact_checker import fact_check_claims
from backend.app.agents.planner import plan_research
from backend.app.agents.writer import writer_chain
from backend.app.graph.state import ResearchState
from backend.app.rag.vectorstore import RetrievedChunk as VectorRetrievedChunk
from backend.app.tools.web import extract_urls

_SCORE_RE = re.compile(r"Score:\s*(\d+(?:\.\d+)?)\s*/\s*10", re.IGNORECASE)


# ── 1. Plan node ─────────────────────────────────────────────────────────────

def plan_node(state: ResearchState) -> dict:
    """Create a research plan for the query."""
    plan = plan_research(state["query"])
    return {"research_plan": plan}


# ── 2. Research node ─────────────────────────────────────────────────────────

def _default_web_research(query: str, angles: list[str]) -> tuple[str, list[str]]:
    """Run a direct Tavily search (no LLM) and return (text, source URLs).

    A plain tool call is far faster and cheaper than the search agent, which
    needed two LLM round-trips (decide-to-search + summarize). On the free
    tier every extra LLM call risks a 30-50s rate-limit wait, so dropping the
    agent here is the single biggest speedup available.
    """
    from backend.app.tools.web import web_search

    text = web_search.invoke({"query": query})
    return text, extract_urls(text)


def _to_state_chunk(chunk: VectorRetrievedChunk) -> dict:
    """Convert a vector-store RetrievedChunk into the state RetrievedChunk shape."""
    return {
        "text": chunk.text,
        "score": chunk.score,
        "metadata": {
            "document_id": chunk.document_id,
            "source_name": chunk.source_name,
            "source_type": chunk.source_type,
            "chunk_id": chunk.chunk_id,
            "chunk_index": chunk.chunk_index,
            "total_chunks": chunk.total_chunks,
            "page_number": chunk.page_number,
        },
    }


def _doc_refs_from_chunks(chunks: list[VectorRetrievedChunk]) -> list[dict]:
    seen: set[str] = set()
    refs: list[dict] = []
    for c in chunks:
        if c.document_id and c.document_id not in seen:
            seen.add(c.document_id)
            refs.append({
                "document_id": c.document_id,
                "source_name": c.source_name,
                "source_type": c.source_type,
            })
    return refs


def _default_rag_retrieval(query: str) -> tuple[list[dict], list[dict]]:
    """Run RAG retrieval and return (state-typed chunks, document refs)."""
    from backend.app.rag.vectorstore import search_knowledge_base

    results = search_knowledge_base(query)
    return [_to_state_chunk(r) for r in results], _doc_refs_from_chunks(results)


def research_node(state: ResearchState, search_fn=None, rag_fn=None) -> dict:
    """Run web research (and RAG only when the plan says ``use_rag``).

    ``search_fn(query, angles) -> (text, urls)`` and
    ``rag_fn(query) -> (chunks, document_refs)`` may be injected for tests.
    """
    query = state["query"]
    plan = state.get("research_plan") or {}
    use_rag = bool(plan.get("use_rag"))

    search_fn = search_fn or _default_web_research
    search_text, urls = search_fn(query, plan.get("research_angles") or [])

    update = {"search_results": search_text, "sources": urls}
    if use_rag:
        rag_fn = rag_fn or _default_rag_retrieval
        chunks, doc_refs = rag_fn(query)
        update["retrieved_chunks"] = chunks
        update["documents_used"] = doc_refs
    return update


# ── 3. Evidence node ─────────────────────────────────────────────────────────

def _web_evidence_from_state(state: ResearchState) -> list[dict]:
    """Minimal adapter: string-based web research -> web EvidenceItems."""
    sources = state.get("sources") or []
    text = (
        state.get("extracted_information") or state.get("search_results") or ""
    ).strip()
    if not sources or not text:
        return []
    # The same summary text is shared across every source URL; cap each copy
    # so it is not duplicated per source and inflates every downstream prompt.
    text = text[: settings.evidence_max_chars]
    return [
        {
            "source_type": "web",
            "text": text,
            "title": url,
            "url": url,
            "document_id": None,
            "page": None,
            "chunk_index": None,
            "score": 0.0,
        }
        for url in sources
    ]


def _state_chunks_to_rag_evidence(chunks) -> list[dict]:
    """Convert state-typed retrieved chunks into rag EvidenceItems."""
    items: list[dict] = []
    for chunk in chunks or []:
        if not isinstance(chunk, dict):
            continue
        meta = chunk.get("metadata") or {}
        vector_chunk = VectorRetrievedChunk(
            text=chunk.get("text", ""),
            score=_to_float(chunk.get("score")) or 0.0,
            document_id=meta.get("document_id", ""),
            source_name=meta.get("source_name", ""),
            source_type=meta.get("source_type", ""),
            chunk_id=meta.get("chunk_id", ""),
            chunk_index=meta.get("chunk_index", 0),
            total_chunks=meta.get("total_chunks", 0),
            page_number=meta.get("page_number"),
        )
        items.append(rag_chunk_to_evidence(vector_chunk))
    return items


def evidence_node(state: ResearchState) -> dict:
    """Merge web + RAG evidence from the research output into ``evidence``."""
    web = _web_evidence_from_state(state)
    rag = _state_chunks_to_rag_evidence(state.get("retrieved_chunks"))
    merged = merge_evidence(web, rag)
    return {"evidence": merged}


# ── 4. Claim extraction node ─────────────────────────────────────────────────

def _research_text_from_state(state: ResearchState) -> str:
    """Assemble the raw research text from the state's research fields."""
    parts: list[str] = []
    for key in ("search_results", "extracted_information"):
        value = state.get(key)
        if value and str(value).strip():
            parts.append(str(value).strip())
    return "\n\n".join(parts)


def claim_extraction_node(state: ResearchState) -> dict:
    """Extract checkable claims from the research material and evidence."""
    claims = extract_claims(
        research=_research_text_from_state(state),
        evidence=state.get("evidence") or [],
    )
    return {"claims": claims}


# ── 5. Fact check node ───────────────────────────────────────────────────────

def fact_check_node(state: ResearchState, claims=None) -> dict:
    """Fact-check claims against the state's evidence.

    Claims are read from ``state["claims"]`` (produced by the claim extraction
    node) unless explicitly supplied via the ``claims`` parameter. Returns
    empty fact checks when no claims are available.
    """
    if claims is None:
        claims = state.get("claims") or []
    if not claims:
        return {"fact_checks": []}
    checks = fact_check_claims(list(claims), state.get("evidence") or [], batch=True)
    return {"fact_checks": checks}


# ── 6. Citation node ─────────────────────────────────────────────────────────

def citation_node(state: ResearchState) -> dict:
    """Generate deterministic citations from evidence + fact checks."""
    citations = generate_citations(
        state.get("evidence") or [],
        state.get("fact_checks"),
    )
    return {"citations": citations}


# ── 7. Confidence node ───────────────────────────────────────────────────────

def confidence_node(state: ResearchState) -> dict:
    """Compute the confidence label only (routing belongs to the graph)."""
    confidence = calculate_confidence(
        state.get("evidence") or [],
        state.get("fact_checks"),
        state.get("citations"),
    )
    return {"confidence": confidence}


# ── 8. Writer node ───────────────────────────────────────────────────────────

def _evidence_to_research_text(evidence) -> str:
    """Assemble the evidence list into the writer's ``research`` text block."""
    blocks: list[str] = []
    for item in evidence or []:
        if not isinstance(item, dict):
            continue
        eid = item.get("id", "")
        source = item.get("source_type", "")
        title = item.get("title", "")
        text = item.get("text", "")
        blocks.append(f"[{eid}] ({source} — {title})\n{text}")
    return "\n\n".join(blocks)


def _format_claims(claims) -> str:
    lines = []
    for claim in claims or []:
        if isinstance(claim, str) and claim.strip():
            lines.append(f"- {claim.strip()}")
    return "\n".join(lines)


def _format_fact_checks(fact_checks) -> str:
    lines = []
    for fc in fact_checks or []:
        if not isinstance(fc, dict):
            continue
        lines.append(
            f"- claim: {fc.get('claim', '')} | verdict: {fc.get('verdict', '')} "
            f"| confidence: {fc.get('confidence', '')} | evidence: {fc.get('evidence_refs', [])}"
        )
    return "\n".join(lines)


def _format_citations(citations) -> str:
    lines = []
    for c in citations or []:
        if not isinstance(c, dict):
            continue
        title = c.get("title", "")
        ref = c.get("url") or c.get("document_id") or title
        page = c.get("page")
        suffix = f" (page {page})" if page is not None else ""
        lines.append(
            f"[{c.get('index', '?')}] ({c.get('source_type', '')}) {title} — {ref}{suffix}"
        )
    return "\n".join(lines)


def _build_writer_research(state: ResearchState) -> str:
    """Assemble the writer's ``research`` payload from the verified state.

    Keeps the evidence section and appends the verification metadata (claims,
    fact checks, citations, confidence) so the writer can produce a grounded,
    citation-aware report — without changing the writer chain contract.
    """
    sections: list[str] = []

    evidence_text = _evidence_to_research_text(state.get("evidence") or [])
    if evidence_text:
        sections.append(f"EVIDENCE:\n{evidence_text}")

    claims_text = _format_claims(state.get("claims"))
    if claims_text:
        sections.append(f"CLAIMS:\n{claims_text}")

    fact_checks_text = _format_fact_checks(state.get("fact_checks"))
    if fact_checks_text:
        sections.append(f"FACT CHECKS:\n{fact_checks_text}")

    citations_text = _format_citations(state.get("citations"))
    if citations_text:
        sections.append(f"CITATIONS:\n{citations_text}")

    confidence = state.get("confidence")
    if confidence:
        sections.append(f"CONFIDENCE: {confidence}")

    return "\n\n".join(sections)


def writer_node(state: ResearchState) -> dict:
    """Draft the report from the verified research state (existing chain)."""
    research = _build_writer_research(state)
    report = writer_chain.invoke({"topic": state["query"], "research": research})
    return {"report_draft": report}


# ── 9. Critic node ───────────────────────────────────────────────────────────

def _extract_critic_score(feedback: str) -> int | None:
    """Parse ``Score: X/10`` from the critic feedback (or None)."""
    match = _SCORE_RE.search(str(feedback))
    if not match:
        return None
    try:
        return int(float(match.group(1)))
    except ValueError:
        return None


def critic_node(state: ResearchState) -> dict:
    """Review the draft report with the existing critic chain.

    Skipped (no LLM call) when ``settings.run_critic`` is False — the default
    on the free tier, where the critic's report re-read (~2000+ tokens) is the
    largest non-essential cost. Returns an empty update so the graph state is
    unchanged.
    """
    if not settings.run_critic:
        return {}
    report = state.get("report_draft") or state.get("report") or ""
    feedback = critic_chain.invoke({"report": report})
    return {"critic_feedback": feedback, "critic_score": _extract_critic_score(feedback)}


# ── Shared helper ────────────────────────────────────────────────────────────

def _to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
