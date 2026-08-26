"""Read-oriented catalog tools: search, detail lookup, and recommendations.

Build these first (per the plan's M1 build order) — they're read-only and
lowest-risk, good for validating that @mcp.tool() schema derivation from
type hints works before touching any write tools.
"""

from typing import Annotated, cast

from pydantic import Field
from typing_extensions import TypedDict

from mcp_instance import mcp
from http_client import DataServiceClient

_client = DataServiceClient()


class TitleHit(TypedDict):
    id: int
    title: str
    release_date: str | None
    popularity: float
    vote_average: float


class SearchTitlesResult(TypedDict):
    results: list[TitleHit]


@mcp.tool()
def search_titles(
    query: Annotated[
        str, Field(description="Free-text term matched against the movie title.")
    ],
    limit: Annotated[
        int, Field(default=10, ge=1, le=50, description="Max results to return.")
    ] = 10,
) -> SearchTitlesResult:
    """Search the local movie catalog by title text."""
    response = _client.search_titles(query, limit)
    return {"results": cast(list[TitleHit], response)}


class GenreHit(TypedDict):
    id: int
    name: str


class CastHit(TypedDict):
    person_id: int
    name: str
    character: str | None
    order: int | None


class CrewHit(TypedDict):
    person_id: int
    name: str
    job: str | None


class TitleDetails(TypedDict):
    id: int
    title: str
    overview: str | None
    release_date: str | None
    runtime: int | None
    status: str | None
    vote_average: float | None
    adult: bool | None
    softcore: bool | None
    collection_name: str | None
    genres: list[GenreHit]
    cast: list[CastHit]
    crew: list[CrewHit]


@mcp.tool()
def get_title_details(
    title_id: Annotated[int, Field(description="The TMDB id of the movie.")],
) -> TitleDetails:
    """Get full details for one movie, including genres, cast, and crew."""
    response = _client.get_title(title_id)
    return cast(TitleDetails, response)


@mcp.tool()
def get_recommendations(
    based_on: str, genre: str | None = None, limit: int = 10
) -> dict:
    """Suggest titles based on either the watchlist or a genre.

    This is the deliberately COARSE, task-level tool of the set — it composes
    two backend calls itself (rather than making the agent orchestrate two
    separate tool calls and reason about the join). Compare this to
    search_titles/get_title_details, which stay thin and separate on purpose.
    Think about the tradeoff each design makes before implementing this one.

    Args:
        based_on: "watchlist" or "genre".
        genre: required when based_on="genre" — the genre name to filter by.
        limit: max results to return (default 10).

    Returns:
        {"results": [{"id", "title", "reason"}, ...]}
    """
    # TODO(you): if based_on == "watchlist", call _client.list_watchlist() and
    # derive recommendations (e.g. same genres as watchlisted titles) using
    # _client.list_titles_by_genre(...). If based_on == "genre", call
    # _client.list_titles_by_genre(genre, limit) directly. Fill in "reason"
    # with a short string explaining why each title was picked.
    raise NotImplementedError
