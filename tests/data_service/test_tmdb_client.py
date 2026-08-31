"""TmdbClient._get retry/backoff tests — transport-error retries and 429
rate-limit handling — using httpx.MockTransport so nothing here makes a
real network call to TMDB. asyncio.sleep is monkeypatched to a no-op that
records requested delays, so these tests run fast instead of actually
waiting out the real backoff schedule.
"""

import asyncio

import httpx
import pytest

from data_service.tmdb_client import (
    TmdbClient,
    _MAX_CONNECT_RETRIES,
    _MAX_RATE_LIMIT_RETRIES,
    _RATE_LIMIT_JITTER_SECONDS,
    _rate_limit_delay,
)


def _client_with_handler(handler) -> TmdbClient:
    transport = httpx.MockTransport(handler)
    return TmdbClient(client=httpx.AsyncClient(transport=transport))


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    calls = []

    async def fake_sleep(seconds):
        calls.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return calls


# ---- _rate_limit_delay (pure function, no async/transport needed) ----


def test_rate_limit_delay_uses_retry_after_seconds():
    assert _rate_limit_delay("3", rate_limit_attempts=0) == 3.0


def test_rate_limit_delay_falls_back_on_non_numeric_retry_after():
    delay = _rate_limit_delay("Wed, 21 Oct 2026 07:28:00 GMT", rate_limit_attempts=1)
    # falls through to exponential+jitter: 2**1 <= delay < 2**1 + jitter
    assert 2 <= delay < 2 + _RATE_LIMIT_JITTER_SECONDS


def test_rate_limit_delay_exponential_with_jitter_when_no_header():
    for attempt in range(4):
        delay = _rate_limit_delay(None, rate_limit_attempts=attempt)
        assert 2**attempt <= delay < 2**attempt + _RATE_LIMIT_JITTER_SECONDS


# ---- transport-error retry path ----


async def test_get_succeeds_without_retry_when_first_call_works():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"ok": True})

    client = _client_with_handler(handler)
    result = await client._get("https://api.themoviedb.org/3/movie/1", {})
    assert result == {"ok": True}
    assert len(calls) == 1


async def test_get_retries_on_transport_error_then_succeeds():
    attempts = {"n": 0}

    def handler(request):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200, json={"ok": True})

    client = _client_with_handler(handler)
    result = await client._get("https://api.themoviedb.org/3/movie/1", {})
    assert result == {"ok": True}
    assert attempts["n"] == 3


async def test_get_gives_up_after_max_connect_retries():
    attempts = {"n": 0}

    def handler(request):
        attempts["n"] += 1
        raise httpx.ConnectError("boom", request=request)

    client = _client_with_handler(handler)
    with pytest.raises(httpx.TransportError):
        await client._get("https://api.themoviedb.org/3/movie/1", {})
    assert attempts["n"] == _MAX_CONNECT_RETRIES + 1


async def test_get_404_is_not_retried():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(404, json={"status_message": "not found"})

    client = _client_with_handler(handler)
    with pytest.raises(httpx.HTTPStatusError):
        await client._get("https://api.themoviedb.org/3/movie/999999", {})
    assert len(calls) == 1


# ---- 429 rate-limit retry path ----


async def test_get_retries_on_429_with_retry_after_then_succeeds(_no_real_sleep):
    attempts = {"n": 0}

    def handler(request):
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "1"}, json={})
        return httpx.Response(200, json={"ok": True})

    client = _client_with_handler(handler)
    result = await client._get("https://api.themoviedb.org/3/movie/1", {})
    assert result == {"ok": True}
    assert attempts["n"] == 2
    assert _no_real_sleep == [1.0]


async def test_get_retries_on_429_without_header_uses_backoff():
    attempts = {"n": 0}

    def handler(request):
        attempts["n"] += 1
        if attempts["n"] <= 2:
            return httpx.Response(429, json={})
        return httpx.Response(200, json={"ok": True})

    client = _client_with_handler(handler)
    result = await client._get("https://api.themoviedb.org/3/movie/1", {})
    assert result == {"ok": True}
    assert attempts["n"] == 3


async def test_get_429_exhausted_raises_http_status_error():
    attempts = {"n": 0}

    def handler(request):
        attempts["n"] += 1
        return httpx.Response(429, json={})

    client = _client_with_handler(handler)
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client._get("https://api.themoviedb.org/3/movie/1", {})
    assert exc_info.value.response.status_code == 429
    # 1 initial + _MAX_RATE_LIMIT_RETRIES retries, all within the same
    # outer connect-retry attempt (no TransportError occurred)
    assert attempts["n"] == _MAX_RATE_LIMIT_RETRIES + 1
