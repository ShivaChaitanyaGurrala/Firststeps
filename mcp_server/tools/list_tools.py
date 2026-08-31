"""Custom list tools — thin 1:1 wrappers around the lists endpoints.

M3 TODO(you): unlike add_to_watchlist/rate_title, create_list has no
natural upsert key, so it is NOT safe to blindly retry on a transport
failure (see http_client.py's docstring). Still catch
errors.DataServiceError here and re-raise as
mcp.server.mcpserver.exceptions.ToolError(str(exc)) for the error-shape
requirement — just don't add a retry to the client method backing this one.
"""

from typing import Annotated, cast
from pydantic import Field
from typing_extensions import TypedDict
from mcp_instance import mcp
from http_client import DataServiceClient
from mcp.server.mcpserver.exceptions import ToolError
from errors import DataServiceError

_client = DataServiceClient()


class CreateListResult(TypedDict):
    id: int
    name: str
    description: str | None


@mcp.tool()
def create_list(
    name: Annotated[str, Field(description="The name of the list")],
    description: Annotated[
        str | None, Field(default=None, description="Optional free-text description")
    ] = None,
) -> CreateListResult:
    """Create a new named list (e.g. "Weekend picks", "To rewatch")."""
    try:
        response = _client.create_list(name, description)
    except DataServiceError as exc:
        raise ToolError(str(exc)) from exc
    return cast(CreateListResult, response)


class ListItemOut(TypedDict):
    title_id: int
    title: str
    added_at: str  # ISO 8601 string


class ListDetailOut(TypedDict):
    id: int
    name: str
    description: str | None
    items: list[ListItemOut]


@mcp.tool()
def add_to_list(
    list_id: Annotated[
        int, Field(description="The id of the list to add the title to")
    ],
    title_id: Annotated[
        int, Field(description="The TMDB id of the movie or TV show to add")
    ],
) -> ListDetailOut:
    """Add a title to an existing list.

    Returns:
        {"id", "name", "description", "items": [{"title_id", "title", "added_at"}, ...]}
    """
    try:
        response = _client.add_to_list(list_id, title_id)
    except DataServiceError as exc:
        raise ToolError(str(exc)) from exc
    return cast(ListDetailOut, response)
