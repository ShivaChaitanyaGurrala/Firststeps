"""Thin async wrapper around the TMDB v3 REST API + daily export files.

Auth: v4 Bearer token on every call (no api_key query param).
"""

import asyncio
import gzip
import json
from datetime import date, timedelta
from typing import Any, AsyncIterator

import httpx

from data_service.config import settings

API_BASE = "https://api.themoviedb.org/3"
EXPORTS_BASE = "https://files.tmdb.org/p/exports"

_EXPORT_FILE_NAMES = {
    "movie": "movie_ids",
    "person": "person_ids",
}

# Transient connection-level failures under concurrent load (seen locally as
# httpx.ConnectError with an empty message even for known-valid ids) get a
# small bounded retry. This is NOT the rate-limit-aware backoff planned for
# M3 — no 429 handling, no jitter, just enough to not fail a bulk seed on a
# flaky handshake. HTTPStatusError (404, etc.) is never retried here since
# that's a real answer from the API, not a transport hiccup.
_MAX_CONNECT_RETRIES = 4
_RETRY_DELAY_SECONDS = 0.5


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.tmdb_api_token}",
        "accept": "application/json",
    }


class TmdbClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(headers=_headers(), timeout=30.0)
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(_MAX_CONNECT_RETRIES + 1):
            try:
                resp = await self._client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
            except httpx.TransportError:
                if attempt == _MAX_CONNECT_RETRIES:
                    raise
                await asyncio.sleep(_RETRY_DELAY_SECONDS)

    async def get_movie_details(self, movie_id: int) -> dict[str, Any]:
        return await self._get(
            f"{API_BASE}/movie/{movie_id}",
            {"language": "en-US", "append_to_response": "credits"},
        )

    async def get_person_details(self, person_id: int) -> dict[str, Any]:
        return await self._get(f"{API_BASE}/person/{person_id}", {"language": "en-US"})

    async def get_changes(
        self, entity_type: str, start_date: date, end_date: date, page: int = 1
    ) -> dict[str, Any]:
        """entity_type: 'movie' | 'person'. Window is capped by TMDB at 14 days."""
        return await self._get(
            f"{API_BASE}/{entity_type}/changes",
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "page": page,
            },
        )

    async def download_daily_export(self, entity_type: str) -> AsyncIterator[dict[str, Any]]:
        """Streams the daily ID export file, yielding one parsed JSON object per line.

        Files are published ~7-8am UTC for "yesterday"; step back a day on 404
        since today's file may not exist yet.
        """
        file_stub = _EXPORT_FILE_NAMES[entity_type]
        candidate = date.today() - timedelta(days=1)
        for _ in range(5):
            url = f"{EXPORTS_BASE}/{file_stub}_{candidate.strftime('%m_%d_%Y')}.json.gz"
            resp = await self._client.get(url)
            if resp.status_code == 404:
                candidate -= timedelta(days=1)
                continue
            resp.raise_for_status()
            for line in gzip.decompress(resp.content).splitlines():
                line = line.strip()
                if line:
                    yield json.loads(line)
            return
        raise RuntimeError(f"No daily export file found for '{entity_type}' in the last 5 days")
