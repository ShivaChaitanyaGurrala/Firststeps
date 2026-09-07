"""RecursiveCharacterTextSplitter is local/free — no mocking needed here."""

from rag_service.chunking import chunk_review


def test_long_content_splits_into_sequential_chunks():
    content = "Sentence one is here. " * 100
    chunks = chunk_review("review-1", 27205, content)

    assert len(chunks) > 1
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert all(c.review_id == "review-1" for c in chunks)
    assert all(c.title_id == 27205 for c in chunks)


def test_short_content_produces_single_chunk():
    chunks = chunk_review("review-2", 1, "Short review.")
    assert len(chunks) == 1
    assert chunks[0].text == "Short review."
    assert chunks[0].chunk_index == 0


def test_empty_content_produces_no_chunks():
    assert chunk_review("review-3", 1, "") == []
