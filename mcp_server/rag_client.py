"""Thin client for calling rag_service — the M4 counterpart to
http_client.py's DataServiceClient. Kept as its own module/class rather than
folded into DataServiceClient because it talks to a different service
entirely (different base_url, different backing store) — mcp_server now
fans out to two backend services, and this file makes that visible instead
of hiding it behind one shared client.
"""

from typing import Any

import errors
import schemas

from config import settings
from http_client import _validate_model

import httpx

# Explicit rather than httpx's 5s default, which is no longer than Cohere's own
# 5s budget alone. rag_service/reranker.py's LIVE_RETRY has to fit inside the
# read timeout along with Voyage + Chroma.
_TIMEOUT = httpx.Timeout(20.0, connect=2.0)


class RagServiceClient:
    def __init__(self) -> None:
        self._client = httpx.Client(
            base_url=settings.rag_service_base_url, timeout=_TIMEOUT
        )

    def search_reviews(
        self, query: str, title_id: int | None = None, limit: int = 5
    ) -> dict[str, Any]:
        """GET /search?query=&title_id=&limit= -> ReviewSearchResponse
        (rag_service/main.py). Same error-normalization/response-validation
        shape as DataServiceClient's methods in http_client.py — reuses its
        _validate_model helper rather than duplicating it.
        """
        params: dict[str, Any] = {"query": query, "limit": limit}
        if title_id is not None:
            params["title_id"] = title_id
        try:
            response = self._client.get("/search", params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise errors.from_httpx_error(exc) from exc
        except httpx.TransportError as exc:
            raise errors.UpstreamError(
                "Review search timed out or is unreachable. Try again shortly."
            ) from exc
        return _validate_model(schemas.ReviewSearchResponse, response.json())
