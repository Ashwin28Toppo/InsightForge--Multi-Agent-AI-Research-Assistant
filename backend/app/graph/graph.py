"""Compiled LangGraph for the research workflow (Phase 2C Steps 2-4).

Topology:

    START
      ↓
    plan → research → evidence → claim_extraction → fact_check
      → citation → confidence → writer → critic → [conditional router]
        ├── complete             → END
        ├── insufficient         → END
        └── additional_research  → increment_rounds → research (bounded loop)

The router is a thin adapter over the existing ``route_research()``; the loop
is bounded because ``route_research`` terminates once ``research_rounds >= 2``
for non-high confidence. This module is orchestration only — no business logic
lives here.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from backend.app.agents.confidence import route_research
from backend.app.graph import nodes
from backend.app.graph.state import ResearchState


def _research_graph_node(state):
    """Thin adapter: use research_node's default web/RAG behavior."""
    return nodes.research_node(state)


def _fact_check_graph_node(state):
    """Thin adapter: fact_check_node consumes ``state["claims"]`` produced by
    the claim extraction node (empty fact checks when no claims exist)."""
    return nodes.fact_check_node(state)


def _route_after_critic(state) -> str:
    """Thin adapter: delegate the post-research routing decision."""
    return route_research(
        confidence=state.get("confidence"),
        research_rounds=state.get("research_rounds") or 0,
    )


def _increment_rounds_node(state) -> dict:
    """Increment the research round counter before the next cycle."""
    return {"research_rounds": (state.get("research_rounds") or 0) + 1}


def build_research_graph():
    """Build and compile the linear research StateGraph."""
    graph = StateGraph(ResearchState)

    graph.add_node("plan", nodes.plan_node)
    graph.add_node("research", _research_graph_node)
    graph.add_node("evidence", nodes.evidence_node)
    graph.add_node("claim_extraction", nodes.claim_extraction_node)
    graph.add_node("fact_check", _fact_check_graph_node)
    graph.add_node("citation", nodes.citation_node)
    graph.add_node("confidence", nodes.confidence_node)
    graph.add_node("writer", nodes.writer_node)
    graph.add_node("critic", nodes.critic_node)
    graph.add_node("increment_rounds", _increment_rounds_node)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "research")
    graph.add_edge("research", "evidence")
    graph.add_edge("evidence", "claim_extraction")
    graph.add_edge("claim_extraction", "fact_check")
    graph.add_edge("fact_check", "citation")
    graph.add_edge("citation", "confidence")
    graph.add_edge("confidence", "writer")
    graph.add_edge("writer", "critic")

    # Conditional routing after the critic (existing route_research semantics).
    graph.add_conditional_edges(
        "critic",
        _route_after_critic,
        {
            "complete": END,
            "insufficient": END,
            "additional_research": "increment_rounds",
        },
    )
    graph.add_edge("increment_rounds", "research")

    return graph.compile()


# Module-level compiled graph (consistent with the module-level chain pattern).
research_graph = build_research_graph()
