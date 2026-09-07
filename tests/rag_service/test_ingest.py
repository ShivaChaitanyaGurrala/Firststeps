"""DataServiceClient and the vector store are both faked/local here (see
conftest.py's fake_vector_store) — no real HTTP call to data_service, no
Chroma Docker container, no Voyage embedding call needed to run this file.
"""

import time
from dataclasses import dataclass, field

import pytest

from rag_service import ingest


@dataclass
class _FakeDataServiceClient:
    pages: list  # list of pages, each a list[dict]
    calls: list = field(default_factory=list)

    def list_reviews(self, limit, offset):
        self.calls.append({"limit": limit, "offset": offset})
        page_index = offset // limit
        return self.pages[page_index] if page_index < len(self.pages) else []


def test_all_reviews_pages_until_an_empty_page():
    pages = [
        [{"id": f"r{i}"} for i in range(ingest._PAGE_SIZE)],  # full page
        [{"id": "r-last"}],  # short but non-empty page
    ]
    client = _FakeDataServiceClient(pages=pages)

    reviews = list(ingest._all_reviews(client))

    assert len(reviews) == ingest._PAGE_SIZE + 1
    assert reviews[-1]["id"] == "r-last"
    # A short-but-non-empty page doesn't stop the loop by itself (only an
    # empty page does) — so one extra request happens after it. Documenting
    # this rather than treating it as a bug: harmless, one wasted request
    # per full ingest run.
    assert len(client.calls) == 3


def test_all_reviews_empty_catalog_makes_one_call():
    client = _FakeDataServiceClient(pages=[[]])
    assert list(ingest._all_reviews(client)) == []
    assert len(client.calls) == 1


def test_ingest_one_builds_metadata_and_defaults_missing_rating(fake_vector_store):
    review = {
        "id": "r1",
        "title_id": 27205,
        "title": "Inception",
        "author": "alice",
        "rating": None,
        "content": "A genuinely good movie. " * 50,
    }

    chunk_count = ingest._ingest_one(fake_vector_store, review)

    assert chunk_count > 0
    stored = fake_vector_store.get(where={"review_id": "r1"}, include=["metadatas"])
    assert len(stored["metadatas"]) == chunk_count
    assert all(m["rating"] == 0.0 for m in stored["metadatas"])
    assert all(m["title"] == "Inception" for m in stored["metadatas"])
    assert {m["chunk_index"] for m in stored["metadatas"]} == set(range(chunk_count))


def test_ingest_one_with_retry_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def flaky_ingest_one(vector_store, review):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionResetError("simulated WinError 10054")
        return 5

    monkeypatch.setattr(ingest, "_ingest_one", flaky_ingest_one)
    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    result = ingest._ingest_one_with_retry(object(), {"id": "r1"})

    assert result == 5
    assert calls["n"] == 3
    assert sleeps == [ingest._RETRY_DELAY_SECONDS, ingest._RETRY_DELAY_SECONDS]


def test_ingest_one_with_retry_raises_after_exhausting_retries(monkeypatch):
    calls = {"n": 0}

    def always_fails(vector_store, review):
        calls["n"] += 1
        raise ConnectionResetError("simulated permanent failure")

    monkeypatch.setattr(ingest, "_ingest_one", always_fails)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    with pytest.raises(ConnectionResetError):
        ingest._ingest_one_with_retry(object(), {"id": "r1"})

    assert calls["n"] == ingest._MAX_INGEST_RETRIES + 1


def test_run_skips_reviews_already_in_the_vector_store(monkeypatch, capsys):
    fake_client = _FakeDataServiceClient(
        pages=[[{"id": "r1", "title_id": 1, "title": "T", "author": "a", "rating": 5.0, "content": "text"}]]
    )
    monkeypatch.setattr(ingest, "DataServiceClient", lambda: fake_client)
    monkeypatch.setattr(ingest, "get_vector_store", lambda: object())
    monkeypatch.setattr(ingest, "existing_review_ids", lambda vector_store: {"r1"})

    ingest.run()

    out = capsys.readouterr().out
    assert "examined=0 skipped=1 upserted=0 failed=0" in out


def test_run_ingests_new_reviews_and_counts_failures(monkeypatch, capsys, fake_vector_store):
    fake_client = _FakeDataServiceClient(
        pages=[
            [
                {"id": "r-good", "title_id": 1, "title": "T", "author": "a", "rating": 5.0, "content": "great movie plot"},
                {"id": "r-bad", "title_id": 1, "title": "T", "author": "a", "rating": 5.0, "content": "bad movie plot"},
            ]
        ]
    )
    monkeypatch.setattr(ingest, "DataServiceClient", lambda: fake_client)
    monkeypatch.setattr(ingest, "get_vector_store", lambda: fake_vector_store)
    monkeypatch.setattr(ingest, "existing_review_ids", lambda vector_store: set())

    real_retry = ingest._ingest_one_with_retry

    def flaky_retry(vector_store, review):
        if review["id"] == "r-bad":
            raise RuntimeError("boom")
        return real_retry(vector_store, review)

    monkeypatch.setattr(ingest, "_ingest_one_with_retry", flaky_retry)

    ingest.run()

    out = capsys.readouterr().out
    assert "examined=2 skipped=0 upserted=1 failed=1" in out
    assert "Failed to ingest review r-bad: boom" in out
