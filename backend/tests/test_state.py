"""Unit tests for the extended ResearchState and its TypedDict schemas."""
from typing import get_type_hints

from backend.app.graph.state import (
    Citation,
    DocumentRef,
    EvidenceItem,
    FactCheck,
    ResearchPlan,
    ResearchState,
    RetrievedChunk,
)

PHASE_1_FIELDS = {
    "query",
    "search_results",
    "sources",
    "extracted_information",
    "report",
    "critic_feedback",
    "critic_score",
    "errors",
}

PHASE_2B_FIELDS = {
    "research_plan",
    "retrieved_chunks",
    "evidence",
    "claims",
    "fact_checks",
    "confidence",
    "citations",
    "report_draft",
    "documents_used",
    "research_rounds",
}

ALL_FIELDS = PHASE_1_FIELDS | PHASE_2B_FIELDS


# ── ResearchState field presence ─────────────────────────────────────────────

def test_existing_state_fields_still_present():
    assert PHASE_1_FIELDS <= set(ResearchState.__annotations__)


def test_new_state_fields_present():
    assert PHASE_2B_FIELDS <= set(ResearchState.__annotations__)


def test_research_state_has_exactly_expected_fields():
    assert set(ResearchState.__annotations__) == ALL_FIELDS


def test_research_state_remains_total_false():
    assert ResearchState.__required_keys__ == frozenset()
    assert set(ResearchState.__optional_keys__) == ALL_FIELDS


# ── EvidenceItem ─────────────────────────────────────────────────────────────

def test_evidence_item_web_variant():
    item = EvidenceItem(
        id="E1",
        source_type="web",
        text="Some evidence text",
        title="Example source",
        url="https://example.com",
        document_id=None,
        page=None,
        chunk_index=None,
        score=0.9,
    )
    assert item["id"] == "E1"
    assert item["source_type"] == "web"
    assert item["text"] == "Some evidence text"
    assert item["url"] == "https://example.com"
    assert item["score"] == 0.9


def test_evidence_item_rag_variant():
    item = EvidenceItem(
        id="E2",
        source_type="rag",
        text="Chunk content",
        title="report.pdf",
        url=None,
        document_id="doc-123",
        page=4,
        chunk_index=2,
        score=0.77,
    )
    assert item["source_type"] == "rag"
    assert item["document_id"] == "doc-123"
    assert item["page"] == 4
    assert item["chunk_index"] == 2


def test_evidence_item_optional_provenance_fields_default_to_none():
    item = EvidenceItem(id="E3", source_type="web", text="x", title="t", score=0.5)
    assert item.get("url") is None
    assert item.get("document_id") is None
    assert item.get("page") is None
    assert item.get("chunk_index") is None


def test_evidence_source_type_is_literal_web_or_rag():
    hints = get_type_hints(EvidenceItem)
    assert hints["source_type"].__args__ == ("web", "rag")


# ── FactCheck ────────────────────────────────────────────────────────────────

def test_fact_check_valid_instance():
    fc = FactCheck(
        claim="The sky is blue",
        verdict="supported",
        confidence=0.95,
        evidence_refs=["E1", "E3"],
    )
    assert fc["claim"] == "The sky is blue"
    assert fc["verdict"] == "supported"
    assert fc["confidence"] == 0.95
    assert fc["evidence_refs"] == ["E1", "E3"]


# ── Citation ─────────────────────────────────────────────────────────────────

def test_citation_valid_instance():
    c = Citation(
        index=1,
        source_type="rag",
        title="report.pdf",
        url=None,
        document_id="doc-123",
        page=4,
        chunk_index=2,
    )
    assert c["index"] == 1
    assert c["source_type"] == "rag"
    assert c["title"] == "report.pdf"
    assert c["document_id"] == "doc-123"
    assert c["page"] == 4
    assert c["chunk_index"] == 2


def test_citation_source_type_is_literal_web_or_rag():
    hints = get_type_hints(Citation)
    assert hints["source_type"].__args__ == ("web", "rag")


# ── RetrievedChunk / DocumentRef / ResearchPlan ──────────────────────────────

def test_retrieved_chunk_valid_instance():
    rc = RetrievedChunk(
        text="chunk text",
        score=0.82,
        metadata={"document_id": "doc-1", "source_name": "a.txt", "page_number": None},
    )
    assert rc["text"] == "chunk text"
    assert rc["score"] == 0.82
    assert rc["metadata"]["source_name"] == "a.txt"


def test_document_ref_valid_instance():
    dr = DocumentRef(document_id="doc-1", source_name="a.pdf", source_type="pdf")
    assert dr["document_id"] == "doc-1"
    assert dr["source_name"] == "a.pdf"
    assert dr["source_type"] == "pdf"


def test_research_plan_valid_instance():
    plan = ResearchPlan(research_angles=["angle one", "angle two"], use_rag=True)
    assert plan["research_angles"] == ["angle one", "angle two"]
    assert plan["use_rag"] is True


# ── Full ResearchState ───────────────────────────────────────────────────────

def test_full_research_state_instance():
    state = ResearchState(
        query="Quantum computing",
        search_results="...",
        sources=["https://a.com"],
        extracted_information="...",
        report="...",
        critic_feedback="...",
        critic_score=7,
        errors=[],
        research_plan=ResearchPlan(research_angles=["a"], use_rag=True),
        retrieved_chunks=[RetrievedChunk(text="t", score=0.5, metadata={})],
        evidence=[EvidenceItem(id="E1", source_type="web", text="t", title="T", score=0.9)],
        fact_checks=[FactCheck(claim="c", verdict="supported", confidence=0.9, evidence_refs=["E1"])],
        confidence="high",
        citations=[Citation(index=1, source_type="web", title="T", url="https://a.com")],
        report_draft="draft",
        documents_used=[DocumentRef(document_id="d", source_name="n", source_type="txt")],
        research_rounds=1,
    )
    assert state["query"] == "Quantum computing"
    assert state["critic_score"] == 7
    assert state["research_plan"]["use_rag"] is True
    assert state["retrieved_chunks"][0]["text"] == "t"
    assert state["evidence"][0]["id"] == "E1"
    assert state["fact_checks"][0]["verdict"] == "supported"
    assert state["confidence"] == "high"
    assert state["citations"][0]["index"] == 1
    assert state["report_draft"] == "draft"
    assert state["documents_used"][0]["source_name"] == "n"
    assert state["research_rounds"] == 1


def test_minimal_research_state_still_valid():
    # Phase 1 style construction must keep working with the extended state.
    state = ResearchState(query="topic", errors=[])
    assert state == {"query": "topic", "errors": []}
