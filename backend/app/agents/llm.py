"""LLM factory — the single place where the model is constructed."""
from __future__ import annotations

import asyncio
import logging
import re
import time
from functools import lru_cache
from typing import Any

from groq import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)
from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_groq import ChatGroq

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Groq 429 messages include a server-suggested wait, e.g.
# "Please try again in 33.759999999s." — parse it so we sleep just long
# enough for the per-minute token window to reset.
_RETRY_IN_MSG_RE = re.compile(r"try again in\s+([0-9.]+)\s*s", re.IGNORECASE)
_DEFAULT_RATE_LIMIT_WAIT_SECONDS = 15.0
_MAX_TRANSIENT_BACKOFF_SECONDS = 8.0


def parse_retry_seconds(message: str, headers=None) -> float | None:
    """Extract the server-suggested wait (seconds) from a 429 response.

    Checks the ``Retry-After`` header first, then the human-readable message
    Groq includes (``Please try again in 33.7s``). Returns ``None`` when no
    wait time can be found.
    """
    if headers is not None:
        retry_after = headers.get("retry-after")
        if retry_after:
            try:
                return float(retry_after)
            except (TypeError, ValueError):
                pass
    match = _RETRY_IN_MSG_RE.search(message)
    if match:
        try:
            return float(match.group(1))
        except (TypeError, ValueError):
            return None
    return None


class RateLimitResilientChatGroq(ChatGroq):
    """A ``ChatGroq`` that waits out 429 rate limits instead of crashing.

    A single research run makes many LLM calls (planner → search agent →
    claims → fact check → writer → critic), so on Groq's free tier (6000
    TPM) it regularly exceeds the per-minute budget and Groq answers 429
    with ``Please try again in ~30s``. The SDK's built-in retries use short
    exponential backoff and never wait that long.

    This subclass detects ``RateLimitError``, sleeps for the server-suggested
    delay (or a sane default), and retries. Transient server/network errors
    (5xx, connection/timeout) get a short exponential backoff. Both are
    capped at ``rate_limit_retries`` total attempts. The underlying SDK is
    configured with ``max_retries=0`` so all retry logic lives here and is
    deterministic.
    """

    rate_limit_retries: int = 5
    """Total attempts (including the first) made before giving up."""

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        last_error: Exception | None = None
        for attempt in range(1, self.rate_limit_retries + 1):
            try:
                return super()._generate(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )
            except RateLimitError as exc:
                last_error = exc
                if attempt == self.rate_limit_retries:
                    break
                wait = (
                    parse_retry_seconds(str(exc), exc.response.headers)
                    or _DEFAULT_RATE_LIMIT_WAIT_SECONDS
                )
                logger.warning(
                    "Groq rate limited; waiting %.1fs before retry (attempt %d/%d)",
                    wait,
                    attempt + 1,
                    self.rate_limit_retries,
                )
                time.sleep(wait)
            except (APIConnectionError, APITimeoutError, InternalServerError) as exc:
                last_error = exc
                if attempt == self.rate_limit_retries:
                    break
                time.sleep(min(2 ** (attempt - 1), _MAX_TRANSIENT_BACKOFF_SECONDS))
        assert last_error is not None
        raise last_error

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        last_error: Exception | None = None
        for attempt in range(1, self.rate_limit_retries + 1):
            try:
                return await super()._agenerate(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )
            except RateLimitError as exc:
                last_error = exc
                if attempt == self.rate_limit_retries:
                    break
                wait = (
                    parse_retry_seconds(str(exc), exc.response.headers)
                    or _DEFAULT_RATE_LIMIT_WAIT_SECONDS
                )
                logger.warning(
                    "Groq rate limited; waiting %.1fs before retry (attempt %d/%d)",
                    wait,
                    attempt + 1,
                    self.rate_limit_retries,
                )
                await asyncio.sleep(wait)
            except (APIConnectionError, APITimeoutError, InternalServerError) as exc:
                last_error = exc
                if attempt == self.rate_limit_retries:
                    break
                await asyncio.sleep(
                    min(2 ** (attempt - 1), _MAX_TRANSIENT_BACKOFF_SECONDS)
                )
        assert last_error is not None
        raise last_error


@lru_cache(maxsize=1)
def get_llm() -> RateLimitResilientChatGroq:
    """Return a shared, rate-limit-resilient ``ChatGroq`` from settings."""
    return RateLimitResilientChatGroq(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,  # cap output to fit the TPM budget
        max_retries=0,  # the wrapper owns all retry logic
        rate_limit_retries=settings.llm_rate_limit_retries,
        api_key=settings.groq_api_key,
    )
