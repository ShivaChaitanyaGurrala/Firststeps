"""Cross-encoder reranking via Cohere's hosted Rerank API — the second stage
of the two-stage retrieval pipeline (see retriever.py's module docstring for
why a second stage exists at all).

pip install: cohere (already in pyproject.toml).
API key: settings.cohere_api_key (rag_service/config.py), sourced from
COHERE_API_KEY in .env. Get one at https://dashboard.cohere.com/api-keys.
"""

import time
from dataclasses import dataclass

from rag_service.config import retrieval_config_snapshot, settings
from langsmith import traceable
import cohere
from cohere.errors import TooManyRequestsError

_MAX_ATTEMPTS = 5
_BACKOFF_SECONDS = 10  # trial key: 10 calls/min, so a 429 needs a real wait

# LangSmith observability: this module calls the raw `cohere` SDK directly
# (unlike embeddings.py/vector_store.py, which are LangChain-native), so it
# needs an explicit @traceable to be visible at all. Since retriever.py's
# search() is also @traceable, a rerank() call made from inside search()
# automatically nests as a child run under the parent search trace — no
# extra wiring needed, LangSmith threads that through Python contextvars.
# metadata=retrieval_config_snapshot() stamps the active tuning-knob values
# onto every rerank trace, so traces stay attributable to their config even
# after .env changes for a later experiment (see config.py's docstring).


@dataclass
class RerankedHit:
    index: int  # position of this document in the `documents` list you passed in
    relevance_score: float


@traceable(name="cohere_rerank", run_type="tool", metadata=retrieval_config_snapshot())
def rerank(
    query: str, documents: list[str], top_n: int = settings.rerank_top_n
) -> list[RerankedHit]:
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
    for attempt in range(_MAX_ATTEMPTS):
        try:
            result = cohere_client.rerank(
                model=settings.rerank_model,  # https://docs.cohere.com/docs/rerank
                query=query,
                documents=documents,
                top_n=top_n,
            )
            break
        except TooManyRequestsError:
            if attempt == _MAX_ATTEMPTS - 1:
                raise
            time.sleep(_BACKOFF_SECONDS * (attempt + 1))
    return [
        RerankedHit(index=hit.index, relevance_score=hit.relevance_score)
        for hit in result.results
    ]
