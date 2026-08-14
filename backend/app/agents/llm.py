"""LLM factory — the single place where the model is constructed."""
from functools import lru_cache

from langchain_groq import ChatGroq

from backend.app.core.config import settings


@lru_cache(maxsize=1)
def get_llm() -> ChatGroq:
    """Return a shared ``ChatGroq`` instance configured from settings."""
    return ChatGroq(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_retries=settings.llm_max_retries,
        api_key=settings.groq_api_key,
    )
