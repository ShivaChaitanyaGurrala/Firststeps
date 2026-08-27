"""Rating tool — thin 1:1 wrapper around the ratings endpoint."""

from typing import Annotated, TypedDict, cast
from pydantic import Field
from mcp_instance import mcp
from http_client import DataServiceClient

_client = DataServiceClient()


class RateTitleResult(TypedDict):
    id: int
    title_id: int
    score: int
    rated_at: str
    review: str | None
    title: str


@mcp.tool()
def rate_title(
    title_id: Annotated[int, Field(description="The TMDB id of the movie being rated")],
    score: Annotated[int, Field(ge=1, le=10, description="The rating score from 1-10")],
    review: Annotated[
        str | None, Field(default=None, description="Optional free-text review")
    ] = None,
) -> RateTitleResult:
    """Rate a title from 1-10, optionally with a written review.

    Calling this again for the same title_id updates the existing rating
    rather than creating a duplicate (the backend enforces one rating per title).

    """
    response = _client.rate_title(title_id, score, review)
    return cast(RateTitleResult, response)
