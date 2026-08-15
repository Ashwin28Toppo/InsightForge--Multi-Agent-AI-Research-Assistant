"""FastAPI transport layer for the InsightForge research pipeline.

This module is intentionally THIN: it exposes the existing application-layer
entry point (``backend.app.main.run_research_pipeline``) over HTTP and contains
no research/business logic. Orchestration stays in the compiled LangGraph
(``backend.app.graph.graph``); nothing here creates a graph, agent, chain, or
tool.

Endpoints:
    GET  /health    - liveness probe (never executes the pipeline).
    POST /research  - run the existing research pipeline for a query.
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, field_validator

from backend.app.main import run_research_pipeline

app = FastAPI(
    title="InsightForge API",
    description=(
        "Multi-Agent AI Research Assistant — exposes the existing LangGraph "
        "research pipeline over HTTP. Thin transport layer only."
    ),
    version="0.1.0",
)


class ResearchRequest(BaseModel):
    """Request body for ``POST /research``."""

    query: str

    @field_validator("query")
    @classmethod
    def _query_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must not be empty or whitespace-only")
        return stripped


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Does not execute the research pipeline."""
    return {"status": "ok"}


@app.post("/research")
def research(request: ResearchRequest) -> dict:
    """Run the existing research pipeline for the given query.

    Delegates to ``run_research_pipeline`` (the application layer), which owns
    the compiled LangGraph orchestration. Returns the application result
    unchanged — the API adds no fields of its own.
    """
    return run_research_pipeline(request.query)
