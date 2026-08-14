"""Unit tests for deterministic citation generation.

No LLM/API calls — all inputs are fake evidence/fact-check dicts, and tests
verify the LLM is never invoked.
"""
import pytest

from backend.app.agents.citation import (
    DEFAULT_MAX_CITATIONS,
    generate_citations,
)

CITATION_KEYS = {"index", "source_type", "title", "url", "document_id", "page", "chunk_index"}


class FakeChain:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def invoke(self, inputs):
        self.calls.append(inputs)
        if self.error is not None:
            raise self.error
        return inputs


def make_evidence(
    eid="E1",
    source_type="web",
    title="Example",
    text="some text",
    url="https://example.com",
    document_id=None,
    page=None,
    chunk_index=None,
    score=0.5,
):
    return {
        "id": eid,
        "source_type": source_type,
        "text": text,
        "title": title,
        "url": url,
        "document_id": document_id,
        "page": page,
        "chunk_index": chunk_index,
        "score": score,
    }


def make_fact_check(verdict="supported", refs=("E1",)):
    return {"claim": "c", "verdict": verdict, "confidence": 0.9, "evidence_refs": list(refs)}


# ── Basic behavior ───────────────────────────────────────────────────────────

def test_empty_evidence_returns_empty():
    assert generate_citations([]) == []
    assert generate_citations(None) == []


def test_single_web_evidence():
    citations = generate_citations([make_evidence(url="https://a.com")])
    assert len(citations) == 1
    c = citations[0]
    assert set(c.keys()) == CITATION_KEYS
    assert c["index"] == 1
    assert c["source_type"] == "web"
    assert c["title"] == "Example"
    assert c["url"] == "https://a.com"
    assert c["document_id"] is None
    assert c["page"] is None
    assert c["chunk_index"] is None


def test_single_rag_evidence():
    citations = generate_citations(
        [make_evidence(eid="E2", source_type="rag", url=None, document_id="doc-1", page=4, chunk_index=2)]
    )
    assert len(citations) == 1
    c = citations[0]
    assert c["source_type"] == "rag"
    assert c["url"] is None
    assert c["document_id"] == "doc-1"
    assert c["page"] == 4
    assert c["chunk_index"] == 2


# ── Provenance ───────────────────────────────────────────────────────────────

def test_web_provenance_preserved():
    c = generate_citations([make_evidence(title="Alpha", url="https://a.com")])[0]
    assert c["title"] == "Alpha"
    assert c["url"] == "https://a.com"
    assert c["document_id"] is None and c["page"] is None and c["chunk_index"] is None


def test_rag_provenance_preserved():
    c = generate_citations(
        [make_evidence(source_type="rag", title="report.pdf", url=None, document_id="doc-9", page=7, chunk_index=5)]
    )[0]
    assert c["title"] == "report.pdf"
    assert c["document_id"] == "doc-9"
    assert c["page"] == 7
    assert c["chunk_index"] == 5


def test_missing_optional_metadata_preserved_as_none():
    web = generate_citations([make_evidence(url=None, title="T")])[0]
    assert web["url"] is None
    rag = generate_citations(
        [make_evidence(source_type="rag", url=None, document_id="doc-1", page=None, chunk_index=None)]
    )[0]
    assert rag["page"] is None
    assert rag["chunk_index"] is None
    no_doc = generate_citations(
        [make_evidence(source_type="rag", url=None, document_id=None, page=1, chunk_index=1)]
    )[0]
    assert no_doc["document_id"] is None


def test_web_empty_string_url_becomes_none():
    c = generate_citations([make_evidence(url="")])[0]
    assert c["url"] is None


# ── Indexes ──────────────────────────────────────────────────────────────────

def test_sequential_indexes():
    evidence = [
        make_evidence(eid="E1", url="https://a.com", score=0.3),
        make_evidence(eid="E2", url="https://b.com", score=0.6),
        make_evidence(eid="E3", url="https://c.com", score=0.9),
    ]
    citations = generate_citations(evidence)
    assert [c["index"] for c in citations] == [1, 2, 3]


def test_indexes_always_restart_at_one():
    citations = generate_citations(
        [make_evidence(eid="E1", url="https://a.com"), make_evidence(eid="E2", url="https://b.com")]
    )
    assert [c["index"] for c in citations] == [1, 2]


# ── Determinism & ordering ───────────────────────────────────────────────────

def test_same_input_different_order_same_output():
    evidence = [
        make_evidence(eid="E1", url="https://a.com", score=0.3),
        make_evidence(eid="E2", url="https://b.com", score=0.9),
        make_evidence(eid="E3", url="https://c.com", score=0.6),
    ]
    a = generate_citations(evidence)
    b = generate_citations(list(reversed(evidence)))
    assert a == b
    assert [c["url"] for c in a] == ["https://b.com", "https://c.com", "https://a.com"]


def test_determinism_across_repeated_calls():
    evidence = [make_evidence(eid="E1", url="https://a.com"), make_evidence(eid="E2", url="https://b.com")]
    assert generate_citations(evidence) == generate_citations(evidence)


# ── Deduplication ────────────────────────────────────────────────────────────

def test_duplicate_web_evidence_removed():
    evidence = [
        make_evidence(eid="E1", url="https://same.com", score=0.5),
        make_evidence(eid="E2", url="https://same.com", score=0.9),
    ]
    citations = generate_citations(evidence)
    assert len(citations) == 1
    assert citations[0]["url"] == "https://same.com"


def test_identical_rag_text_different_provenance_both_preserved():
    evidence = [
        make_evidence(eid="E1", source_type="rag", url=None, text="same words", document_id="doc-1", chunk_index=0, score=0.8),
        make_evidence(eid="E2", source_type="rag", url=None, text="same words", document_id="doc-2", chunk_index=0, score=0.6),
    ]
    citations = generate_citations(evidence)
    assert len(citations) == 2
    assert {c["document_id"] for c in citations} == {"doc-1", "doc-2"}


# ── Fact-check integration ───────────────────────────────────────────────────

def test_fact_check_refs_prioritize_referenced_evidence():
    evidence = [
        make_evidence(eid="E1", url="https://a.com", score=0.9),
        make_evidence(eid="E2", url="https://b.com", score=0.1),
    ]
    citations = generate_citations(evidence, fact_checks=[make_fact_check("supported", ["E2"])])
    assert [c["url"] for c in citations] == ["https://b.com", "https://a.com"]


def test_supported_fact_check_references():
    evidence = [make_evidence(eid="E1", url="https://a.com"), make_evidence(eid="E2", url="https://b.com")]
    citations = generate_citations(evidence, fact_checks=[make_fact_check("supported", ["E1"])])
    assert citations[0]["url"] == "https://a.com"


def test_contradicted_fact_check_references():
    evidence = [make_evidence(eid="E1", url="https://a.com"), make_evidence(eid="E2", url="https://b.com")]
    citations = generate_citations(evidence, fact_checks=[make_fact_check("contradicted", ["E2"])])
    assert citations[0]["url"] == "https://b.com"


def test_insufficient_fact_check_handling():
    evidence = [
        make_evidence(eid="E1", url="https://a.com", score=0.9),
        make_evidence(eid="E2", url="https://b.com", score=0.1),
    ]
    citations = generate_citations(evidence, fact_checks=[make_fact_check("insufficient", ["E2"])])
    # insufficient-referenced evidence ranks above unreferenced evidence
    assert [c["url"] for c in citations] == ["https://b.com", "https://a.com"]


def test_hallucinated_evidence_refs_ignored():
    evidence = [make_evidence(eid="E1", url="https://a.com")]
    citations = generate_citations(evidence, fact_checks=[make_fact_check("supported", ["FAKE123"])])
    assert len(citations) == 1
    assert citations[0]["url"] == "https://a.com"


def test_unknown_references_never_become_citations():
    evidence = [make_evidence(eid="E1", url="https://a.com")]
    citations = generate_citations(evidence, fact_checks=[make_fact_check("supported", ["GHOST"])])
    assert len(citations) == 1
    assert all(c["url"] != "GHOST" for c in citations)


def test_no_fact_checks_evidence_only():
    evidence = [
        make_evidence(eid="E1", url="https://a.com", score=0.2),
        make_evidence(eid="E2", url="https://b.com", score=0.9),
    ]
    citations = generate_citations(evidence)
    assert [c["url"] for c in citations] == ["https://b.com", "https://a.com"]


# ── max_citations ────────────────────────────────────────────────────────────

def test_max_citations_limit():
    evidence = [make_evidence(eid=f"E{i}", url=f"https://{i}.com", score=i) for i in range(5)]
    citations = generate_citations(evidence, max_citations=2)
    assert len(citations) == 2
    assert [c["index"] for c in citations] == [1, 2]


def test_default_limit_applies():
    evidence = [make_evidence(eid=f"E{i}", url=f"https://{i}.com", score=i) for i in range(30)]
    citations = generate_citations(evidence)
    assert len(citations) == DEFAULT_MAX_CITATIONS


def test_max_citations_zero_raises():
    with pytest.raises(ValueError, match="max_citations"):
        generate_citations([make_evidence()], max_citations=0)


def test_max_citations_negative_raises():
    with pytest.raises(ValueError, match="max_citations"):
        generate_citations([make_evidence()], max_citations=-1)


# ── Malformed / invalid input handling ───────────────────────────────────────

def test_invalid_source_type_skipped():
    evidence = [
        make_evidence(eid="E1", source_type="doc", url="https://x.com"),
        make_evidence(eid="E2", url="https://ok.com"),
    ]
    citations = generate_citations(evidence)
    assert len(citations) == 1
    assert citations[0]["url"] == "https://ok.com"


def test_malformed_evidence_skipped():
    evidence = [
        "not a dict",
        42,
        {"source_type": "web", "url": "https://noid.com"},  # missing id
        make_evidence(eid="E1", url="https://ok.com"),
    ]
    citations = generate_citations(evidence)
    assert len(citations) == 1
    assert citations[0]["url"] == "https://ok.com"


# ── Schema / LLM-free ────────────────────────────────────────────────────────

def test_full_citation_schema_validation():
    citations = generate_citations(
        [
            make_evidence(eid="E1", url="https://a.com"),
            make_evidence(eid="E2", source_type="rag", url=None, document_id="d", page=1, chunk_index=0),
        ]
    )
    assert len(citations) == 2
    for c in citations:
        assert set(c.keys()) == CITATION_KEYS


def test_no_llm_call_deterministic_path():
    chain = FakeChain(error=AssertionError("chain must not be called"))
    generate_citations(
        [make_evidence(eid="E1", url="https://a.com")],
        fact_checks=[make_fact_check("supported", ["E1"])],
        chain=chain,
        fallback_chain=chain,
    )
    assert chain.calls == []
