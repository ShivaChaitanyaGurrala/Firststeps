"""Batch job: pull review content from data_service, chunk + embed every
review, and upsert into Chroma.

rag_service never reads Postgres directly — it walks data_service's
GET /reviews (paginated, title_id omitted = whole catalog) via
http_client.DataServiceClient, the same "pull what you need over HTTP from
whoever owns that store" boundary mcp_server keeps everywhere.

No SyncRun-style audit row here (unlike data_service's bulk_seed/daily_sync/
fetch_reviews) — SyncRun lives in data_service's Postgres, which rag_service
deliberately doesn't touch. If you want auditability for ingestion runs,
that's an open design question: log locally, or add a small audit
mechanism data_service exposes an endpoint for. Not decided here.

Incremental re-runs: run() queries Chroma itself for review_ids already
embedded (vector_store.existing_review_ids) and skips them, rather than
tracking ingested ids in a separate local file — Chroma is already the
source of truth for "has this been embedded," so a second copy of that
state would just be one more thing to keep in sync. This also means a
review that failed mid-run (e.g. the connection-reset storm this dev
environment is prone to — see the retry constants below) gets picked up
automatically on the next run, since it was never actually written.

Usage (once implemented):
    python -m rag_service.ingest
"""

import time
from typing import Iterator

from rag_service.chunking import chunk_review
from rag_service.http_client import DataServiceClient
from rag_service.vector_store import existing_review_ids, get_vector_store, upsert_chunks

_PAGE_SIZE = 100

# Mirrors tmdb_client.py's connect-retry shape (bounded retries, short fixed
# delay) applied per-review instead of per-HTTP-call: a live run showed an
# ~86% failure rate, entirely WinError 10054/10053 connection resets — this
# dev environment's known HTTPS flakiness (same root cause as tmdb_client.py's
# retry, just hitting Voyage/Chroma instead of TMDB this time). Broad
# `Exception` catch here (not a narrower transport-only type like
# tmdb_client.py uses) because the embed+upsert step crosses two different
# HTTP stacks (voyageai's requests-based client, Chroma's own client) with
# different exception hierarchies, and there's no single transient-failure
# type common to both worth importing just for this.
_MAX_INGEST_RETRIES = 4
_RETRY_DELAY_SECONDS = 1.0


def _all_reviews(client: DataServiceClient) -> Iterator[dict]:
    """Page through GET /reviews until data_service returns fewer than
    _PAGE_SIZE results (i.e. the last page).

    TODO(you): loop calling client.list_reviews(limit=_PAGE_SIZE,
    offset=offset), incrementing offset by _PAGE_SIZE each time, collecting
    results, stopping when a page comes back shorter than _PAGE_SIZE (or
    empty).
    """

    for offset in range(
        0, 10000, _PAGE_SIZE
    ):  # Arbitrary upper limit to avoid infinite loop
        reviews = client.list_reviews(limit=_PAGE_SIZE, offset=offset)
        if not reviews:
            break
        yield from reviews


def _ingest_one(vector_store, review: dict) -> int:
    """Chunk one review (a dict from data_service's ReviewOut JSON, not an
    ORM row — rag_service has no ORM) and upsert its chunks into Chroma.
    Returns the number of chunks written.

    Takes vector_store rather than building one itself — see
    vector_store.upsert_chunks's docstring for why (built once per run(),
    not rebuilt per review).
    """
    chunks = chunk_review(review["id"], review["title_id"], review["content"])
    chunk_ids = [f"{review['id']}:{c.chunk_index}" for c in chunks]
    texts = [c.text for c in chunks]
    metadatas = [
        {
            "review_id": review["id"],
            "title_id": review["title_id"],
            "title": review["title"],
            "author": review["author"],
            "rating": review["rating"] if review["rating"] is not None else 0.0,
            "chunk_index": c.chunk_index,
        }
        for c in chunks
    ]
    upsert_chunks(vector_store, chunk_ids, texts, metadatas)
    return len(chunks)


def _ingest_one_with_retry(vector_store, review: dict) -> int:
    """_ingest_one, retrying a bounded number of times on transient
    connection failures before giving up on this one review. See the
    _MAX_INGEST_RETRIES comment above for why this exists and why the catch
    is broad."""
    for attempt in range(_MAX_INGEST_RETRIES + 1):
        try:
            return _ingest_one(vector_store, review)
        except Exception:
            if attempt == _MAX_INGEST_RETRIES:
                raise
            time.sleep(_RETRY_DELAY_SECONDS)
    raise RuntimeError("unreachable")  # loop always returns or raises above


def run() -> None:
    """Pull every review from data_service (skipping ones already embedded
    in a prior run — see existing_review_ids), chunk+embed+upsert each into
    Chroma, and print an examined/skipped/upserted/failed summary. See this
    file's module docstring on why there's no SyncRun row to write it to
    instead.
    """
    client = DataServiceClient()
    vector_store = get_vector_store()
    already_ingested = existing_review_ids(vector_store)

    examined = skipped = upserted = failed = 0
    for review in _all_reviews(client):
        if review["id"] in already_ingested:
            skipped += 1
            continue
        examined += 1
        try:
            _ingest_one_with_retry(vector_store, review)
            upserted += 1
        except Exception as e:
            failed += 1
            print(f"Failed to ingest review {review['id']}: {e}")
    print(
        f"Done. examined={examined} skipped={skipped} "
        f"upserted={upserted} failed={failed}"
    )


def main() -> None:
    run()


if __name__ == "__main__":
    main()
