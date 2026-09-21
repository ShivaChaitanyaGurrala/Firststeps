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

from langchain_core.documents import Document

from rag_service.config import retrieval_config_snapshot, settings
from rag_service.reranker import rerank
from rag_service.vector_store import get_vector_store
from langsmith import traceable

_DEFAULT_FETCH_K = settings.fetch_k  # candidates pulled from Chroma before reranking


def _log_candidates(results: list[tuple[Document, float]]) -> dict:
    """process_outputs for _fetch_candidates below: reshapes the raw
    (Document, score) tuples into a clean, LangSmith-legible view (plain
    dicts, truncated review_id-keyed) without changing what the function
    actually returns to its caller."""
    return {
        "candidates": [
            {
                "review_id": doc.metadata.get("review_id"),
                "score": score,
                "chunk_text": doc.page_content,
            }
            for doc, score in results
        ]
    }


# LangSmith observability, the Chroma stage: store.similarity_search() is a
# bare method call, not @traceable and not invoked through LangChain's
# Runnable interface (that's what would get it auto-traced) - so without
# this wrapper there'd be no dedicated span for "what did the bi-encoder
# retrieve," only an indirect, score-less view buried in cohere_rerank's
# Input. similarity_search_with_score (not plain similarity_search) is what
# recovers the scores - Chroma's raw distance metric, not Cohere's
# relevance_score. This becomes its own nested span under rag_search,
# alongside cohere_rerank rather than hidden inside it, showing every
# fetch_k candidate with its score - the piece that tells you whether a
# miss is an embedding_miss (chunk never shows up here at all) vs a
# reranker_demoted one (shows up here with a decent score, cohere_rerank
# just ranked it below top_n).
@traceable(
    name="chroma_similarity_search",
    run_type="retriever",
    metadata=retrieval_config_snapshot(),
    process_outputs=_log_candidates,
)
def _fetch_candidates(query: str, title_id: int | None) -> list[tuple[Document, float]]:
    store = get_vector_store()
    return store.similarity_search_with_score(
        query, k=_DEFAULT_FETCH_K, filter={"title_id": title_id} if title_id else None  # type: ignore
    )


# LangSmith observability, search() itself: run_type="retriever" (not the
# default "chain") because search()'s contract is exactly what that type
# means to LangSmith - query string in, ranked documents out - regardless
# of the two-stage implementation underneath. Same classification
# LangChain itself gives ContextualCompressionRetriever (base retriever +
# reranker/compressor, structurally identical to embed-then-rerank here).
@traceable(name="rag_search", run_type="retriever", metadata=retrieval_config_snapshot())
def search(
    query: str, top_n: int = settings.rerank_top_n, title_id: int | None = None
) -> list[dict]:
    """Retrieve the top_n most relevant review chunks for `query`.
    first stage: vector similarity search from chroma DB
    second stage: cross-encoder rerank - cohere rerank API

    """
    candidates_with_scores = _fetch_candidates(query, title_id)
    candidates = [doc for doc, _ in candidates_with_scores]
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
