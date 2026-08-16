"""Application settings loaded from environment variables and ``.env``.

This is the single source of truth for configuration. Values are read from
environment variables first, then from the ``.env`` file at the project root.
"""
from typing import Annotated

from dotenv import load_dotenv
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Populate os.environ from .env so libraries that read env vars directly
# (e.g. ChatGroq) keep working even when not passed an explicit api_key.
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── API keys ──────────────────────────────────────────────────────────
    groq_api_key: str = ""
    # Accept both the canonical TAVILY_API_KEY and the existing (typo'd)
    # TAVILY_KEY_KEY found in the project .env, so nothing breaks.
    tavily_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("TAVILY_API_KEY", "TAVILY_KEY_KEY"),
    )
    google_api_key: str = ""

    # ── LLM ───────────────────────────────────────────────────────────────
    llm_model: str = "llama-3.1-8b-instant"
    llm_temperature: float = 0.0
    llm_max_retries: int = 2
    # Total attempts (incl. the first) made when Groq answers 429 rate-limited.
    llm_rate_limit_retries: int = 5

    # ── Research loop ─────────────────────────────────────────────────────
    # Max ADDITIONAL research rounds before the pipeline terminates. 0 = a
    # single pass (loop disabled), the free-tier-friendly default — every
    # extra round re-runs the whole pipeline and burns tokens.
    research_loop_max_rounds: int = 0

    # ── Token budget (free-tier friendly) ─────────────────────────────────
    # Max output tokens per LLM generation. Capping outputs keeps a single
    # pipeline pass inside Groq's 6000 TPM free-tier window.
    llm_max_tokens: int = 1536
    # Max chars of text kept per web-evidence item. The search summary is
    # shared across every source URL, so without a cap the same text gets
    # duplicated per source and inflates every downstream prompt.
    evidence_max_chars: int = 300
    # Max chars of each Tavily snippet kept in formatted search results.
    search_snippet_max_chars: int = 150
    # Run the critic review step? Off by default — the critic re-reads the
    # whole report (~2000+ tokens), the largest non-essential LLM call.
    # Enable on a higher tier.
    run_critic: bool = False

    # ── Web research ──────────────────────────────────────────────────────
    tavily_max_results: int = 5
    scrape_max_chars: int = 3000
    scrape_timeout: int = 8

    # ── Embeddings ────────────────────────────────────────────────────────
    embedding_provider: str = "google"
    embedding_model: str = "gemini-embedding-2"
    embedding_dim: int = 768

    # ── Qdrant vector store ───────────────────────────────────────────────
    # Local embedded mode (path) is the Phase 2 default; QDRANT_URL is
    # optional and reserved for switching to a remote/server Qdrant later.
    qdrant_path: str = "./qdrant_storage"
    qdrant_url: str | None = None
    qdrant_collection: str = "insightforge_documents"

    # ── Document chunking ─────────────────────────────────────────────────
    chunk_size: int = 1000
    chunk_overlap: int = 150

    # ── Retrieval ─────────────────────────────────────────────────────────
    retrieval_top_k: int = 5
    retrieval_score_threshold: float = 0.5

    # ── Storage ───────────────────────────────────────────────────────────
    document_storage_dir: str = "./data/documents"

    # ── API / CORS ────────────────────────────────────────────────────────
    # Comma-separated list of allowed CORS origins (the future Next.js dev
    # server). Explicit origins only — never "*".
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
    # How long terminal (completed/failed) jobs remain queryable before they
    # are cleaned up from the in-memory store.
    job_ttl_seconds: int = 3600

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


settings = Settings()
