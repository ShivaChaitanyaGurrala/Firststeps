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

import httpx


class RagServiceClient:
    def __init__(self) -> None:
        self._client = httpx.Client(base_url=settings.rag_service_base_url)

    def search_reviews(
        self, query: str, title_id: int | None = None, limit: int = 5
    ) -> dict[str, Any]:
        """GET /search?query=&title_id=&limit= -> ReviewSearchResponse
        (rag_service/main.py). Same error-normalization/response-validation
        shape as DataServiceClient's methods in http_client.py.

        TODO(you):
            params: dict[str, Any] = {"query": query, "limit": limit}
            if title_id is not None:
                params["title_id"] = title_id
            response = self._client.get("/search", params=params)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise errors.from_httpx_error(exc) from exc
            return _validate_model(schemas.ReviewSearchResponse, response.json())
        (_validate_model is the same helper defined in http_client.py —
        either import it from there, or decide this file should have its
        own copy; both are reasonable, but don't silently duplicate the
        error-normalization logic itself without deciding which.)
        """
        raise NotImplementedError
