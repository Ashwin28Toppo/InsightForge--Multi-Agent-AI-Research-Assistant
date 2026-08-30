"""Unit tests for the rate-limit-resilient LLM wrapper.

All tests are offline: the Groq HTTP client is monkeypatched with fakes, so no
network calls or API keys are required.
"""
import asyncio

import httpx
import pytest
from groq import APIConnectionError, RateLimitError

from backend.app.agents.llm import (
    RateLimitResilientChatGroq,
    get_llm,
    parse_retry_seconds,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _rate_limit_error(seconds: float = 1.5) -> RateLimitError:
    """Build a realistic Groq 429 error with the ``try again in Xs`` text."""
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    body = {
        "error": {
            "message": f"Rate limit reached. Please try again in {seconds}s.",
        }
    }
    response = httpx.Response(429, request=request, json=body)
    return RateLimitError(
        f"Error code: 429 - {body!r}",
        response=response,
        body=body,
    )


def _fake_completion(text: str = "hello") -> dict:
    """A minimal ChatCompletion-shaped dict parsed by ``_create_chat_result``."""
    return {
        "id": "chatcmpl_test",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
                "logprobs": None,
            }
        ],
        "created": 1700000000,
        "model": "test-model",
        "object": "chat.completion",
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    }


def _make_model(rate_limit_retries: int = 3, **overrides) -> RateLimitResilientChatGroq:
    return RateLimitResilientChatGroq(
        model="test-model",
        api_key="test-key",
        max_retries=0,
        rate_limit_retries=rate_limit_retries,
        **overrides,
    )


# ── parse_retry_seconds ─────────────────────────────────────────────────────


def test_parse_retry_seconds_from_message():
    assert parse_retry_seconds("Please try again in 33.759999999s.") == pytest.approx(33.76)


def test_parse_retry_seconds_from_retry_after_header():
    headers = httpx.Headers({"retry-after": "12.5"})
    assert parse_retry_seconds("no message hint", headers=headers) == pytest.approx(12.5)


def test_parse_retry_seconds_returns_none_when_absent():
    assert parse_retry_seconds("rate limited") is None
    assert parse_retry_seconds("rate limited", headers=httpx.Headers({"x-x": "1"})) is None


# ── Factory ─────────────────────────────────────────────────────────────────


def test_get_llm_returns_resilient_chat_groq():
    assert isinstance(get_llm(), RateLimitResilientChatGroq)


# ── Sync path ───────────────────────────────────────────────────────────────


def test_generate_waits_out_rate_limit_and_succeeds(monkeypatch):
    model = _make_model(rate_limit_retries=3)
    calls = {"n": 0}
    sleeps: list[float] = []

    def flaky_create(messages, **kwargs):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise _rate_limit_error(seconds=0.25)
        return _fake_completion("final answer")

    monkeypatch.setattr(model.client, "create", flaky_create)
    monkeypatch.setattr("backend.app.agents.llm.time.sleep", sleeps.append)

    result = model.invoke("hi")

    assert calls["n"] == 3
    assert result.content == "final answer"
    assert sleeps == [0.25, 0.25]  # waited for the server-suggested delay


def test_generate_gives_up_after_exhausting_retries(monkeypatch):
    model = _make_model(rate_limit_retries=3)
    calls = {"n": 0}

    def always_429(messages, **kwargs):
        calls["n"] += 1
        raise _rate_limit_error(seconds=0.25)

    monkeypatch.setattr(model.client, "create", always_429)
    monkeypatch.setattr("backend.app.agents.llm.time.sleep", lambda s: None)

    with pytest.raises(RateLimitError):
        model.invoke("hi")
    assert calls["n"] == 3


def test_generate_backs_off_on_transient_errors(monkeypatch):
    model = _make_model(rate_limit_retries=3)
    calls = {"n": 0}
    sleeps: list[float] = []

    def flaky_create(messages, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise APIConnectionError(
                message="connection reset",
                request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
            )
        return _fake_completion("ok")

    monkeypatch.setattr(model.client, "create", flaky_create)
    monkeypatch.setattr("backend.app.agents.llm.time.sleep", sleeps.append)

    result = model.invoke("hi")

    assert calls["n"] == 2
    assert result.content == "ok"
    assert sleeps == [1.0]  # 2**(attempt-1) with attempt=1


# ── Async path ──────────────────────────────────────────────────────────────


def test_agenerate_waits_out_rate_limit_and_succeeds(monkeypatch):
    model = _make_model(rate_limit_retries=3)
    calls = {"n": 0}

    async def flaky_create(messages, **kwargs):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise _rate_limit_error(seconds=0.25)
        return _fake_completion("async answer")

    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr(model.async_client, "create", flaky_create)
    monkeypatch.setattr("backend.app.agents.llm.asyncio.sleep", _no_sleep)

    result = asyncio.run(model.ainvoke("hi"))

    assert calls["n"] == 3
    assert result.content == "async answer"
