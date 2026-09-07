"""retrieve_chunks (retriever.search, imported into main.py's namespace) is
faked here — a real call would hit Chroma/Voyage and Cohere. This file only
tests the FastAPI route wiring/response shaping, not retrieval quality."""

from fastapi.testclient import TestClient

from rag_service import main as main_module
from rag_service.main import app


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_search_calls_retriever_and_shapes_response(monkeypatch):
    def fake_retrieve_chunks(query, top_n, title_id):
        assert query == "great movie"
        assert top_n == 1
        assert title_id is None
        return [
            {
                "review_id": "r1",
                "title_id": 1,
                "title": "T",
                "chunk_text": "text",
                "author": "a",
                "rating": 8.0,
                "score": 0.9,
            }
        ]

    monkeypatch.setattr(main_module, "retrieve_chunks", fake_retrieve_chunks)

    with TestClient(app) as client:
        resp = client.get("/search", params={"query": "great movie", "limit": 1})

    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "great movie"
    assert body["results"] == [
        {
            "review_id": "r1",
            "title_id": 1,
            "title": "T",
            "chunk_text": "text",
            "author": "a",
            "rating": 8.0,
            "score": 0.9,
        }
    ]


def test_search_passes_title_id_through(monkeypatch):
    captured = {}

    def fake_retrieve_chunks(query, top_n, title_id):
        captured["title_id"] = title_id
        return []

    monkeypatch.setattr(main_module, "retrieve_chunks", fake_retrieve_chunks)

    with TestClient(app) as client:
        client.get("/search", params={"query": "x", "title_id": 27205})

    assert captured["title_id"] == 27205


def test_search_limit_out_of_range_returns_422():
    with TestClient(app) as client:
        resp = client.get("/search", params={"query": "x", "limit": 100})
    assert resp.status_code == 422
