"""Thin client for calling the local FastAPI data service from MCP tools.

TODO(you): implement each method's body using httpx. Decide sync (httpx.Client)
vs async (httpx.AsyncClient) up front and be consistent across every method —
whichever you pick, the tool functions in tools/*.py that call these must
match (sync tool functions calling sync methods, or `async def` tools awaiting
async methods — the MCP SDK supports both for @mcp.tool()-decorated functions).

Base URL comes from config.settings.data_service_base_url. Raise on non-2xx
responses (httpx's .raise_for_status()) rather than swallowing errors here —
M1 doesn't need error normalization yet, that's M3's job.
"""

from config import settings
from typing import Any

import httpx


class DataServiceClient:
    def __init__(self) -> None:
        self._client = httpx.Client(base_url=settings.data_service_base_url)

    def search_titles(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """GET /titles?q={query}&limit={limit} -> list[TitleSummary]"""
        response = self._client.get(
            "/titles",
            params={"q": query, "limit": limit},
        )
        response.raise_for_status()
        return response.json()

    def get_title(self, title_id: int) -> dict[str, Any]:
        """GET /titles/{title_id} -> TitleDetail"""
        response = self._client.get(f"/titles/{title_id}")
        response.raise_for_status()
        return response.json()

    def list_titles_by_genre(self, genre: str, limit: int = 10) -> list[dict[str, Any]]:
        """GET /titles?genre={genre}&limit={limit} -> list[TitleSummary]

        Used by the get_recommendations tool's genre-based mode.
        """
        response = self._client.get(
            "/titles",
            params={"genre": genre, "limit": limit},
        )
        response.raise_for_status()
        return response.json()

    def add_to_watchlist(
        self, title_id: int, notes: str | None = None
    ) -> dict[str, Any]:
        """POST /watchlist {title_id, notes} -> WatchlistOut"""
        response = self._client.post(
            "/watchlist",
            json={"title_id": title_id, "notes": notes},
        )
        response.raise_for_status()
        return response.json()

    def remove_from_watchlist(self, watchlist_id: int) -> None:
        """DELETE /watchlist/{watchlist_id}"""
        response = self._client.delete(f"/watchlist/{watchlist_id}")
        response.raise_for_status()

    def list_watchlist(self) -> list[dict[str, Any]]:
        """GET /watchlist -> list[WatchlistOut]

        Used by both the list_watchlist tool directly and get_recommendations'
        watchlist-based mode.
        """
        response = self._client.get("/watchlist")
        response.raise_for_status()
        return response.json()

    def rate_title(
        self, title_id: int, score: int, review: str | None = None
    ) -> dict[str, Any]:
        """POST /ratings {title_id, score, review} -> RatingOut"""
        response = self._client.post(
            "/ratings",
            json={"title_id": title_id, "score": score, "review": review},
        )
        response.raise_for_status()
        return response.json()

    def create_list(self, name: str, description: str | None = None) -> dict[str, Any]:
        """POST /lists {name, description} -> ListOut"""
        response = self._client.post(
            "/lists",
            json={"name": name, "description": description},
        )
        response.raise_for_status()
        return response.json()

    def add_to_list(self, list_id: int, title_id: int) -> dict[str, Any]:
        """POST /lists/{list_id}/items {title_id} -> ListDetailOut"""
        response = self._client.post(
            f"/lists/{list_id}/items",
            json={"title_id": title_id},
        )
        response.raise_for_status()
        return response.json()

    def get_person(self, person_id: int) -> dict[str, Any]:
        """GET /people/{person_id} -> PersonDetail"""
        response = self._client.get(f"/people/{person_id}")
        response.raise_for_status()
        return response.json()

    def list_sync_runs(self, run_id: int | None = None) -> list[dict[str, Any]]:
        """GET /sync/runs (all recent) or GET /sync/runs/{run_id} (one) -> SyncRunOut[]"""
        response = self._client.get("/sync/runs" + (f"/{run_id}" if run_id else ""))
        response.raise_for_status()
        return response.json()

    def trigger_sync(self, run_type: str) -> dict[str, Any]:
        """POST /sync/trigger {run_type} -> SyncTriggerResponse"""
        response = self._client.post(
            "/sync/trigger",
            json={"run_type": run_type},
        )
        response.raise_for_status()
        return response.json()
