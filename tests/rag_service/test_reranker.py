"""cohere.Client is faked out entirely — Cohere's rerank endpoint is a paid
call and this project is deliberately budget-conscious about it (see the
25-call cap used for live manual testing). No test here should ever make a
real Cohere API call."""

from dataclasses import dataclass, field

import pytest

from rag_service import reranker
from rag_service.config import settings


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
    monkeypatch.setattr(reranker.cohere, "Client", lambda api_key: fake_client)

    hits = reranker.rerank("query", ["doc a", "doc b"], top_n=2)

    assert [h.index for h in hits] == [1, 0]
    assert [h.relevance_score for h in hits] == [0.9, 0.4]
    assert fake_client.calls[0]["query"] == "query"
    assert fake_client.calls[0]["documents"] == ["doc a", "doc b"]
    assert fake_client.calls[0]["top_n"] == 2
