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


settings = Settings()
