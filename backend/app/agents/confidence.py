"""Confidence scoring and research routing (deterministic, no LLM).

Scoring formula (documented, deterministic, explainable):

    fact_score      = mean of signed fact-check confidences
                      (supported: +conf, contradicted: -conf, insufficient: 0.0)
                      When there are no usable fact checks, the fact component
                      stays at a conservative neutral 0.0.
    evidence_score  = mean of evidence scores, each clamped to [0, 1]
    citation_score  = min(1, number_of_citations / number_of_evidence_items)

    normalized_fact_score = (fact_score + 1) / 2     # maps [-1, 1] -> [0, 1]

    raw_score = (0.55 * normalized_fact_score
               + 0.30 * evidence_score
               + 0.15 * citation_score)
    clamped to [0, 1].

Thresholds:
    score >= 0.75 -> "high"
    score >= 0.50 -> "medium"
    score <  0.50 -> "low"

Design notes:
- No evidence -> score 0.0 -> "low".
- Without fact checks the fact component stays neutral (0.5), capping the
  maximum achievable score at 0.725, so evidence alone can never reach "high".
- Contradictions pull the normalized fact score down sharply.
- Malformed fact checks are skipped; out-of-range confidences/scores are
  clamped, never crash.
"""
from __future__ import annotations

from typing import Iterable

from backend.app.graph.state import Citation, EvidenceItem, FactCheck

VALID_CONFIDENCE = ("high", "medium", "low")

HIGH_THRESHOLD = 0.75
MEDIUM_THRESHOLD = 0.50

# Bounded rounds: additional research is attempted while rounds < MAX_ROUNDS.
MAX_ROUNDS = 2

_W_FACT = 0.55
_W_EVIDENCE = 0.30
_W_CITATION = 0.15


# ── Public API ───────────────────────────────────────────────────────────────

def confidence_score(
    evidence: Iterable[EvidenceItem] | None,
    fact_checks: Iterable[FactCheck] | None = None,
    citations: Iterable[Citation] | None = None,
) -> float:
    """Return the raw normalized research confidence in [0.0, 1.0]."""
    # Only usable evidence counts (dicts with an id), consistent with the
    # fact checker and citation layers.
    evidence_items = [
        e for e in (evidence or []) if isinstance(e, dict) and e.get("id")
    ]
    if not evidence_items:
        return 0.0

    # Evidence component: mean of per-item scores, clamped to [0, 1].
    evidence_scores = [_clamp01(_score(e)) for e in evidence_items]
    evidence_score = sum(evidence_scores) / len(evidence_scores)

    # Citation component: coverage ratio, capped at 1.0.
    citation_count = len([c for c in (citations or []) if isinstance(c, dict)])
    citation_score = min(1.0, citation_count / len(evidence_items))

    # Fact-check component: mean signed confidence.
    signed = []
    for fc in fact_checks or []:
        if not isinstance(fc, dict):
            continue  # skip malformed
        verdict = fc.get("verdict")
        if verdict not in ("supported", "contradicted", "insufficient"):
            continue  # skip invalid verdicts
        confidence = _clamp01(_to_float(fc.get("confidence")) or 0.0)
        if verdict == "supported":
            signed.append(confidence)
        elif verdict == "contradicted":
            signed.append(-confidence)
        else:  # insufficient contributes neutrally
            signed.append(0.0)

    if signed:
        fact_score = sum(signed) / len(signed)  # in [-1, 1]
        normalized_fact = (fact_score + 1.0) / 2.0
    else:
        # Conservative neutral: prevents "high" without any fact checks.
        normalized_fact = 0.5

    raw = (
        _W_FACT * normalized_fact
        + _W_EVIDENCE * evidence_score
        + _W_CITATION * citation_score
    )
    return _clamp01(raw)


def calculate_confidence(
    evidence: Iterable[EvidenceItem] | None,
    fact_checks: Iterable[FactCheck] | None = None,
    citations: Iterable[Citation] | None = None,
) -> str:
    """Map the confidence score to exactly one of: high | medium | low."""
    score = confidence_score(evidence, fact_checks, citations)
    if score >= HIGH_THRESHOLD:
        return "high"
    if score >= MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def route_research(confidence: str, research_rounds: int = 0) -> str:
    """Decide the next action from confidence and the research round count.

    Rules:
        high                    -> "complete"
        medium/low, rounds < 2  -> "additional_research"
        medium/low, rounds >= 2 -> "insufficient"

    Returns exactly one of: complete | additional_research | insufficient.

    Raises:
        ValueError: for unknown confidence values or negative research_rounds.
    """
    if confidence not in VALID_CONFIDENCE:
        raise ValueError(
            f"invalid confidence: {confidence!r}. "
            f"Expected one of {VALID_CONFIDENCE}"
        )
    if research_rounds < 0:
        raise ValueError(
            f"research_rounds must be >= 0, got {research_rounds}"
        )

    if confidence == "high":
        return "complete"
    if research_rounds < MAX_ROUNDS:
        return "additional_research"
    return "insufficient"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _score(item: dict) -> float:
    value = _to_float(item.get("score"))
    return value if value is not None else 0.0


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))
