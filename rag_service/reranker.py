"""Cross-encoder reranking via Cohere's hosted Rerank API — the second stage
of the two-stage retrieval pipeline (see retriever.py's module docstring for
why a second stage exists at all).

pip install: cohere (already in pyproject.toml).
API key: settings.cohere_api_key (rag_service/config.py), sourced from
COHERE_API_KEY in .env. Get one at https://dashboard.cohere.com/api-keys.
"""

from dataclasses import dataclass

from rag_service.config import settings
import cohere


@dataclass
class RerankedHit:
    index: int  # position of this document in the `documents` list you passed in
    relevance_score: float


def rerank(query: str, documents: list[str], top_n: int = 5) -> list[RerankedHit]:
    """Score `documents` against `query` and return the top_n, best-first.

    `result.results` is already sorted best-first; each entry has
    `.index` (position in your original `documents` list — use this to map
    back to the chunk/metadata that document came from) and
    `.relevance_score`. Map those into RerankedHit and return.
    """
    if not settings.cohere_api_key:
        raise RuntimeError(
            "Cohere API key is empty; set COHERE_API_KEY in .env"
            "get the key at https://dashboard.cohere.com/api-keys"
        )

    cohere_client = cohere.Client(settings.cohere_api_key)
    result = cohere_client.rerank(
        model="rerank-v3.5",  # current models : https://docs.cohere.com/docs/rerank
        query=query,
        documents=documents,
        top_n=top_n,
    )
    return [
        RerankedHit(index=hit.index, relevance_score=hit.relevance_score)
        for hit in result.results
    ]
