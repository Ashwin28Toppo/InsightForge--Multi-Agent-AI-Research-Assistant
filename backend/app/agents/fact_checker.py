"""Fact Checker — evaluates claims strictly against supplied evidence.

Produces :class:`FactCheck` dicts (the schema from ``graph/state.py``) with
one FactCheck per claim, in input order. No web browsing or document
retrieval: the LLM only ever sees the claim and the compact evidence context.

Pattern follows ``planner.py``: primary structured-output chain with a
JSON-parsing fallback. If there is no usable evidence, results are
deterministic and no LLM call is made.
"""
from __future__ import annotations

import json
from typing import Literal

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from backend.app.agents.llm import get_llm
from backend.app.graph.state import EvidenceItem, FactCheck

VALID_VERDICTS = ("supported", "contradicted", "insufficient")

fact_check_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a fact checker. Evaluate the claim ONLY against the supplied evidence.

Rules:
- Do not use outside knowledge or general model knowledge.
- Use only the supplied evidence. Do not invent evidence.
- Do not browse the web or retrieve documents.

Determine exactly one of three verdicts:
- "supported": the supplied evidence provides sufficient information supporting the claim.
- "contradicted": the supplied evidence provides information that conflicts with the claim.
- "insufficient": the supplied evidence does not contain enough information to establish support or contradiction.

Return only evidence IDs from the EVIDENCE section that actually support or contradict the claim.
If the verdict is "insufficient", evidence_refs should be an empty list.
Confidence must be a number between 0.0 and 1.0 representing your confidence in the verdict.

Respond with a single JSON object of the form:
{"verdict": "supported", "confidence": 0.9, "evidence_refs": ["E1"]}"""),
    ("human", "CLAIM:\n{claim}\n\nEVIDENCE:\n{evidence}"),
])


class _VerdictOutput(BaseModel):
    """Internal structured schema for the LLM verdict on one claim."""

    verdict: Literal["supported", "contradicted", "insufficient"]
    confidence: float
    evidence_refs: list[str] = Field(default_factory=list)


def build_fact_check_chain(llm=None):
    """Primary chain: structured output over one claim + evidence context."""
    llm = llm or get_llm()
    return fact_check_prompt | llm.with_structured_output(_VerdictOutput)


def build_fact_check_fallback_chain(llm=None):
    """Fallback chain: plain generation, JSON parsed afterwards."""
    llm = llm or get_llm()
    return fact_check_prompt | llm | StrOutputParser()


_default_chain = build_fact_check_chain()
_fallback_chain = build_fact_check_fallback_chain()


# ── Public API ───────────────────────────────────────────────────────────────

def fact_check_claims(
    claims: list[str],
    evidence: list[EvidenceItem] | None = None,
    chain=None,
    fallback_chain=None,
) -> list[FactCheck]:
    """Fact-check each claim against the supplied evidence.

    Args:
        claims: Non-blank claim strings. One FactCheck is returned per claim,
            in the same order.
        evidence: :class:`EvidenceItem` dicts to evaluate against.
        chain / fallback_chain: Optional chain overrides (for tests).

    Returns:
        List of :class:`FactCheck` (same length and order as ``claims``).

    Raises:
        ValueError: for blank claims, invalid LLM output (after both paths),
            or unsupported/contradicted results with no valid evidence refs.

    Notes:
        - If there is no usable evidence, every claim deterministically
          returns ``{"verdict": "insufficient", "confidence": 0.0,
          "evidence_refs": []}`` and the LLM is NOT called.
        - The claim is attached by this code; the model never rewrites it.
    """
    normalized_claims: list[str] = []
    for claim in claims:
        if not isinstance(claim, str) or not claim.strip():
            raise ValueError("claims must be non-blank strings")
        normalized_claims.append(claim.strip())

    usable_evidence = [
        e for e in (evidence or []) if isinstance(e, dict) and e.get("id")
    ]
    if not usable_evidence:
        return [
            FactCheck(claim=c, verdict="insufficient", confidence=0.0, evidence_refs=[])
            for c in normalized_claims
        ]

    chain = chain or _default_chain
    fallback_chain = fallback_chain or _fallback_chain
    valid_ids = {e["id"] for e in usable_evidence}

    return [
        _check_single_claim(c, usable_evidence, chain, fallback_chain, valid_ids)
        for c in normalized_claims
    ]


# ── Per-claim flow ───────────────────────────────────────────────────────────

def _check_single_claim(
    claim: str,
    evidence: list[EvidenceItem],
    chain,
    fallback_chain,
    valid_ids: set[str],
) -> FactCheck:
    context = _format_evidence_context(evidence)
    try:
        result = chain.invoke({"claim": claim, "evidence": context})
        return _coerce_fact_check(claim, result, valid_ids)
    except Exception:
        try:
            raw = fallback_chain.invoke({"claim": claim, "evidence": context})
            return _parse_fact_check(claim, raw, valid_ids)
        except Exception as e:
            raise ValueError(
                f"fact checking failed for claim {claim!r}: {e}"
            ) from e


# ── Evidence context formatting ──────────────────────────────────────────────

def _format_evidence_context(evidence: list[EvidenceItem]) -> str:
    """Build a compact, ID-labelled evidence context (nothing else is sent)."""
    blocks: list[str] = []
    for item in evidence:
        lines = [f"[{item.get('id', '')}]"]
        lines.append(f"Source: {item.get('source_type', '')}")
        lines.append(f"Title: {item.get('title', '')}")
        if item.get("url"):
            lines.append(f"URL: {item['url']}")
        if item.get("document_id"):
            lines.append(f"Document: {item['document_id']}")
        if item.get("page") is not None:
            lines.append(f"Page: {item['page']}")
        if item.get("chunk_index") is not None:
            lines.append(f"Chunk index: {item['chunk_index']}")
        lines.append(f"Text: {item.get('text', '')}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


# ── Parsing / validation helpers ─────────────────────────────────────────────

def _coerce_fact_check(
    claim: str, result, valid_ids: set[str]
) -> FactCheck:
    if hasattr(result, "model_dump"):
        result = result.model_dump()
    if not isinstance(result, dict):
        raise ValueError(f"fact checker did not return a dict, got {type(result).__name__}")
    return _validate_fact_check(
        claim,
        result.get("verdict"),
        result.get("confidence"),
        result.get("evidence_refs"),
        valid_ids,
    )


def _validate_fact_check(
    claim: str,
    verdict,
    confidence,
    evidence_refs,
    valid_ids: set[str],
) -> FactCheck:
    """Validate and normalize a single verdict into a :class:`FactCheck`."""
    if verdict not in VALID_VERDICTS:
        raise ValueError(f"invalid verdict: {verdict!r}")

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        raise ValueError(f"invalid confidence: {confidence!r}")
    if not (0.0 <= confidence <= 1.0):
        raise ValueError(f"confidence out of range [0.0, 1.0]: {confidence}")

    if not isinstance(evidence_refs, list) or not all(
        isinstance(r, str) for r in evidence_refs
    ):
        raise ValueError("evidence_refs must be a list of strings")

    # Never allow hallucinated evidence IDs into the result.
    filtered_refs = [r for r in evidence_refs if r in valid_ids]

    if verdict in ("supported", "contradicted") and not filtered_refs:
        raise ValueError(
            f"verdict {verdict!r} requires at least one valid evidence reference"
        )

    return FactCheck(
        claim=claim,
        verdict=verdict,
        confidence=confidence,
        evidence_refs=filtered_refs,
    )


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


def _parse_fact_check(claim: str, raw, valid_ids: set[str]) -> FactCheck:
    """Parse a plain-text LLM response into a validated FactCheck."""
    if not isinstance(raw, str):
        raw = str(raw)
    try:
        data = json.loads(_extract_json(raw))
    except json.JSONDecodeError as e:
        raise ValueError(
            f"fact checker returned unparseable output: {raw[:200]!r}"
        ) from e
    return _coerce_fact_check(claim, data, valid_ids)
