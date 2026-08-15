"""Unit tests for the fact checker.

No real LLM/API calls: fake chains are injected and the validation/parsing
helpers are tested directly.
"""
import pytest

from backend.app.agents.fact_checker import (
    _format_evidence_context,
    _validate_fact_check,
    fact_check_claims,
)

VALID_IDS = {"E1", "E2", "E3"}


class FakeChain:
    """Minimal stand-in for an LCEL chain (implements ``invoke``)."""

    def __init__(self, result=None, error=None, responder=None):
        self.result = result
        self.error = error
        self.responder = responder
        self.calls = []

    def invoke(self, inputs):
        self.calls.append(inputs)
        assert inputs["claim"].strip(), "chain should only be invoked with a non-blank claim"
        if self.error is not None:
            raise self.error
        if self.responder is not None:
            return self.responder(inputs)
        return self.result


def make_evidence(
    eid="E1",
    source_type="web",
    title="Example",
    text="Evidence text here",
    url="https://example.com",
    document_id=None,
    page=None,
    chunk_index=None,
    score=0.8,
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


VALID_RESULT = {"verdict": "supported", "confidence": 0.92, "evidence_refs": ["E1"]}
VALID_JSON = '{"verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1"]}'
EVIDENCE = [make_evidence(), make_evidence(eid="E2", title="Other")]


# ── Basic verdicts ───────────────────────────────────────────────────────────

def test_supported_result():
    chain = FakeChain(result=VALID_RESULT)
    result = fact_check_claims(["the claim"], EVIDENCE, chain=chain)
    assert set(result[0].keys()) == {"claim", "verdict", "confidence", "evidence_refs"}
    assert result[0]["claim"] == "the claim"
    assert result[0]["verdict"] == "supported"
    assert result[0]["confidence"] == 0.92
    assert result[0]["evidence_refs"] == ["E1"]


def test_contradicted_result():
    chain = FakeChain(result={"verdict": "contradicted", "confidence": 0.8, "evidence_refs": ["E2"]})
    result = fact_check_claims(["c"], EVIDENCE, chain=chain)
    assert result[0]["verdict"] == "contradicted"
    assert result[0]["evidence_refs"] == ["E2"]


def test_insufficient_result():
    chain = FakeChain(result={"verdict": "insufficient", "confidence": 0.4, "evidence_refs": []})
    result = fact_check_claims(["c"], EVIDENCE, chain=chain)
    assert result[0]["verdict"] == "insufficient"
    assert result[0]["evidence_refs"] == []


def test_claim_attached_by_application_not_model():
    # Even if the model echoes a different claim, the app's claim wins.
    chain = FakeChain(result={"claim": "HACKED", "verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1"]})
    result = fact_check_claims(["my real claim"], EVIDENCE, chain=chain)
    assert result[0]["claim"] == "my real claim"


def test_multiple_claims_preserve_input_order():
    def responder(inputs):
        claim = inputs["claim"]
        if claim == "first":
            return {"verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1"]}
        if claim == "second":
            return {"verdict": "contradicted", "confidence": 0.7, "evidence_refs": ["E2"]}
        return {"verdict": "insufficient", "confidence": 0.5, "evidence_refs": []}

    chain = FakeChain(responder=responder)
    result = fact_check_claims(["first", "second", "third"], EVIDENCE, chain=chain)
    assert [r["claim"] for r in result] == ["first", "second", "third"]
    assert [r["verdict"] for r in result] == ["supported", "contradicted", "insufficient"]


def test_blank_claim_raises_value_error():
    chain = FakeChain(result=VALID_RESULT)
    with pytest.raises(ValueError, match="claims"):
        fact_check_claims(["ok", "   "], EVIDENCE, chain=chain)
    assert chain.calls == []  # nothing invoked


def test_non_string_claim_raises_value_error():
    with pytest.raises(ValueError, match="claims"):
        fact_check_claims([42], EVIDENCE)


# ── Validation helpers ───────────────────────────────────────────────────────

def test_invalid_verdict_rejected():
    with pytest.raises(ValueError, match="verdict"):
        _validate_fact_check("c", "maybe", 0.5, ["E1"], VALID_IDS)


def test_invalid_confidence_rejected():
    with pytest.raises(ValueError, match="confidence"):
        _validate_fact_check("c", "supported", "high", ["E1"], VALID_IDS)


def test_confidence_below_zero_rejected():
    with pytest.raises(ValueError, match="confidence"):
        _validate_fact_check("c", "supported", -0.1, ["E1"], VALID_IDS)


def test_confidence_above_one_rejected():
    with pytest.raises(ValueError, match="confidence"):
        _validate_fact_check("c", "supported", 1.1, ["E1"], VALID_IDS)


def test_non_list_evidence_refs_rejected():
    with pytest.raises(ValueError, match="evidence_refs"):
        _validate_fact_check("c", "supported", 0.9, "E1", VALID_IDS)


def test_evidence_refs_non_string_entries_rejected():
    with pytest.raises(ValueError, match="evidence_refs"):
        _validate_fact_check("c", "supported", 0.9, ["E1", 42], VALID_IDS)


# ── Evidence references ──────────────────────────────────────────────────────

def test_valid_evidence_refs_preserved_exactly():
    fc = _validate_fact_check("c", "supported", 0.9, ["E1", "E3"], VALID_IDS)
    assert fc["evidence_refs"] == ["E1", "E3"]


def test_hallucinated_evidence_ids_filtered():
    fc = _validate_fact_check("c", "supported", 0.9, ["E1", "FAKE123"], VALID_IDS)
    assert fc["evidence_refs"] == ["E1"]


def test_supported_without_valid_ref_raises():
    with pytest.raises(ValueError, match="evidence reference"):
        _validate_fact_check("c", "supported", 0.9, ["FAKE"], VALID_IDS)


def test_contradicted_without_valid_ref_raises():
    with pytest.raises(ValueError, match="evidence reference"):
        _validate_fact_check("c", "contradicted", 0.9, [], VALID_IDS)


def test_insufficient_may_have_empty_refs():
    fc = _validate_fact_check("c", "insufficient", 0.3, [], VALID_IDS)
    assert fc["verdict"] == "insufficient"
    assert fc["evidence_refs"] == []


# ── No-evidence behavior ─────────────────────────────────────────────────────

def test_empty_evidence_returns_insufficient_without_llm():
    chain = FakeChain(error=RuntimeError("chain must not be called"))
    result = fact_check_claims(["c1", "c2"], [], chain=chain)
    assert [r["verdict"] for r in result] == ["insufficient", "insufficient"]
    assert all(r["confidence"] == 0.0 for r in result)
    assert all(r["evidence_refs"] == [] for r in result)
    assert chain.calls == []  # LLM not called


def test_evidence_without_ids_treated_as_no_evidence():
    chain = FakeChain(error=RuntimeError("chain must not be called"))
    evidence = [{"source_type": "web", "text": "x", "title": "t", "score": 0.5}]  # no id
    result = fact_check_claims(["c"], evidence, chain=chain)
    assert result[0]["verdict"] == "insufficient"
    assert chain.calls == []


# ── LLM failure / fallback ───────────────────────────────────────────────────

def test_primary_failure_falls_back_to_json():
    chain = FakeChain(error=RuntimeError("structured output failed"))
    fallback = FakeChain(result=VALID_JSON)
    result = fact_check_claims(["c"], EVIDENCE, chain=chain, fallback_chain=fallback)
    assert result[0]["verdict"] == "supported"
    assert result[0]["confidence"] == 0.9
    assert fallback.calls


def test_malformed_structured_output_falls_back():
    chain = FakeChain(result={"verdict": "maybe", "confidence": 0.5, "evidence_refs": ["E1"]})
    fallback = FakeChain(result=VALID_JSON)
    result = fact_check_claims(["c"], EVIDENCE, chain=chain, fallback_chain=fallback)
    assert result[0]["verdict"] == "supported"


def test_json_code_fenced_fallback():
    chain = FakeChain(error=RuntimeError("boom"))
    fenced = '```json\n{"verdict": "contradicted", "confidence": 0.6, "evidence_refs": ["E2"]}\n```'
    result = fact_check_claims(["c"], EVIDENCE, chain=chain, fallback_chain=FakeChain(result=fenced))
    assert result[0]["verdict"] == "contradicted"
    assert result[0]["evidence_refs"] == ["E2"]


def test_invalid_fallback_json_raises_value_error():
    chain = FakeChain(error=RuntimeError("boom"))
    with pytest.raises(ValueError, match="unparseable"):
        fact_check_claims(["c"], EVIDENCE, chain=chain, fallback_chain=FakeChain(result="not json"))


def test_llm_failure_does_not_silently_produce_supported():
    chain = FakeChain(error=RuntimeError("primary boom"))
    fallback = FakeChain(error=RuntimeError("fallback boom"))
    with pytest.raises(ValueError):
        fact_check_claims(["c"], EVIDENCE, chain=chain, fallback_chain=fallback)


def test_fallback_hallucinated_ids_filtered_and_supported_kept():
    chain = FakeChain(error=RuntimeError("boom"))
    fallback = FakeChain(result='{"verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1", "FAKE"]}')
    result = fact_check_claims(["c"], EVIDENCE, chain=chain, fallback_chain=fallback)
    assert result[0]["evidence_refs"] == ["E1"]


# ── Evidence context ─────────────────────────────────────────────────────────

def test_evidence_context_includes_required_fields():
    context = _format_evidence_context(
        [
            make_evidence(eid="E1", source_type="web", title="Alpha", text="web text", url="https://a.com"),
            make_evidence(
                eid="E2", source_type="rag", title="doc.pdf", text="rag text",
                url=None, document_id="doc-1", page=4, chunk_index=2,
            ),
        ]
    )
    assert "[E1]" in context
    assert "Source: web" in context
    assert "Title: Alpha" in context
    assert "URL: https://a.com" in context
    assert "Text: web text" in context
    assert "[E2]" in context
    assert "Source: rag" in context
    assert "Document: doc-1" in context
    assert "Page: 4" in context
    assert "Chunk index: 2" in context
    assert "Text: rag text" in context


def test_evidence_context_omits_unrelated_fields():
    item = make_evidence(eid="E1", text="only this text matters")
    item["secret_field"] = "MUST NOT LEAK"
    context = _format_evidence_context([item])
    assert "MUST NOT LEAK" not in context
    assert "secret_field" not in context


def test_chain_receives_only_claim_and_evidence():
    chain = FakeChain(result=VALID_RESULT)
    fact_check_claims(["c"], EVIDENCE, chain=chain)
    inputs = chain.calls[0]
    assert set(inputs.keys()) == {"claim", "evidence"}
    assert "report" not in inputs
    assert inputs["claim"] == "c"
    assert "E1" in inputs["evidence"] and "E2" in inputs["evidence"]


# ── Determinism ──────────────────────────────────────────────────────────────

def test_application_level_output_is_deterministic():
    chain = FakeChain(result=VALID_RESULT)
    a = fact_check_claims(["c1", "c2"], EVIDENCE, chain=chain)
    b = fact_check_claims(["c1", "c2"], EVIDENCE, chain=chain)
    assert a == b


# ── Batched mode (one LLM call for all claims) ──────────────────────────────


class FakeBatchChain:
    """Stand-in for the batched fact-check chain (inputs use ``claims``)."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def invoke(self, inputs):
        self.calls.append(inputs)
        if self.error is not None:
            raise self.error
        return self.result


def test_batch_mode_checks_all_claims_in_one_call():
    chain = FakeBatchChain(result={
        "results": [
            {"claim": 0, "verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1"]},
            {"claim": 1, "verdict": "insufficient", "confidence": 0.2, "evidence_refs": []},
        ]
    })
    result = fact_check_claims(["a", "b"], EVIDENCE, chain=chain, batch=True)

    assert len(chain.calls) == 1  # ONE call for both claims
    assert set(chain.calls[0].keys()) == {"claims", "evidence"}
    assert [fc["verdict"] for fc in result] == ["supported", "insufficient"]
    assert result[0]["claim"] == "a"
    assert result[1]["claim"] == "b"


def test_batch_mode_preserves_input_order_regardless_of_result_order():
    chain = FakeBatchChain(result={
        "results": [
            {"claim": 1, "verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1"]},
            {"claim": 0, "verdict": "contradicted", "confidence": 0.8, "evidence_refs": ["E2"]},
        ]
    })
    result = fact_check_claims(["first", "second"], EVIDENCE, chain=chain, batch=True)

    assert [fc["claim"] for fc in result] == ["first", "second"]
    assert result[0]["verdict"] == "contradicted"
    assert result[1]["verdict"] == "supported"


def test_batch_mode_fallback_parses_json():
    chain = FakeBatchChain(error=RuntimeError("structured output failed"))
    fallback = FakeBatchChain(result=(
        '```json\n{"results": [{"claim": 0, "verdict": "supported", '
        '"confidence": 0.9, "evidence_refs": ["E1"]}]}\n```'
    ))
    result = fact_check_claims(["c"], EVIDENCE, chain=chain, fallback_chain=fallback, batch=True)

    assert result[0]["verdict"] == "supported"


def test_batch_mode_rejects_missing_claim_results():
    chain = FakeBatchChain(result={
        "results": [{"claim": 0, "verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1"]}]
    })
    fallback = FakeBatchChain(error=RuntimeError("fallback boom"))
    with pytest.raises(ValueError):
        fact_check_claims(["a", "b"], EVIDENCE, chain=chain, fallback_chain=fallback, batch=True)


def test_batch_mode_rejects_out_of_range_claim_index():
    chain = FakeBatchChain(result={
        "results": [{"claim": 5, "verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1"]}]
    })
    fallback = FakeBatchChain(error=RuntimeError("fallback boom"))
    with pytest.raises(ValueError):
        fact_check_claims(["a"], EVIDENCE, chain=chain, fallback_chain=fallback, batch=True)


def test_batch_mode_no_evidence_short_circuits_without_llm():
    chain = FakeBatchChain(error=RuntimeError("chain must not be called"))
    result = fact_check_claims(["a", "b"], [], chain=chain, batch=True)
    assert all(fc["verdict"] == "insufficient" for fc in result)
