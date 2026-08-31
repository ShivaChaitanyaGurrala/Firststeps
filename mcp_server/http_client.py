"""Thin client for calling the local FastAPI data service from MCP tools.

M1 note (implemented): each method uses httpx.Client (sync) and raises on
non-2xx via .raise_for_status().

M3 note (implemented): every method below catches httpx.HTTPStatusError and
re-raises via errors.from_httpx_error(exc) — see errors.py's docstring for
the full walkthrough.

M3 note (implemented): every method validates data_service's response
against the matching schemas.py model via .model_validate()/TypeAdapter
(so a shape mismatch raises pydantic.ValidationError immediately instead of
silently propagating), then immediately .model_dump(mode="json")s it back
to a plain dict/list[dict]. Returning the dict form rather than the
Pydantic instance itself is deliberate — every tools/*.py module was
already written against dict-style access (h["id"], .get("notes"), etc.);
returning real model instances would mean rewriting all of that call-site
code to attribute access for no functional gain here. The validation still
happens either way — this only changes what shape survives it.

M3 note (implemented): add_to_watchlist/rate_title retry on transient
connection failures (httpx.TransportError) via _post_idempotent, same
pattern as data_service/tmdb_client.py's `_get`. create_list/add_to_list
deliberately do NOT get this — there's no natural upsert key (two retried
create_list calls with the same name would make two lists), so blindly
retrying them would violate the "idempotent writes" requirement rather than
satisfy it; they still use self._client.post directly.

M3 note (implemented): search_titles/list_titles_by_genre now take an
`offset` param and pass it through to GET /titles?offset=..., matching
what data_service/routers/titles.py already supports. Threaded through to
tools/catalog_tools.py's `search_titles` tool.

M3 note (implemented): a pydantic.ValidationError from the
.model_validate()/TypeAdapter calls below (schemas.py's own TODO item 2)
is caught by _validate_model/_validate_list and re-raised as
errors.UpstreamError — data_service sent something that doesn't match its
own contract, which is an upstream problem, not the caller's. Without this,
a schema mismatch would propagate as a raw, unnormalized ValidationError
straight past tools/*.py's `except DataServiceError` handlers — exactly the
"raw stack trace reaches the LLM" failure mode M3 exists to close.
"""

import time

import errors
import schemas

from config import settings
from typing import Any

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError

_title_summary_list = TypeAdapter(list[schemas.TitleSummary])
_watchlist_out_list = TypeAdapter(list[schemas.WatchlistOut])
_sync_run_out_list = TypeAdapter(list[schemas.SyncRunOut])

# Local network hop to data_service, not the public internet like TMDB —
# a short, cheap retry budget is enough to ride out a dropped connection.
_MAX_CONNECT_RETRIES = 2
_RETRY_DELAY_SECONDS = 0.2


def _validate_model(model_cls: type[BaseModel], data: Any) -> dict[str, Any]:
    try:
        return model_cls.model_validate(data).model_dump(mode="json")
    except ValidationError as exc:
        raise errors.UpstreamError(str(exc)) from exc


def _validate_list(adapter: TypeAdapter, data: Any) -> list[dict[str, Any]]:
    try:
        validated = adapter.validate_python(data)
    except ValidationError as exc:
        raise errors.UpstreamError(str(exc)) from exc
    return adapter.dump_python(validated, mode="json")


class DataServiceClient:
    def __init__(self) -> None:
        self._client = httpx.Client(base_url=settings.data_service_base_url)

    def _post_idempotent(self, path: str, json_body: dict[str, Any]) -> httpx.Response:
        """POST with retries on transient connection failures. Only for
        endpoints that are safe to call twice (upsert-by-id at the service
        layer) — see this file's module docstring.
        """
        for attempt in range(_MAX_CONNECT_RETRIES + 1):
            try:
                return self._client.post(path, json=json_body)
            except httpx.TransportError:
                if attempt == _MAX_CONNECT_RETRIES:
                    raise
                time.sleep(_RETRY_DELAY_SECONDS)
        raise httpx.TransportError("Max connection attempts reached")

    def search_titles(
        self, query: str, limit: int = 10, offset: int = 0
    ) -> list[dict[str, Any]]:
        """GET /titles?q={query}&limit={limit}&offset={offset} -> list[TitleSummary]"""
        response = self._client.get(
            "/titles",
            params={"q": query, "limit": limit, "offset": offset},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise errors.from_httpx_error(exc) from exc
        return _validate_list(_title_summary_list, response.json())

    def get_title(self, title_id: int) -> dict[str, Any]:
        """GET /titles/{title_id} -> TitleDetail"""
        response = self._client.get(f"/titles/{title_id}")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise errors.from_httpx_error(exc) from exc
        return _validate_model(schemas.TitleDetail, response.json())

    def list_titles_by_genre(
        self, genre: str, limit: int = 10, offset: int = 0
    ) -> list[dict[str, Any]]:
        """GET /titles?genre={genre}&limit={limit}&offset={offset} -> list[TitleSummary]

        Used by the get_recommendations tool's genre-based mode.
        """
        response = self._client.get(
            "/titles",
            params={"genre": genre, "limit": limit, "offset": offset},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise errors.from_httpx_error(exc) from exc
        return _validate_list(_title_summary_list, response.json())

    def add_to_watchlist(
        self, title_id: int, notes: str | None = None
    ) -> dict[str, Any]:
        """POST /watchlist {title_id, notes} -> WatchlistOut"""
        response = self._post_idempotent(
            "/watchlist",
            {"title_id": title_id, "notes": notes},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise errors.from_httpx_error(exc) from exc
        return _validate_model(schemas.WatchlistOut, response.json())

    def remove_from_watchlist(self, watchlist_id: int) -> None:
        """DELETE /watchlist/{watchlist_id}"""
        response = self._client.delete(f"/watchlist/{watchlist_id}")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise errors.from_httpx_error(exc) from exc

    def list_watchlist(self) -> list[dict[str, Any]]:
        """GET /watchlist -> list[WatchlistOut]

        Used by both the list_watchlist tool directly and get_recommendations'
        watchlist-based mode.
        """
        response = self._client.get("/watchlist")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise errors.from_httpx_error(exc) from exc
        return _validate_list(_watchlist_out_list, response.json())

    def rate_title(
        self, title_id: int, score: int, review: str | None = None
    ) -> dict[str, Any]:
        """POST /ratings {title_id, score, review} -> RatingOut"""
        response = self._post_idempotent(
            "/ratings",
            {"title_id": title_id, "score": score, "review": review},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise errors.from_httpx_error(exc) from exc
        return _validate_model(schemas.RatingOut, response.json())

    def create_list(self, name: str, description: str | None = None) -> dict[str, Any]:
        """POST /lists {name, description} -> ListOut"""
        response = self._client.post(
            "/lists",
            json={"name": name, "description": description},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise errors.from_httpx_error(exc) from exc
        return _validate_model(schemas.ListOut, response.json())

    def add_to_list(self, list_id: int, title_id: int) -> dict[str, Any]:
        """POST /lists/{list_id}/items {title_id} -> ListDetailOut"""
        response = self._client.post(
            f"/lists/{list_id}/items",
            json={"title_id": title_id},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise errors.from_httpx_error(exc) from exc
        return _validate_model(schemas.ListDetailOut, response.json())

    def get_person(self, person_id: int) -> dict[str, Any]:
        """GET /people/{person_id} -> PersonDetail"""
        response = self._client.get(f"/people/{person_id}")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise errors.from_httpx_error(exc) from exc
        return _validate_model(schemas.PersonDetail, response.json())

    def list_sync_runs(self, run_id: int | None = None) -> list[dict[str, Any]] | dict[str, Any]:
        """GET /sync/runs (all recent, a list) or GET /sync/runs/{run_id} (one,
        a single SyncRunOut, not a list — see data_service/routers/sync.py)
        """
        response = self._client.get("/sync/runs" + (f"/{run_id}" if run_id else ""))
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise errors.from_httpx_error(exc) from exc
        if run_id is None:
            return _validate_list(_sync_run_out_list, response.json())
        return _validate_model(schemas.SyncRunOut, response.json())

    def trigger_sync(self, run_type: str) -> dict[str, Any]:
        """POST /sync/trigger {run_type} -> SyncTriggerResponse"""
        response = self._client.post(
            "/sync/trigger",
            json={"run_type": run_type},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise errors.from_httpx_error(exc) from exc
        return _validate_model(schemas.SyncTriggerResponse, response.json())
