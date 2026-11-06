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
from rag_service.errors import RerankUnavailableError
from langsmith import traceable
import cohere
from cohere.core.api_error import ApiError
import httpx

# Trial key: 10 calls/min, so after a 429 the window can be up to a minute away.
_RATE_LIMIT_RETRY_AFTER_SECONDS = 60
_OUTAGE_RETRY_AFTER_SECONDS = 5


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int
    backoff_seconds: float  # sleep is backoff_seconds * attempt number
    request_timeout_seconds: float  # per Cohere call


# A live search has a caller waiting, and a short retry rarely outlasts a
# per-minute limit, so it makes one Cohere call and fails fast. Its 5s has to
# fit inside mcp_server/rag_client.py's 20s read timeout along with Voyage +
# Chroma: an inner budget longer than its caller's does work nobody is still
# waiting for.
LIVE_RETRY = RetryPolicy(max_attempts=1, backoff_seconds=0, request_timeout_seconds=5)
# A batch eval has nobody waiting and needs to outlast the trial key's window.
BATCH_RETRY = RetryPolicy(max_attempts=5, backoff_seconds=10, request_timeout_seconds=60)

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


def _is_transient(exc: ApiError | httpx.TransportError) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    return exc.status_code is not None and (exc.status_code == 429 or exc.status_code >= 500)


def _unavailable(exc: ApiError | httpx.TransportError) -> RerankUnavailableError:
    if isinstance(exc, ApiError) and exc.status_code == 429:
        return RerankUnavailableError(
            "Review search is rate limited right now.", _RATE_LIMIT_RETRY_AFTER_SECONDS
        )
    return RerankUnavailableError(
        "Review search is temporarily unavailable.", _OUTAGE_RETRY_AFTER_SECONDS
    )


@traceable(name="cohere_rerank", run_type="tool", metadata=retrieval_config_snapshot())
def rerank(
    query: str,
    documents: list[str],
    top_n: int = settings.rerank_top_n,
    retry: RetryPolicy = LIVE_RETRY,
) -> list[RerankedHit]:
    """Score `documents` against `query` and return the top_n, best-first.

    `result.results` is already sorted best-first; each entry has
    `.index` (position in your original `documents` list — use this to map
    back to the chunk/metadata that document came from) and
    `.relevance_score`. Map those into RerankedHit and return.

    Raises RerankUnavailableError once `retry` is used up on a transient
    failure (429, 5xx, timeout, dropped connection).
    """
    if not settings.cohere_api_key:
        raise RuntimeError(
            "Cohere API key is empty; set COHERE_API_KEY in .env"
            "get the key at https://dashboard.cohere.com/api-keys"
        )

    # max_retries=0: the SDK otherwise retries 429s itself (2 by default), on
    # top of the loop below and outside `retry`'s budget.
    cohere_client = cohere.Client(
        settings.cohere_api_key,
        timeout=retry.request_timeout_seconds,
        max_retries=0,
    )
    for attempt in range(retry.max_attempts):
        try:
            result = cohere_client.rerank(
                model=settings.rerank_model,  # https://docs.cohere.com/docs/rerank
                query=query,
                documents=documents,
                top_n=top_n,
            )
            break
        except (ApiError, httpx.TransportError) as exc:
            if not _is_transient(exc):
                raise
            if attempt == retry.max_attempts - 1:
                raise _unavailable(exc) from exc
            time.sleep(retry.backoff_seconds * (attempt + 1))
    return [
        RerankedHit(index=hit.index, relevance_score=hit.relevance_score)
        for hit in result.results
    ]
