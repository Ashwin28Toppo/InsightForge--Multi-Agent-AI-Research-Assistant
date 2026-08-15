"""Regression tests: prompt templates must not treat JSON examples as variables.

Each of these prompts embeds a literal JSON example in its system message.
Without escaped braces, ``ChatPromptTemplate`` parses ``{"key": ...}`` as a
template variable and formatting fails at runtime (this was a latent bug that
only surfaced once the compiled graph started formatting the real prompts in
production).
"""
from backend.app.agents.claim_extractor import claim_extraction_prompt
from backend.app.agents.fact_checker import fact_check_prompt
from backend.app.agents.planner import planner_prompt


def test_planner_prompt_formats_with_query_only():
    rendered = planner_prompt.format(query="sample query")
    assert set(planner_prompt.input_variables) == {"query"}
    assert '{"research_angles": ["angle one", "angle two"], "use_rag": true}' in rendered


def test_fact_check_prompt_formats_with_claim_and_evidence():
    rendered = fact_check_prompt.format(claim="a claim", evidence="some evidence")
    assert set(fact_check_prompt.input_variables) == {"claim", "evidence"}
    assert '{"verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1"]}' in rendered


def test_claim_extraction_prompt_formats_with_research_and_evidence():
    rendered = claim_extraction_prompt.format(research="material", evidence="evidence")
    assert set(claim_extraction_prompt.input_variables) == {"research", "evidence"}
    assert '{"claims": ["claim one", "claim two"]}' in rendered
