"""Watchlist CRUD tools — thin 1:1 wrappers around the watchlist endpoints.

Third in the M1 build order, alongside rating_tools.py and list_tools.py —
the write tools, built after the read tools are validated.
"""

from server import mcp
from http_client import DataServiceClient

_client = DataServiceClient()


@mcp.tool()
def add_to_watchlist(title_id: int, notes: str | None = None) -> dict:
    """Add a title to the watchlist.

    Args:
        title_id: the TMDB id of the movie or TV show to add.
        notes: optional free-text note.

    Returns:
        {"id", "title_id", "added_at"}
    """
    # TODO(you): call _client.add_to_watchlist(title_id, notes) and shape the response dict.
    raise NotImplementedError


@mcp.tool()
def remove_from_watchlist(watchlist_id: int) -> dict:
    """Remove an entry from the watchlist.

    Args:
        watchlist_id: the watchlist entry's own id (not the title id).

    Returns:
        {"success": true}
    """
    # TODO(you): call _client.remove_from_watchlist(watchlist_id).
    raise NotImplementedError


@mcp.tool()
def list_watchlist() -> dict:
    """List everything currently on the watchlist.

    Returns:
        {"items": [{"id", "title_id", "title", "added_at", "notes"}, ...]}
    """
    # TODO(you): call _client.list_watchlist() and shape the response dict.
    raise NotImplementedError
