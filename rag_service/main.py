"""rag_service's FastAPI app — the one HTTP endpoint mcp_server's
search_reviews tool calls (see mcp_server/rag_client.py).

Run: uvicorn rag_service.main:app --port 8020
"""

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from langsmith import traceable

from rag_service.errors import RerankUnavailableError
from rag_service.retriever import search as retrieve_chunks
from rag_service.schemas import ReviewSearchHit, ReviewSearchResponse

app = FastAPI(title="RAG Service", version="0.1.0")


@app.exception_handler(RerankUnavailableError)
def rerank_unavailable_handler(request: Request, exc: RerankUnavailableError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": f"{exc} Retry in about {exc.retry_after_seconds} seconds."},
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


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
