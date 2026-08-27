"""Watchlist CRUD tools — thin 1:1 wrappers around the watchlist endpoints.

Third in the M1 build order, alongside rating_tools.py and list_tools.py —
the write tools, built after the read tools are validated.
"""

from typing import Annotated, cast
from pydantic import Field
from typing_extensions import TypedDict

from mcp_instance import mcp
from http_client import DataServiceClient

_client = DataServiceClient()


class AddToWatchlistResult(TypedDict):
    id: int
    title_id: int
    title: str
    added_at: str
    notes: str | None


@mcp.tool()
def add_to_watchlist(
    title_id: Annotated[int, Field(description="The TMDB id of the movie to add")],
    notes: Annotated[
        str | None, Field(default=None, description="Optional free-text note")
    ] = None,
) -> AddToWatchlistResult:
    """Given a title id Add a title to the watchlist."""
    response = _client.add_to_watchlist(title_id, notes)
    return cast(AddToWatchlistResult, response)


class RemoveFromWatchlistResult(TypedDict):
    success: bool


@mcp.tool()
def remove_from_watchlist(
    watchlist_id: Annotated[
        int, Field(description="The watchlist entry's own id (not the title id)")
    ],
) -> RemoveFromWatchlistResult:
    """Given a watchlist entry id, remove it from the watchlist."""
    _client.remove_from_watchlist(watchlist_id)
    return {"success": True}


class WatchlistHit(TypedDict):
    id: int
    title_id: int
    title: str
    added_at: str
    notes: str | None


class ListWatchlistResult(TypedDict):
    items: list[WatchlistHit]


@mcp.tool()
def list_watchlist() -> ListWatchlistResult:
    """Lists everything currently on the watchlist."""
    response = _client.list_watchlist()
    return cast(ListWatchlistResult, {"items": response})
