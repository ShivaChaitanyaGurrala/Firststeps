"""Thin client for pulling review content from data_service — the same
"never touch a store you don't own directly" boundary mcp_server/http_client.py
already keeps toward data_service, applied here on rag_service's side.

Deliberately much smaller than mcp_server's http_client.py: rag_service only
ever needs to READ reviews (it never writes to Postgres), so there's exactly
one method.
"""

from typing import Any

import httpx

from rag_service.config import settings
from rag_service import errors


class DataServiceClient:
    def __init__(self) -> None:
        self._client = httpx.Client(base_url=settings.data_service_base_url)

    def list_reviews(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """GET /reviews?limit=&offset= (title_id omitted -> whole catalog) ->
        list[ReviewOut], each with id/title_id/title/author/content/rating/
        url/tmdb_created_at — title is already denormalized by data_service
        (see data_service/schemas/reviews.py), which is what lets ingest.py
        write it straight into Chroma metadata without a second call.

        TODO(you): call self._client.get("/reviews", params={"limit": limit,
        "offset": offset}), raise_for_status(), return response.json().
        No response-contract validation layer here (unlike mcp_server's
        http_client.py) — that's an M3-style hardening step you can add
        later following the same pattern (schemas.py + TypeAdapter) if you
        want it; skipped here to keep rag_service's first pass focused on
        the RAG mechanics themselves.
        """
        try:
            response = self._client.get(
                "/reviews", params={"limit": limit, "offset": offset}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise errors.from_httpx_error(exc) from exc
