"""RateLimiter unit tests (pure sliding-window logic, no DB/HTTP needed) plus
one integration test confirming the middleware actually returns 429 once
tripped. See data_service/rate_limit.py for the mechanism being tested.
"""

import data_service.rate_limit as rate_limit_module
import data_service.main as main_module
from data_service.rate_limit import RateLimiter


def test_allow_within_limit(monkeypatch):
    fake_now = [0.0]
    monkeypatch.setattr(rate_limit_module.time, "monotonic", lambda: fake_now[0])
    limiter = RateLimiter(max_requests=3, window_seconds=10)

    assert limiter.allow("a") is True
    assert limiter.allow("a") is True
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False


def test_allow_resets_after_window_elapses(monkeypatch):
    fake_now = [0.0]
    monkeypatch.setattr(rate_limit_module.time, "monotonic", lambda: fake_now[0])
    limiter = RateLimiter(max_requests=1, window_seconds=5)

    assert limiter.allow("a") is True
    assert limiter.allow("a") is False

    fake_now[0] = 5.1  # just past the window
    assert limiter.allow("a") is True


def test_allow_keys_are_independent(monkeypatch):
    fake_now = [0.0]
    monkeypatch.setattr(rate_limit_module.time, "monotonic", lambda: fake_now[0])
    limiter = RateLimiter(max_requests=1, window_seconds=10)

    assert limiter.allow("a") is True
    assert limiter.allow("a") is False
    assert limiter.allow("b") is True  # different key, own budget


def test_middleware_returns_429_once_tripped(client, monkeypatch):
    monkeypatch.setattr(main_module, "_rate_limiter", RateLimiter(max_requests=2, window_seconds=10))

    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200

    resp = client.get("/health")
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


def test_middleware_allows_requests_under_the_limit(client, monkeypatch):
    monkeypatch.setattr(main_module, "_rate_limiter", RateLimiter(max_requests=5, window_seconds=10))

    for _ in range(5):
        assert client.get("/health").status_code == 200
