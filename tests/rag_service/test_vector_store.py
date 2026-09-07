from rag_service.vector_store import existing_review_ids, upsert_chunks


def test_upsert_and_existing_review_ids_roundtrip(fake_vector_store):
    upsert_chunks(
        fake_vector_store,
        chunk_ids=["r1:0", "r1:1"],
        texts=["chunk one", "chunk two"],
        metadatas=[
            {"review_id": "r1", "title_id": 1, "title": "T", "author": "A", "rating": 8.0, "chunk_index": 0},
            {"review_id": "r1", "title_id": 1, "title": "T", "author": "A", "rating": 8.0, "chunk_index": 1},
        ],
    )
    assert existing_review_ids(fake_vector_store) == {"r1"}


def test_upsert_overwrites_by_id_instead_of_duplicating(fake_vector_store):
    metadata = {"review_id": "r2", "title_id": 2, "title": "T2", "author": "A2", "rating": 5.0, "chunk_index": 0}
    upsert_chunks(fake_vector_store, ["r2:0"], ["original text"], [metadata])
    upsert_chunks(fake_vector_store, ["r2:0"], ["updated text"], [metadata])

    stored = fake_vector_store.get(ids=["r2:0"])
    assert stored["documents"] == ["updated text"]


def test_existing_review_ids_empty_when_nothing_stored(fake_vector_store):
    assert existing_review_ids(fake_vector_store) == set()


def test_upsert_chunks_silently_drops_none_metadata_values(fake_vector_store):
    """Verified against the real client (not assumed): a None metadata value
    doesn't raise — Chroma just drops that key entirely from the stored
    metadata. This is actually why ingest.py's rating-defaulting to 0.0
    matters: without it, an unrated review would ingest "successfully" but
    with no `rating` key at all, and retriever.py's
    `candidate.metadata["rating"]` would raise KeyError later, at query
    time, on a totally different code path than ingestion — a much harder
    bug to trace back to its source than a loud failure during ingest would
    have been."""
    metadata = {"review_id": "r3", "title_id": 3, "title": "T3", "author": "A3", "rating": None, "chunk_index": 0}
    upsert_chunks(fake_vector_store, ["r3:0"], ["text"], [metadata])

    stored = fake_vector_store.get(ids=["r3:0"], include=["metadatas"])
    assert "rating" not in stored["metadatas"][0]
