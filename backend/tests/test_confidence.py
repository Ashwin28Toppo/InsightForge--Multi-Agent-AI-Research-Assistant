"""Unit tests for confidence scoring and research routing.

Pure arithmetic — no LLM/API calls.
"""
import pytest

from backend.app.agents.confidence import (
    calculate_confidence,
    confidence_score,
    route_research,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def ev(eid="E1", score=0.8, source_type="web", url="https://a.com"):
    return {
        "id": eid, "source_type": source_type, "text": "t", "title": "T",
        "url": url, "document_id": None, "page": None, "chunk_index": None,
        "score": score,
    }


def fc(verdict="supported", confidence=0.9, refs=("E1",)):
    return {"claim": "c", "verdict": verdict, "confidence": confidence, "evidence_refs": list(refs)}


def cit(index=1):
    return {"index": index, "source_type": "web", "title": "T", "url": "https://a.com",
            "document_id": None, "page": None, "chunk_index": None}


# ── No evidence ──────────────────────────────────────────────────────────────

def test_no_evidence_is_low():
    assert calculate_confidence([]) == "low"
    assert confidence_score([]) == 0.0


def test_no_evidence_no_fact_checks_is_low():
    assert calculate_confidence([], [], []) == "low"


def test_no_evidence_with_fact_checks_still_low():
    assert calculate_confidence([], [fc()], [cit()]) == "low"


# ── Fact-check verdicts ──────────────────────────────────────────────────────

def test_supported_claim_with_strong_confidence():
    score = confidence_score([ev(score=0.8)], [fc("supported", 0.9)], [cit()])
    assert score == pytest.approx(0.9125)
    assert calculate_confidence([ev(score=0.8)], [fc("supported", 0.9)], [cit()]) == "high"


def test_contradicted_claim_reduces_confidence():
    score = confidence_score([ev(score=0.8)], [fc("contradicted", 0.9)], [cit()])
    assert score == pytest.approx(0.4175)
    assert calculate_confidence([ev(score=0.8)], [fc("contradicted", 0.9)], [cit()]) == "low"


def test_insufficient_claim_never_high():
    score = confidence_score([ev(score=0.9)], [fc("insufficient", 0.9)], [cit()])
    assert score == pytest.approx(0.695)
    assert calculate_confidence([ev(score=0.9)], [fc("insufficient", 0.9)], [cit()]) == "medium"


def test_multiple_supported_claims_high():
    evidence = [ev(eid="E1", score=0.9), ev(eid="E2", score=0.9)]
    checks = [fc("supported", 0.9, ["E1"]), fc("supported", 0.8, ["E2"])]
    citations = [cit(1), cit(2)]
    assert calculate_confidence(evidence, checks, citations) == "high"


def test_mixed_supported_and_contradicted_medium():
    evidence = [ev(eid="E1", score=0.7), ev(eid="E2", score=0.7)]
    checks = [fc("supported", 0.8, ["E1"]), fc("contradicted", 0.6, ["E2"])]
    citations = [cit(1), cit(2)]
    assert calculate_confidence(evidence, checks, citations) == "medium"


# ── Evidence / citations interplay ───────────────────────────────────────────

def test_strong_evidence_supported_citations_high():
    evidence = [ev(score=0.95)]
    checks = [fc("supported", 0.95)]
    assert calculate_confidence(evidence, checks, [cit()]) == "high"


def test_weak_evidence_prevents_high():
    score = confidence_score([ev(score=0.1)], [fc("supported", 0.9)], [cit()])
    assert score == pytest.approx(0.7025)
    assert calculate_confidence([ev(score=0.1)], [fc("supported", 0.9)], [cit()]) == "medium"


def test_evidence_without_fact_checks_cannot_be_high():
    evidence = [ev(score=1.0)]
    score = confidence_score(evidence, [], [cit()])
    assert score == pytest.approx(0.725)
    assert calculate_confidence(evidence, [], [cit()]) == "medium"


def test_empty_fact_checks_same_as_missing():
    evidence = [ev(score=1.0)]
    assert confidence_score(evidence, []) == confidence_score(evidence, None)


def test_empty_citations_still_deterministic():
    score = confidence_score([ev(score=0.8)], [fc("supported", 0.9)], [])
    assert score == pytest.approx(0.7625)
    assert 0.0 <= score <= 1.0


def test_citation_coverage_increases_score():
    evidence = [ev(eid="E1", score=0.8), ev(eid="E2", score=0.8)]
    checks = [fc("supported", 0.9, ["E1", "E2"])]
    partial = confidence_score(evidence, checks, [cit(1)])            # 1/2 coverage
    full = confidence_score(evidence, checks, [cit(1), cit(2)])       # 2/2 coverage
    assert full > partial


def test_strong_evidence_scores_high():
    score = confidence_score([ev(score=0.95)], [fc("supported", 0.95)], [cit()])
    assert score >= 0.75


# ── Score invariants ─────────────────────────────────────────────────────────

def test_score_always_in_01():
    cases = [
        ([ev(score=0.8)], [fc("supported", 0.9)], [cit()]),
        ([ev(score=-5.0)], [fc("contradicted", 3.0)], [cit()]),
        ([ev(score=99.0)], [fc("supported", 99.0)], []),
        ([], [], []),
    ]
    for evidence, checks, citations in cases:
        score = confidence_score(evidence, checks, citations)
        assert 0.0 <= score <= 1.0


def test_deterministic_repeated_calls():
    args = ([ev(score=0.8)], [fc("supported", 0.9)], [cit()])
    assert confidence_score(*args) == confidence_score(*args)
    assert calculate_confidence(*args) == calculate_confidence(*args)


def test_input_order_does_not_affect_score():
    evidence = [ev(eid="E1", score=0.8), ev(eid="E2", score=0.6), ev(eid="E3", score=0.9)]
    checks = [fc("supported", 0.9, ["E1"]), fc("insufficient", 0.5, ["E2"]), fc("contradicted", 0.4, ["E3"])]
    a = confidence_score(evidence, checks, [cit(1), cit(2)])
    b = confidence_score(list(reversed(evidence)), list(reversed(checks)), [cit(1), cit(2)])
    assert a == b


def test_confidence_out_of_range_clamped():
    # supported with confidence 1.5 is clamped to 1.0
    assert confidence_score([ev(score=1.0)], [fc("supported", 1.5)], [cit()]) == \
        confidence_score([ev(score=1.0)], [fc("supported", 1.0)], [cit()])
    # evidence score 5.0 is clamped to 1.0
    assert confidence_score([ev(score=5.0)], [], []) == \
        confidence_score([ev(score=1.0)], [], [])


def test_malformed_fact_checks_handled_safely():
    evidence = [ev(score=0.8)]
    malformed = ["not a dict", {"verdict": "maybe", "confidence": 0.9}, {"verdict": "supported", "confidence": "high"}]
    score = confidence_score(evidence, malformed, [cit()])
    # All malformed checks are skipped -> neutral fact component.
    assert score == confidence_score(evidence, [], [cit()])
    assert 0.0 <= score <= 1.0


def test_malformed_evidence_handled_safely():
    evidence = ["not a dict", {"source_type": "web", "url": "https://x.com"}, ev(score=0.8)]
    assert confidence_score(evidence, [fc("supported", 0.9)], [cit()]) == \
        confidence_score([ev(score=0.8)], [fc("supported", 0.9)], [cit()])


def test_no_llm_or_api_required():
    # Pure arithmetic — calling the functions never performs I/O.
    assert calculate_confidence([ev()], [fc()], [cit()]) in {"high", "medium", "low"}
    assert route_research("high", 0) in {"complete", "additional_research", "insufficient"}


# ── Routing ──────────────────────────────────────────────────────────────────

def test_invalid_confidence_raises():
    with pytest.raises(ValueError, match="confidence"):
        route_research("unknown", 0)
    with pytest.raises(ValueError, match="confidence"):
        route_research("", 0)


def test_negative_research_rounds_raises():
    with pytest.raises(ValueError, match="research_rounds"):
        route_research("medium", -1)


@pytest.mark.parametrize(
    "confidence,rounds,expected",
    [
        ("high", 0, "complete"),
        ("high", 1, "complete"),
        ("high", 2, "complete"),
        ("high", 5, "complete"),
        ("medium", 0, "additional_research"),
        ("medium", 1, "additional_research"),
        ("medium", 2, "insufficient"),
        ("medium", 3, "insufficient"),
        ("low", 0, "additional_research"),
        ("low", 1, "additional_research"),
        ("low", 2, "insufficient"),
        ("low", 5, "insufficient"),
    ],
)
def test_route_research_table(confidence, rounds, expected):
    assert route_research(confidence, rounds) == expected
