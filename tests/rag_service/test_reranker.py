"""cohere.Client is faked out entirely — Cohere's rerank endpoint is a paid
call and this project is deliberately budget-conscious about it (see the
25-call cap used for live manual testing). No test here should ever make a
real Cohere API call."""

from dataclasses import dataclass, field

from cohere.core.api_error import ApiError
from cohere.errors import TooManyRequestsError
import httpx
import pytest

from rag_service import reranker
from rag_service.config import settings
from rag_service.errors import RerankUnavailableError


@dataclass
class _FakeResultItem:
    index: int
    relevance_score: float


@dataclass
class _FakeRerankResponse:
    results: list


@dataclass
class _FakeCohereClient:
    api_key: str
    calls: list = field(default_factory=list)

    def rerank(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeRerankResponse(
            results=[
                _FakeResultItem(index=1, relevance_score=0.9),
                _FakeResultItem(index=0, relevance_score=0.4),
            ]
        )


def test_raises_when_api_key_missing(monkeypatch):
    monkeypatch.setattr(settings, "cohere_api_key", "")
    with pytest.raises(RuntimeError, match="COHERE_API_KEY"):
        reranker.rerank("query", ["a", "b"])


def test_rerank_maps_response_into_hits_best_first(monkeypatch):
    monkeypatch.setattr(settings, "cohere_api_key", "fake-key")
    fake_client = _FakeCohereClient(api_key="fake-key")
    monkeypatch.setattr(reranker.cohere, "Client", lambda api_key, **kwargs: fake_client)

    hits = reranker.rerank("query", ["doc a", "doc b"], top_n=2)

    assert [h.index for h in hits] == [1, 0]
    assert [h.relevance_score for h in hits] == [0.9, 0.4]
    assert fake_client.calls[0]["query"] == "query"
    assert fake_client.calls[0]["documents"] == ["doc a", "doc b"]
    assert fake_client.calls[0]["top_n"] == 2


class _FailingCohereClient:
    def __init__(self, exc):
        self.exc = exc
        self.calls = 0

    def rerank(self, **kwargs):
        self.calls += 1
        raise self.exc


@pytest.fixture
def failing_client(monkeypatch):
    """Returns a helper installing a Cohere client that always raises `exc`.
    Records the constructor kwargs and sleeps instead of really sleeping."""
    monkeypatch.setattr(settings, "cohere_api_key", "fake-key")
    captured = {"sleeps": [], "client_kwargs": None}
    monkeypatch.setattr(reranker.time, "sleep", captured["sleeps"].append)

    def install(exc):
        client = _FailingCohereClient(exc)

        def factory(api_key, **kwargs):
            captured["client_kwargs"] = kwargs
            return client

        monkeypatch.setattr(reranker.cohere, "Client", factory)
        captured["client"] = client
        return captured

    return install


def test_live_policy_fits_inside_mcp_read_timeout():
    p = reranker.LIVE_RETRY
    sleep_total = sum(p.backoff_seconds * (i + 1) for i in range(p.max_attempts - 1))
    assert p.max_attempts * p.request_timeout_seconds + sleep_total < 20


def test_live_429_makes_one_call_and_fails_fast(failing_client):
    captured = failing_client(TooManyRequestsError(body="slow down"))

    with pytest.raises(RerankUnavailableError) as exc_info:
        reranker.rerank("query", ["a"])

    assert captured["client"].calls == 1
    assert captured["sleeps"] == []
    assert exc_info.value.retry_after_seconds == 60


def test_batch_policy_keeps_the_long_backoff(failing_client):
    captured = failing_client(TooManyRequestsError(body="slow down"))

    with pytest.raises(RerankUnavailableError):
        reranker.rerank("query", ["a"], retry=reranker.BATCH_RETRY)

    assert captured["client"].calls == 5
    assert captured["sleeps"] == [10, 20, 30, 40]


def test_sdk_internal_retries_are_off_and_timeout_is_set(failing_client):
    captured = failing_client(httpx.ReadTimeout("timed out"))

    with pytest.raises(RerankUnavailableError) as exc_info:
        reranker.rerank("query", ["a"])

    assert captured["client_kwargs"] == {"timeout": 5, "max_retries": 0}
    assert captured["client"].calls == 1
    assert exc_info.value.retry_after_seconds == 5


def test_non_transient_cohere_error_is_not_retried(failing_client):
    captured = failing_client(ApiError(status_code=400, body="bad request"))

    with pytest.raises(ApiError):
        reranker.rerank("query", ["a"], retry=reranker.BATCH_RETRY)

    assert captured["client"].calls == 1
    assert captured["sleeps"] == []
