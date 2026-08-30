"""Typed state for the research pipeline.

``ResearchState`` is the shared data structure produced and consumed by the
research workflow. Today it is filled in by the sequential pipeline in
``backend.app.main``; in a later phase it becomes the LangGraph state schema
(where reducers will be added for accumulation).
"""
from typing import Literal, TypedDict


class EvidenceItem(TypedDict, total=False):
    """A single piece of evidence (web or RAG) grounding the report."""

    id: str
    source_type: Literal["web", "rag"]
    text: str
    title: str
    url: str | None
    document_id: str | None
    page: int | None
    chunk_index: int | None
    score: float


class FactCheck(TypedDict, total=False):
    """A claim-level fact check produced by the fact checker."""

    claim: str
    verdict: str
    confidence: float
    evidence_refs: list[str]


class Citation(TypedDict, total=False):
    """A single numbered citation in the final report."""

    index: int
    source_type: Literal["web", "rag"]
    title: str
    url: str | None
    document_id: str | None
    page: int | None
    chunk_index: int | None


class RetrievedChunk(TypedDict, total=False):
    """A RAG retrieval hit with its similarity score and stored metadata."""

    text: str
    score: float
    metadata: dict


class DocumentRef(TypedDict, total=False):
    """Reference to a knowledge-base document used during research."""

    document_id: str
    source_name: str
    source_type: str


class ResearchPlan(TypedDict, total=False):
    """The planner's output: research angles and whether RAG should be used."""

    research_angles: list[str]
    use_rag: bool


class ResearchState(TypedDict, total=False):
    """State produced/consumed by the InsightForge research pipeline.

    All fields are optional (``total=False``) so partial state can exist at
    every stage of the workflow.
    """

    # ── Existing fields (Phase 1) ─────────────────────────────────────────
    query: str
    search_results: str
    sources: list[str]
    extracted_information: str
    report: str
    critic_feedback: str
    # Reserved for the fact-checking phase; not populated yet.
    critic_score: int | None
    errors: list[str]

    # ── Phase 2B fields ───────────────────────────────────────────────────
    research_plan: ResearchPlan
    retrieved_chunks: list[RetrievedChunk]
    evidence: list[EvidenceItem]
    claims: list[str]
    fact_checks: list[FactCheck]
    confidence: str
    citations: list[Citation]
    report_draft: str
    documents_used: list[DocumentRef]
    research_rounds: int
