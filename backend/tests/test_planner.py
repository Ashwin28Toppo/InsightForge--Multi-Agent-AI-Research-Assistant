"""Unit tests for the research planner.

No real LLM/API calls: all chains are injected fakes and the parsing helpers
are tested directly.
"""
import pytest

from backend.app.agents.planner import (
    _parse_json_plan,
    _validate_plan,
    plan_research,
)


class FakeChain:
    """Minimal stand-in for an LCEL chain (implements ``invoke``)."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.called = False

    def invoke(self, inputs):
        self.called = True
        assert inputs["query"], "chain should only be invoked with a non-blank query"
        if self.error is not None:
            raise self.error
        return self.result


class ModelLike:
    """Mimics a pydantic-style result returned by with_structured_output."""

    def __init__(self, data):
        self._data = data

    def model_dump(self):
        return self._data


VALID_PLAN = {"research_angles": ["crop yields", "water availability"], "use_rag": True}
VALID_JSON = '{"research_angles": ["crop yields"], "use_rag": true}'


# ── Valid query → valid plan ─────────────────────────────────────────────────

def test_valid_query_produces_valid_plan():
    chain = FakeChain(result=VALID_PLAN)
    fallback = FakeChain(result=VALID_JSON)

    plan = plan_research("What are the effects of climate change on agriculture?", chain=chain, fallback_chain=fallback)

    assert plan == VALID_PLAN
    assert isinstance(plan["research_angles"], list)
    assert all(isinstance(a, str) for a in plan["research_angles"])
    assert isinstance(plan["use_rag"], bool)
    assert fallback.called is False  # primary path succeeded


def test_use_rag_false_is_allowed():
    chain = FakeChain(result={"research_angles": ["latest news"], "use_rag": False})
    plan = plan_research("Latest AI news this week", chain=chain, fallback_chain=FakeChain(result=VALID_JSON))
    assert plan["use_rag"] is False


def test_structured_result_may_be_pydantic_like():
    chain = FakeChain(result=ModelLike(VALID_PLAN))
    plan = plan_research("climate and agriculture", chain=chain, fallback_chain=FakeChain(result=VALID_JSON))
    assert plan == VALID_PLAN


# ── Input validation ─────────────────────────────────────────────────────────

def test_empty_query_raises_value_error():
    chain = FakeChain(result=VALID_PLAN)
    with pytest.raises(ValueError, match="query"):
        plan_research("", chain=chain, fallback_chain=FakeChain(result=VALID_JSON))
    assert chain.called is False  # validation happens before the chain runs


def test_whitespace_query_raises_value_error():
    chain = FakeChain(result=VALID_PLAN)
    with pytest.raises(ValueError, match="query"):
        plan_research("   \n\t ", chain=chain, fallback_chain=FakeChain(result=VALID_JSON))
    assert chain.called is False


# ── Fallback behavior ────────────────────────────────────────────────────────

def test_primary_failure_falls_back_to_json():
    chain = FakeChain(error=RuntimeError("structured output failed"))
    fallback = FakeChain(result=VALID_JSON)

    plan = plan_research("climate", chain=chain, fallback_chain=fallback)

    assert plan["research_angles"] == ["crop yields"]
    assert plan["use_rag"] is True
    assert fallback.called is True


def test_malformed_structured_output_falls_back_to_json():
    chain = FakeChain(result={"research_angles": "not-a-list", "use_rag": True})
    fallback = FakeChain(result=VALID_JSON)

    plan = plan_research("climate", chain=chain, fallback_chain=fallback)

    assert plan == {"research_angles": ["crop yields"], "use_rag": True}


def test_fallback_parses_json_in_code_fences():
    chain = FakeChain(error=RuntimeError("boom"))
    fenced = '```json\n{"research_angles": ["a", "b"], "use_rag": false}\n```'
    plan = plan_research("climate", chain=chain, fallback_chain=FakeChain(result=fenced))
    assert plan == {"research_angles": ["a", "b"], "use_rag": False}


def test_fallback_unparseable_output_raises_value_error():
    chain = FakeChain(error=RuntimeError("boom"))
    with pytest.raises(ValueError, match="unparseable"):
        plan_research("climate", chain=chain, fallback_chain=FakeChain(result="this is not json"))


def test_fallback_missing_fields_raises_value_error():
    chain = FakeChain(error=RuntimeError("boom"))
    with pytest.raises(ValueError, match="use_rag"):
        plan_research("climate", chain=chain, fallback_chain=FakeChain(result='{"research_angles": []}'))


# ── Validation helpers ───────────────────────────────────────────────────────

def test_validate_plan_accepts_valid():
    assert _validate_plan(VALID_PLAN) == VALID_PLAN


def test_validate_plan_rejects_non_dict():
    with pytest.raises(ValueError):
        _validate_plan(["not", "a", "dict"])


def test_validate_plan_rejects_bad_angles():
    with pytest.raises(ValueError, match="research_angles"):
        _validate_plan({"research_angles": 5, "use_rag": True})


def test_validate_plan_rejects_non_string_angles():
    with pytest.raises(ValueError, match="research_angles"):
        _validate_plan({"research_angles": [1, 2], "use_rag": True})


def test_validate_plan_rejects_bad_use_rag():
    with pytest.raises(ValueError, match="use_rag"):
        _validate_plan({"research_angles": ["a"], "use_rag": "yes"})


def test_parse_json_plan_accepts_valid_json():
    assert _parse_json_plan(VALID_JSON) == {"research_angles": ["crop yields"], "use_rag": True}


def test_parse_json_plan_rejects_invalid_json():
    with pytest.raises(ValueError, match="unparseable"):
        _parse_json_plan("{not json")
