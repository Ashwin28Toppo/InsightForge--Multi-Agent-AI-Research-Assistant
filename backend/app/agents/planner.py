"""Research Planner — converts a user query into a :class:`ResearchPlan`.

The planner is an LCEL chain. The primary path uses structured output
(``with_structured_output`` with the ``ResearchPlan`` TypedDict as the
contract); if that fails or returns malformed data, a robust fallback invokes
the LLM normally and parses the JSON safely.

No web search, Tavily, Qdrant, or embeddings are used here.
"""
from __future__ import annotations

import json

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from backend.app.agents.llm import get_llm
from backend.app.graph.state import ResearchPlan

planner_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert research planner. Given a user's research query, build a concise research plan.

Identify the important, non-redundant research angles needed to answer the query comprehensively. Keep each angle specific and concise (3-6 angles).

Decide whether the local knowledge base (the user's uploaded documents) could be useful:
- Set "use_rag" to true when the query references uploaded/local documents, internal files, or topics where the user's own materials are likely to add value.
- Set "use_rag" to false for general, current, or web-focused queries where local documents are unlikely to help.

Respond with a single JSON object of the form:
{"research_angles": ["angle one", "angle two"], "use_rag": true}"""),
    ("human", "Research query:\n{query}"),
])


def build_planner_chain(llm=None):
    """Build the primary (structured-output) planner chain.

    Args:
        llm: Optional LLM override (for tests); defaults to the shared LLM.
    """
    llm = llm or get_llm()
    return planner_prompt | llm.with_structured_output(ResearchPlan)


def build_fallback_chain(llm=None):
    """Build the fallback chain: plain generation, JSON parsed afterwards."""
    llm = llm or get_llm()
    return planner_prompt | llm | StrOutputParser()


_default_chain = build_planner_chain()
_fallback_chain = build_fallback_chain()


def plan_research(
    query: str,
    chain=None,
    fallback_chain=None,
) -> ResearchPlan:
    """Plan a research query, returning a :class:`ResearchPlan`.

    Args:
        query: The user's research query (must be non-blank).
        chain: Optional primary chain override (for tests).
        fallback_chain: Optional fallback chain override (for tests).

    Returns:
        A ``ResearchPlan`` dict: ``{"research_angles": [...], "use_rag": bool}``.

    Raises:
        ValueError: if the query is empty/blank, or if the output cannot be
            parsed into a valid ResearchPlan.
    """
    if not query or not query.strip():
        raise ValueError("query must not be empty")

    chain = chain or _default_chain
    fallback_chain = fallback_chain or _fallback_chain

    try:
        result = chain.invoke({"query": query})
        return _coerce_structured_result(result)
    except Exception:
        # Fallback: plain generation + safe JSON parsing.
        raw = fallback_chain.invoke({"query": query})
        return _parse_json_plan(raw)


# ── Parsing / validation helpers ─────────────────────────────────────────────

def _coerce_structured_result(result) -> ResearchPlan:
    """Normalize the structured-output result (dict or pydantic model)."""
    if hasattr(result, "model_dump"):
        result = result.model_dump()
    return _validate_plan(result)


def _validate_plan(data) -> ResearchPlan:
    """Validate that ``data`` is a well-formed ResearchPlan dict."""
    if not isinstance(data, dict):
        raise ValueError(
            f"planner did not return a dict, got {type(data).__name__}"
        )
    angles = data.get("research_angles")
    use_rag = data.get("use_rag")
    if not isinstance(angles, list) or not all(isinstance(a, str) for a in angles):
        raise ValueError("planner output missing a valid 'research_angles' list")
    if not isinstance(use_rag, bool):
        raise ValueError("planner output missing a valid 'use_rag' boolean")
    return {"research_angles": angles, "use_rag": use_rag}


def _extract_json(raw: str) -> str:
    """Strip markdown code fences so ``json.loads`` can parse the payload."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _parse_json_plan(raw) -> ResearchPlan:
    """Parse a plain-text LLM response into a validated ResearchPlan."""
    if not isinstance(raw, str):
        raw = str(raw)
    try:
        data = json.loads(_extract_json(raw))
    except json.JSONDecodeError as e:
        raise ValueError(
            f"planner returned unparseable output: {raw[:200]!r}"
        ) from e
    return _validate_plan(data)
