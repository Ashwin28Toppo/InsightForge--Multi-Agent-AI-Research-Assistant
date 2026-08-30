"""Unit tests for claim extraction (no LLM/API calls)."""
import pytest

from backend.app.agents.claim_extractor import (
    _coerce_claims,
    _normalize_claims,
    extract_claims,
)


class FakeChain:
    """Minimal LCEL-chain stand-in with an ``invoke`` method."""

    def __init__(self, result=None, error=None, responder=None):
        self.result = result
        self.error = error
        self.responder = responder
        self.calls = []

    def invoke(self, inputs):
        self.calls.append(inputs)
        assert inputs["research"].strip() or inputs["evidence"].strip(), \
            "chain must not be invoked with empty context"
        if self.error is not None:
            raise self.error
        if self.responder is not None:
            return self.responder(inputs)
        return self.result


def make_evidence(text="evidence text", eid="E1"):
    return {
        "id": eid, "source_type": "web", "text": text, "title": "Source",
        "url": "https://a.com", "score": 0.8,
    }


VALID = {"claims": ["Claim A", "Claim B", "Claim C"]}
VALID_JSON = '{"claims": ["Claim X", "Claim Y"]}'


# ── Valid extraction ─────────────────────────────────────────────────────────

def test_valid_structured_claims():
    chain = FakeChain(result=VALID)
    fallback = FakeChain(result=VALID_JSON)
    claims = extract_claims("some research", [make_evidence()], chain=chain, fallback_chain=fallback)
    assert claims == ["Claim A", "Claim B", "Claim C"]
    assert fallback.calls == []  # primary path succeeded


def test_multiple_claims_preserved_in_order():
    result = {"claims": ["one", "two", "three", "four", "five"]}
    assert extract_claims("r", chain=FakeChain(result=result)) == ["one", "two", "three", "four", "five"]


def test_duplicate_removal_preserves_first_occurrence():
    result = {"claims": ["A", "B", "A", "b"]}
    assert extract_claims("r", chain=FakeChain(result=result)) == ["A", "B", "b"]


def test_whitespace_normalization():
    result = {"claims": ["  padded claim  ", "   "]}
    assert extract_claims("r", chain=FakeChain(result=result)) == ["padded claim"]


def test_blank_claims_removed():
    result = {"claims": ["", "   ", "ok claim"]}
    assert extract_claims("r", chain=FakeChain(result=result)) == ["ok claim"]


# ── Fallback behavior ────────────────────────────────────────────────────────

def test_malformed_structured_output_falls_back():
    chain = FakeChain(result={"claims": "not-a-list"})
    fallback = FakeChain(result=VALID_JSON)
    claims = extract_claims("r", chain=chain, fallback_chain=fallback)
    assert claims == ["Claim X", "Claim Y"]


def test_primary_failure_falls_back():
    chain = FakeChain(error=RuntimeError("structured output failed"))
    fallback = FakeChain(result=VALID_JSON)
    claims = extract_claims("r", chain=chain, fallback_chain=fallback)
    assert claims == ["Claim X", "Claim Y"]


def test_code_fenced_json_fallback():
    chain = FakeChain(error=RuntimeError("boom"))
    fenced = '```json\n{"claims": ["fenced claim"]}\n```'
    assert extract_claims("r", chain=chain, fallback_chain=FakeChain(result=fenced)) == ["fenced claim"]


def test_invalid_json_fallback_raises_value_error():
    chain = FakeChain(error=RuntimeError("boom"))
    with pytest.raises(ValueError, match="unparseable"):
        extract_claims("r", chain=chain, fallback_chain=FakeChain(result="this is not json"))


def test_both_paths_fail_raises_value_error():
    chain = FakeChain(error=RuntimeError("primary boom"))
    fallback = FakeChain(error=RuntimeError("fallback boom"))
    with pytest.raises(ValueError, match="claim extraction failed"):
        extract_claims("r", chain=chain, fallback_chain=fallback)


# ── Validation helpers ───────────────────────────────────────────────────────

def test_non_list_claims_raises():
    with pytest.raises(ValueError, match="claims"):
        _coerce_claims({"claims": "not a list"})


def test_non_string_claim_raises():
    with pytest.raises(ValueError, match="claim must be a string"):
        _coerce_claims({"claims": ["ok", 42]})


def test_normalize_claims_deterministic():
    a = _normalize_claims([" x ", "x", " y ", "x"])
    b = _normalize_claims([" x ", "x", " y ", "x"])
    assert a == ["x", "y"]
    assert a == b


# ── No-context behavior ──────────────────────────────────────────────────────

def test_empty_research_and_evidence_returns_empty_without_chain_call():
    chain = FakeChain(error=RuntimeError("chain must not be called"))
    assert extract_claims(None, None, chain=chain) == []
    assert extract_claims("", [], chain=chain) == []
    assert extract_claims("   ", None, chain=chain) == []
    assert chain.calls == []


def test_evidence_without_usable_text_treated_as_empty():
    chain = FakeChain(error=RuntimeError("chain must not be called"))
    evidence = [{"id": "E1", "source_type": "web", "text": "   ", "title": "T", "score": 0.5}]
    assert extract_claims("", evidence, chain=chain) == []
    assert chain.calls == []


# ── Context passing ──────────────────────────────────────────────────────────

def test_research_only_extraction():
    chain = FakeChain(result=VALID)
    extract_claims("research body", None, chain=chain)
    inputs = chain.calls[0]
    assert inputs["research"] == "research body"
    assert inputs["evidence"] == ""


def test_evidence_only_extraction():
    chain = FakeChain(result=VALID)
    extract_claims(None, [make_evidence(text="evidence body")], chain=chain)
    inputs = chain.calls[0]
    assert inputs["research"] == ""
    assert "evidence body" in inputs["evidence"]
    assert "E1" in inputs["evidence"]


def test_research_and_evidence_extraction():
    chain = FakeChain(result=VALID)
    extract_claims("research body", [make_evidence(text="evidence body")], chain=chain)
    inputs = chain.calls[0]
    assert inputs["research"] == "research body"
    assert "evidence body" in inputs["evidence"]


# ── Determinism ──────────────────────────────────────────────────────────────

def test_deterministic_repeated_calls():
    chain = FakeChain(result=VALID)
    a = extract_claims("r", chain=chain)
    b = extract_claims("r", chain=FakeChain(result=VALID))
    assert a == b
