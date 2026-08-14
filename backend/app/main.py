"""Core research pipeline for InsightForge.

Owns the orchestration that previously lived inside the Streamlit app
(``app.py``). This module is UI-agnostic so it can be reused by a CLI,
Streamlit, and (in later phases) FastAPI.

The current implementation is a sequential Python pipeline; it will be
replaced by a LangGraph ``StateGraph`` in a later phase.
"""
from __future__ import annotations

from typing import Callable, Optional

from langchain.agents import create_agent

from backend.app.agents.critic import critic_chain
from backend.app.agents.llm import get_llm
from backend.app.agents.writer import writer_chain
from backend.app.graph.state import ResearchState
from backend.app.tools.web import extract_urls, scrape_url, web_search


def build_search_agent():
    """Build the search agent: an LLM with the Tavily web-search tool."""
    return create_agent(model=get_llm(), tools=[web_search])


def build_reader_agent():
    """Build the reader agent: an LLM with the URL extraction tool."""
    return create_agent(model=get_llm(), tools=[scrape_url])


def build_research_context(search_results: str, extracted_information: str) -> str:
    """Combine search + extracted content into the writer's research block."""
    return (
        f"SEARCH RESULTS : \n {search_results} \n\n"
        f"DETAILED SCRAPED CONTENT : \n {extracted_information}"
    )


def run_research_pipeline(
    query: str,
    on_step: Optional[Callable[[str], None]] = None,
) -> ResearchState:
    """Run the full research pipeline: search → extract → write → critique.

    Args:
        query: The research topic.
        on_step: Optional callback invoked with the current step name
            (``"search"``, ``"reader"``, ``"writer"``, ``"critic"``) before
            each stage, so the UI can surface progress.

    Returns:
        A completed :class:`ResearchState`.
    """
    state: ResearchState = {"query": query, "errors": []}

    # ── Step 1: Search agent ──────────────────────────────────────────────
    if on_step:
        on_step("search")
    search_agent = build_search_agent()
    search_result = search_agent.invoke({
        "messages": [("user", f"Find recent, reliable and detailed information about: {query}")]
    })
    state["search_results"] = search_result["messages"][-1].content
    # The final message is a prose summary; the actual URLs live in the
    # intermediate tool-result messages, so scan the whole history.
    all_messages_text = "\n".join(
        m.content for m in search_result["messages"] if isinstance(m.content, str)
    )
    state["sources"] = extract_urls(all_messages_text)

    # ── Step 2: Reader agent (extraction) ─────────────────────────────────
    if on_step:
        on_step("reader")
    reader_agent = build_reader_agent()
    reader_result = reader_agent.invoke({
        "messages": [("user",
            f"Based on the following search results about '{query}', "
            f"pick the most relevant URL and scrape it for deeper content.\n\n"
            f"Search Results:\n{state['search_results'][:800]}"
        )]
    })
    state["extracted_information"] = reader_result["messages"][-1].content

    # ── Step 3: Writer chain ──────────────────────────────────────────────
    if on_step:
        on_step("writer")
    research_combined = build_research_context(
        state["search_results"], state["extracted_information"]
    )
    state["report"] = writer_chain.invoke({
        "topic": query,
        "research": research_combined,
    })

    # ── Step 4: Critic chain ──────────────────────────────────────────────
    if on_step:
        on_step("critic")
    state["critic_feedback"] = critic_chain.invoke({"report": state["report"]})

    return state


if __name__ == "__main__":
    topic = input("\n Enter a research topic : ")
    result = run_research_pipeline(topic)
    print("\n Final Report\n", result["report"])
    print("\n Critic feedback\n", result["critic_feedback"])
