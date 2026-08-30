"""Claim extraction — research/evidence -> checkable claim strings.

Follows the planner/fact-checker pattern: a primary structured-output chain
(``with_structured_output``) with a JSON-parsing fallback. The extractor only
produces claims; it never evaluates them (fact checking is a separate step).

Post-processing is deterministic: strip whitespace, drop blanks, and remove
exact duplicates while preserving first-occurrence order.
"""
from __future__ import annotations

import json

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from backend.app.agents.llm import get_llm
from backend.app.graph.state import EvidenceItem

claim_extraction_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a claim extractor. Extract factual, checkable claims from the supplied research and evidence ONLY.

Rules:
- Use ONLY the supplied research/evidence. Do not use outside knowledge.
- Do not invent claims or add facts not present in the supplied context.
- Claims must be factual statements that can be checked against the evidence.
- Claims must be concise, specific, and independently verifiable.
- Avoid questions, instructions, opinions, vague statements, and duplicated claims.
- Target approximately 3-5 claims, but fewer is fine if the material genuinely contains fewer checkable claims.

Respond with a single JSON object of the form:
{{"claims": ["claim one", "claim two"]}}"""),
    ("human", "RESEARCH:\n{research}\n\nEVIDENCE:\n{evidence}"),
])


class _ClaimsOutput(BaseModel):
    """Internal structured schema: a flat list of claim strings."""

    claims: list[str] = Field(default_factory=list)


def build_claim_extraction_chain(llm=None):
    """Primary chain: structured output over research + evidence context."""
    llm = llm or get_llm()
    return claim_extraction_prompt | llm.with_structured_output(_ClaimsOutput)


def build_claim_extraction_fallback_chain(llm=None):
    """Fallback chain: plain generation, JSON parsed afterwards."""
    llm = llm or get_llm()
    return claim_extraction_prompt | llm | StrOutputParser()


_default_chain = build_claim_extraction_chain()
_fallback_chain = build_claim_extraction_fallback_chain()


def extract_claims(
    research: str | None = None,
    evidence: list[EvidenceItem] | None = None,
    chain=None,
    fallback_chain=None,
) -> list[str]:
    """Extract factual, checkable claims from research/evidence.

    Args:
        research: Free-text research material (e.g. search results/scraped text).
        evidence: :class:`EvidenceItem` dicts.
        chain / fallback_chain: Optional chain overrides (for tests).

    Returns:
        Deterministically normalized list of claim strings (stripped, no
        blanks, no exact duplicates, first-occurrence order). ``[]`` when there
        is no research/evidence content (no LLM call is made).

    Raises:
        ValueError: if the output cannot be parsed into valid claims after
            both the primary and fallback paths.
    """
    research_text = (research or "").strip()
    evidence_text = _format_evidence(evidence)
    if not research_text and not evidence_text:
        return []

    chain = chain or _default_chain
    fallback_chain = fallback_chain or _fallback_chain
    context = {"research": research_text, "evidence": evidence_text}

    try:
        result = chain.invoke(context)
        return _coerce_claims(result)
    except Exception:
        try:
            raw = fallback_chain.invoke(context)
            return _parse_claims(raw)
        except Exception as e:
            raise ValueError(f"claim extraction failed: {e}") from e


# ── Helpers ──────────────────────────────────────────────────────────────────

def _format_evidence(evidence) -> str:
    """Compact, ID-labelled evidence context (only usable items)."""
    blocks: list[str] = []
    for item in evidence or []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        label = item.get("title") or item.get("url") or item["id"]
        blocks.append(f"[{item['id']}] {label}\n{text}")
    return "\n\n".join(blocks)


def _coerce_claims(result) -> list[str]:
    """Normalize the structured-output result into validated claims."""
    if hasattr(result, "model_dump"):
        result = result.model_dump()
    if not isinstance(result, dict):
        raise ValueError(
            f"claim extractor did not return a dict, got {type(result).__name__}"
        )
    claims = result.get("claims")
    if not isinstance(claims, list):
        raise ValueError("claim extractor output missing a valid 'claims' list")
    if not all(isinstance(c, str) for c in claims):
        raise ValueError("every claim must be a string")
    return _normalize_claims(claims)


def _normalize_claims(claims: list[str]) -> list[str]:
    """Strip, drop blanks, and dedupe while preserving first-occurrence order."""
    seen: set[str] = set()
    out: list[str] = []
    for claim in claims:
        cleaned = claim.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    return out


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


def _parse_claims(raw) -> list[str]:
    """Parse a plain-text LLM response into validated claims."""
    if not isinstance(raw, str):
        raw = str(raw)
    try:
        data = json.loads(_extract_json(raw))
    except json.JSONDecodeError as e:
        raise ValueError(
            f"claim extractor returned unparseable output: {raw[:200]!r}"
        ) from e
    return _coerce_claims(data)
