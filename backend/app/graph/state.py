"""Typed state for the research pipeline.

``ResearchState`` is the shared data structure produced and consumed by the
research workflow. Today it is filled in by the sequential pipeline in
``backend.app.main``; in a later phase it becomes the LangGraph state schema.
"""
from typing import TypedDict


class ResearchState(TypedDict, total=False):
    """State produced/consumed by the InsightForge research pipeline.

    All fields are optional (``total=False``) so partial state can exist at
    every stage of the workflow.
    """

    query: str
    search_results: str
    sources: list[str]
    extracted_information: str
    report: str
    critic_feedback: str
    # Reserved for the fact-checking phase; not populated yet.
    critic_score: int | None
    errors: list[str]
