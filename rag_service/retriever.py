"""Two-stage retrieval: broad recall via vector similarity, then precise
reranking over that smaller candidate set.

Why two stages instead of just returning Chroma's top-k directly: an
embedding similarity search is fast (approximate nearest-neighbor over
however many chunks are stored) but comparatively coarse — it scores query
and document independently and compares their vectors, so it can miss
subtler relevance signals. A cross-encoder reranker (reranker.py) scores
the query and each candidate document TOGETHER in one pass, which is far
more accurate but too slow to run over an entire corpus. So: cast a wide
net cheaply (fetch_k candidates from Chroma), then spend the expensive
cross-encoder pass only on that narrower set, returning the best `top_n`.
This is the standard two-stage RAG retrieval pattern, not something
specific to this project's dataset.

This module returns fully-formed hit dicts (review_id, title_id, title,
chunk_text, author, rating, score) straight from Chroma's metadata — no
call back to data_service on the query path, because vector_store.py's
upsert_chunks already denormalized title/author/rating into that metadata
at ingest time (see its docstring for the tradeoff that accepts). This is
what keeps rag_service usable directly as M5's LangGraph retriever without
either a data_service round-trip per query or web-layer response shapes
leaking in here.
"""

from rag_service.reranker import rerank
from rag_service.vector_store import get_vector_store

_DEFAULT_FETCH_K = 20  # candidates pulled from Chroma before reranking


def search(query: str, top_n: int = 5, title_id: int | None = None) -> list[dict]:
    """Retrieve the top_n most relevant review chunks for `query`.
    first stage: vector similarity search from chroma DB
    second stage: cross-encoder rerank - cohere rerank API

    """
    store = get_vector_store()
    candidates = store.similarity_search(
        query, k=_DEFAULT_FETCH_K, filter={"title_id": title_id} if title_id else None  # type: ignore
    )
    hits = rerank(query, [doc.page_content for doc in candidates], top_n=top_n)
    return [
        {
            "review_id": (c := candidates[hit.index]).metadata["review_id"],
            "title_id": c.metadata["title_id"],
            "title": c.metadata["title"],
            "chunk_text": c.page_content,
            "author": c.metadata["author"],
            "rating": c.metadata["rating"],
            "score": hit.relevance_score,
        }
        for hit in hits
    ]
