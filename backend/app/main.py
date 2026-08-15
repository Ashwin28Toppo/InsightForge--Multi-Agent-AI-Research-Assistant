"""Core research pipeline for InsightForge.

Owns the application's research execution path. This module is UI-agnostic so
it can be reused by a CLI, Streamlit, and (in later phases) FastAPI.

All orchestration is delegated to the compiled LangGraph
(``backend.app.graph.graph``); this module only passes the user's query into
the graph and maps the final state to the application's result contract.
"""
from __future__ import annotations

from typing import Callable, Optional

from langchain.agents import create_agent

from backend.app.agents.critic import critic_chain
from backend.app.agents.llm import get_llm
from backend.app.agents.writer import writer_chain
from backend.app.graph.graph import research_graph
from backend.app.graph.state import ResearchState
from backend.app.tools.web import extract_urls, scrape_url, web_search


_SEARCH_SYSTEM_PROMPT = (
    "You are a web researcher. You have one tool, web_search.\n"
    "Perform exactly 1 search for the user's topic, then reply with:\n"
    "1) a concise factual summary paragraph, and\n"
    "2) the source URLs you used, one per line.\n"
    "Do not call web_search more than once."
)


def build_search_agent():
    """Build the search agent: an LLM with the Tavily web-search tool.

    A concise system prompt keeps the agent from looping into many
    back-to-back searches. On Groq's free tier every accumulated tool result
    inflates the request, and a single call can exceed the 6000 TPM budget
    (HTTP 413 "Request too large").
    """
    return create_agent(
        model=get_llm(),
        tools=[web_search],
        system_prompt=_SEARCH_SYSTEM_PROMPT,
    )


def build_reader_agent():
    """Build the reader agent: an LLM with the URL extraction tool."""
    return create_agent(model=get_llm(), tools=[scrape_url])


def build_research_context(search_results: str, extracted_information: str) -> str:
    """Combine search + extracted content into the writer's research block."""
    return (
        f"SEARCH RESULTS : \n {search_results} \n\n"
        f"DETAILED SCRAPED CONTENT : \n {extracted_information}"
    )


def _to_application_result(state: dict) -> ResearchState:
    """Map the compiled graph's final state to the application result contract.

    The app expects the final report under ``report``, while the graph stores
    the writer output as ``report_draft``; all other keys pass through.
    """
    mapped: ResearchState = dict(state)
    if "report_draft" in mapped:
        mapped["report"] = mapped["report_draft"]
    mapped.setdefault("errors", [])
    return mapped


def run_research_pipeline(
    query: str,
    on_step: Optional[Callable[[str], None]] = None,
) -> ResearchState:
    """Run the full research workflow through the compiled LangGraph.

    The graph owns all orchestration (plan → research → evidence →
    claim_extraction → fact_check → citation → confidence → writer → critic →
    conditional routing); this function only passes the query into the graph
    and maps the final state to the application's result contract.

    Args:
        query: The research topic.
        on_step: Optional callback invoked with the name of each graph node
            as it completes (drives the Streamlit live-status box).

    Returns:
        The application-level result (``report``, ``search_results``,
        ``sources``, ``critic_feedback``, etc.).
    """
    final_state: dict = {}
    for chunk in research_graph.stream({"query": query}, stream_mode="updates"):
        for node, update in chunk.items():
            if isinstance(update, dict):
                final_state.update(update)
                if on_step is not None:
                    on_step(node)
    return _to_application_result(final_state)


if __name__ == "__main__":
    topic = input("\n Enter a research topic : ")
    result = run_research_pipeline(topic)
    print("\n Final Report\n", result["report"])
    print("\n Critic feedback\n", result["critic_feedback"])
