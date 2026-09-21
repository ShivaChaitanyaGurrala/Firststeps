"""Turn text into vectors via Voyage AI's hosted embedding API.

Design choice worth making deliberately, not defaulting on autopilot:
langchain_chroma's Chroma vectorstore (used in vector_store.py) expects an
object implementing LangChain's `Embeddings` interface — two methods,
`embed_documents(texts: list[str]) -> list[list[float]]` and
`embed_query(text: str) -> list[float]`. You have two ways to get one:

  (a) `pip install langchain-voyageai` and use its VoyageAIEmbeddings class
      directly — zero code here, but one more third-party package pinned
      to LangChain's interface version.
  (b) Call the raw `voyageai` SDK yourself (already in pyproject.toml) and
      wrap it in a small class implementing embed_documents/embed_query
      below — more code, but you see exactly what's crossing the API
      boundary instead of trusting an adapter package.

Either is reasonable; the plan only committed to LangChain glue for
chunking and vector storage, not embeddings specifically. Pick one and
note which in a comment here once you decide — this docstring intentionally
doesn't decide for you.

Voyage model note: `voyage-3` (general-purpose) or `voyage-3-lite` (cheaper,
slightly lower quality) are reasonable starting picks; consult
https://docs.voyageai.com/docs/embeddings for the current model list before
committing to one, since Voyage's lineup does change over time.

API key: settings.voyage_api_key (rag_service/config.py), sourced from
VOYAGE_API_KEY in .env. Get one at https://dash.voyageai.com/.
"""

from pydantic import SecretStr
from langchain_voyageai import VoyageAIEmbeddings

from rag_service.config import settings


def get_embeddings(model: str = settings.embedding_model) -> VoyageAIEmbeddings:
    if not settings.voyage_api_key:
        raise RuntimeError(
            "VOYAGE_API_KEY is not set — add it to .env before using "
            "the RAG pipeline (get one at https://dash.voyageai.com/)."
        )
    return VoyageAIEmbeddings(model=model, api_key=SecretStr(settings.voyage_api_key))
