"""Compiled LangGraph for the linear research workflow (Phase 2C Step 2).

Topology (linear pass only, no conditional routing / loops yet):

    START
      ↓
    plan
      ↓
    research
      ↓
    evidence
      ↓
    fact_check
      ↓
    citation
      ↓
    confidence
      ↓
    writer
      ↓
    critic
      ↓
    END

``route_research`` integration (confidence-based routing) and the research
retry loop arrive in a later step.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from backend.app.graph import nodes
from backend.app.graph.state import ResearchState


def _research_graph_node(state):
    """Thin adapter: use research_node's default web/RAG behavior."""
    return nodes.research_node(state)


def _fact_check_graph_node(state):
    """Thin adapter: ResearchState has no claims field yet (claim extraction is
    a later step), so fact_check_node runs with no claims and returns empty
    fact checks — preserving the Phase 2C Step 1 behavior."""
    return nodes.fact_check_node(state)


def build_research_graph():
    """Build and compile the linear research StateGraph."""
    graph = StateGraph(ResearchState)

    graph.add_node("plan", nodes.plan_node)
    graph.add_node("research", _research_graph_node)
    graph.add_node("evidence", nodes.evidence_node)
    graph.add_node("fact_check", _fact_check_graph_node)
    graph.add_node("citation", nodes.citation_node)
    graph.add_node("confidence", nodes.confidence_node)
    graph.add_node("writer", nodes.writer_node)
    graph.add_node("critic", nodes.critic_node)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "research")
    graph.add_edge("research", "evidence")
    graph.add_edge("evidence", "fact_check")
    graph.add_edge("fact_check", "citation")
    graph.add_edge("citation", "confidence")
    graph.add_edge("confidence", "writer")
    graph.add_edge("writer", "critic")
    graph.add_edge("critic", END)

    return graph.compile()


# Module-level compiled graph (consistent with the module-level chain pattern).
research_graph = build_research_graph()
