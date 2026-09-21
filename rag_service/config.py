"""Settings for rag_service — the standalone service owning the RAG
pipeline (chunking, embeddings, Chroma, reranking).

This is a real second backend service, not a module inside data_service:
separate FastAPI app, separate process, separate port. It does NOT connect
to Postgres directly — it pulls review content it needs from data_service
over HTTP (data_service_base_url below), the exact same "never touch a
store you don't own" boundary mcp_server already keeps toward data_service.
This is the concrete result of the M4 architecture discussion: a real
"AI team owns retrieval infra, backend team owns the data store" split
rather than folding RAG into data_service just because Chroma is also,
technically, a data store.

Run it (once main.py exists):
    uvicorn rag_service.main:app --port 8020
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_service_base_url: str = "http://127.0.0.1:8000"

    voyage_api_key: str = ""
    # Default is Voyage's own API. If your key was issued via MongoDB
    # Atlas's "model API keys" (Voyage AI's parent company) rather than
    # Voyage's own dashboard, it only authenticates against MongoDB's
    # endpoint instead — override this to "https://ai.mongodb.com/v1" in
    # that case. Same underlying Voyage models/service either way.
    voyage_base_url: str = "https://api.voyageai.com/v1"
    cohere_api_key: str = ""

    # Chroma runs client-server via Docker, not embedded:
    #   docker run -d --name tmdb-chroma -p 8001:8000 chromadb/chroma
    # (container's internal port is always 8000; mapped to 8001 externally
    # since data_service itself already uses 8000 on this machine)
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "movie_reviews"

    # --- Tunable retrieval knobs -------------------------------------
    # Centralized here (instead of hardcoded literals scattered across
    # chunking.py/embeddings.py/reranker.py/retriever.py) so RAG tuning is
    # "change a value in .env, re-run ingest.py/run_ragas_eval.py, compare
    # results.json" rather than a code edit per experiment. Current values
    # are what M4 originally launched with; diagnose_retrieval.py's verdicts
    # (embedding_miss / reranker_demoted / chunk-boundary splits) are what
    # should drive which of these you actually change.
    chunk_size: int = 400  # chunking.py's RecursiveCharacterTextSplitter chunk_size
    chunk_overlap: int = 100  # ...chunk_overlap
    embedding_model: str = "voyage-4-lite"  # embeddings.py's get_embeddings() default
    rerank_model: str = "rerank-v3.5"  # reranker.py's Cohere model
    fetch_k: int = 20  # retriever.py's pre-rerank candidate count from Chroma
    rerank_top_n: int = 5  # retriever.py's post-rerank result count

    # --- LangSmith (observability) ------------------------------------
    # LangSmith's own SDK reads LANGSMITH_TRACING/LANGSMITH_API_KEY/
    # LANGSMITH_PROJECT directly from the process environment (not from
    # this Settings object) — that's how `@traceable`-decorated functions
    # know where to send traces with zero plumbing. langsmith_tracing below
    # is this project's own on/off switch, surfaced here (like every other
    # rag_service setting) instead of being an invisible ambient env var;
    # wiring it to actually set LANGSMITH_TRACING at process startup is a
    # TODO — see main.py.
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "tmdb-rag"


settings = Settings()

# LangSmith's SDK reads LANGSMITH_TRACING/LANGSMITH_API_KEY/LANGSMITH_PROJECT
# directly from os.environ, not from this Settings object — but
# pydantic-settings' env_file loading only populates Settings' own fields,
# it does NOT write .env's values into the actual process environment. This
# translation has to happen somewhere BEFORE any @traceable-decorated
# function first runs. It used to live in main.py, which only covers the
# uvicorn/FastAPI entry point — every other entry point (run_ragas_eval.py,
# ingest.py, diagnose_retrieval.py, anything importing rag_service.retriever
# or .reranker directly) never imports main.py, so tracing silently stayed
# off for all of them despite langsmith_tracing=True in .env. config.py is
# the one module every entry point imports, directly or transitively (via
# retriever.py/reranker.py), so it's the only place this is guaranteed to
# run first regardless of which script is the entry point.
if settings.langsmith_tracing:
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
    os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)


def retrieval_config_snapshot() -> dict[str, int | str]:
    """The tunable-knob values active in THIS process, for stamping onto
    LangSmith traces as metadata (see retriever.py/reranker.py's @traceable
    calls). Defined here rather than in retriever.py so both it and
    reranker.py can import the same snapshot without a circular import
    (reranker.py is imported BY retriever.py).

    Read once, at import time — correct because every tuning experiment is
    a fresh process (change .env, re-run the eval), so "current process's
    settings" already means "the config this run actually used." A trace
    made under one config stays correctly labeled even after you edit .env
    and start the next experiment, since that's a different process with
    its own snapshot.
    """
    return {
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "embedding_model": settings.embedding_model,
        "fetch_k": settings.fetch_k,
        "rerank_top_n": settings.rerank_top_n,
        "rerank_model": settings.rerank_model,
    }
