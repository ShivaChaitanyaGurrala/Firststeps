"""rag_service's FastAPI app — the one HTTP endpoint mcp_server's
search_reviews tool calls (see mcp_server/rag_client.py).

Run: uvicorn rag_service.main:app --port 8020
"""

from fastapi import FastAPI, Query
from langsmith import traceable

from rag_service.retriever import search as retrieve_chunks
from rag_service.schemas import ReviewSearchHit, ReviewSearchResponse

app = FastAPI(title="RAG Service", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/search", response_model=ReviewSearchResponse)
@traceable(name="search_endpoint", run_type="chain")
def search(
    query: str,
    title_id: int | None = None,
    limit: int = Query(default=5, ge=1, le=20),
) -> ReviewSearchResponse:
    hits = retrieve_chunks(query, top_n=limit, title_id=title_id)
    return ReviewSearchResponse(
        query=query,
        results=[ReviewSearchHit(**hit) for hit in hits],
    )
