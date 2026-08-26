"""Rating tool — thin 1:1 wrapper around the ratings endpoint."""

from mcp_instance import mcp
from http_client import DataServiceClient

_client = DataServiceClient()


@mcp.tool()
def rate_title(title_id: int, score: int, review: str | None = None) -> dict:
    """Rate a title from 1-10, optionally with a written review.

    Calling this again for the same title_id updates the existing rating
    rather than creating a duplicate (the backend enforces one rating per title).

    Args:
        title_id: the TMDB id of the movie or TV show being rated.
        score: integer 1-10.
        review: optional free-text review.

    Returns:
        {"id", "title_id", "score", "rated_at"}
    """
    # TODO(you): call _client.rate_title(title_id, score, review) and shape the response dict.
    raise NotImplementedError
