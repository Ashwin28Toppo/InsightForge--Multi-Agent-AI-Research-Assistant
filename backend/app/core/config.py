"""Application settings loaded from environment variables and ``.env``.

This is the single source of truth for configuration. Values are read from
environment variables first, then from the ``.env`` file at the project root.
"""
from dotenv import load_dotenv
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

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

    # ── LLM ───────────────────────────────────────────────────────────────
    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.0
    llm_max_retries: int = 2

    # ── Web research ──────────────────────────────────────────────────────
    tavily_max_results: int = 5
    scrape_max_chars: int = 3000
    scrape_timeout: int = 8


settings = Settings()
