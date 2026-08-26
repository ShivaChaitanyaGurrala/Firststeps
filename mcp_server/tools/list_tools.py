"""Custom list tools — thin 1:1 wrappers around the lists endpoints."""

from mcp_instance import mcp
from http_client import DataServiceClient

_client = DataServiceClient()


@mcp.tool()
def create_list(name: str, description: str | None = None) -> dict:
    """Create a new named list (e.g. "Weekend picks", "To rewatch").

    Args:
        name: the list's name.
        description: optional free-text description.

    Returns:
        {"id", "name"}
    """
    # TODO(you): call _client.create_list(name, description) and shape the response dict.
    raise NotImplementedError


@mcp.tool()
def add_to_list(list_id: int, title_id: int) -> dict:
    """Add a title to an existing list.

    Args:
        list_id: the id of the list (from create_list).
        title_id: the TMDB id of the movie or TV show to add.

    Returns:
        {"success": true}
    """
    # TODO(you): call _client.add_to_list(list_id, title_id).
    raise NotImplementedError
