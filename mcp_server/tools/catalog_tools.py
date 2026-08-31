"""Read-oriented catalog tools: search, detail lookup, and recommendations.

Build these first (per the plan's M1 build order) — they're read-only and
lowest-risk, good for validating that @mcp.tool() schema derivation from
type hints works before touching any write tools.

"""

from collections import Counter
from typing import Annotated, Literal, cast


from pydantic import Field
from typing_extensions import TypedDict

from mcp_instance import mcp
from http_client import DataServiceClient
from mcp.server.mcpserver.exceptions import ToolError
from errors import DataServiceError

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
    offset: Annotated[
        int,
        Field(
            default=0,
            ge=0,
            description="Number of results to skip, for paging past `limit`.",
        ),
    ] = 0,
) -> SearchTitlesResult:
    """Search the local movie catalog by title text."""
    try:
        response = _client.search_titles(query, limit, offset)
    except DataServiceError as exc:
        raise ToolError(str(exc)) from exc
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
    include_cast_crew: Annotated[
        bool,
        Field(
            default=True,
            description=(
                "Include the full cast/crew list. Set False when you only "
                "need runtime/genres/overview — cast/crew can be large for "
                "popular titles and costs tokens an agent may not need."
            ),
        ),
    ] = True,
) -> TitleDetails:
    """Get full details for one movie, including genres, cast, and crew."""
    try:
        response = _client.get_title(title_id)
    except DataServiceError as exc:
        raise ToolError(str(exc)) from exc
    if not include_cast_crew:
        response = {**response, "cast": [], "crew": []}
    return cast(TitleDetails, response)


class RecommendationHit(TypedDict):
    id: int
    title: str
    reason: str


class RecommendationsResult(TypedDict):
    results: list[RecommendationHit]


@mcp.tool()
def get_recommendations(
    based_on: Annotated[
        Literal["watchlist", "genre"],
        Field(
            description="Base recommendations on the watchlist's dominant genre, or on a specific genre."
        ),
    ],
    genre: Annotated[
        str | None,
        Field(
            default=None,
            description="Required when based_on='genre' — the genre name to filter by.",
        ),
    ] = None,
    limit: Annotated[
        int, Field(default=10, ge=1, le=50, description="Max results to return.")
    ] = 10,
) -> RecommendationsResult:
    """Suggest titles based on either the watchlist or a genre.

    This is the deliberately COARSE, task-level tool of the set — it composes
    two backend calls itself (rather than making the agent orchestrate two
    separate tool calls and reason about the join). Compare this to
    search_titles/get_title_details, which stay thin and separate on purpose.
    Think about the tradeoff each design makes before implementing this one.
    """
    if based_on == "genre":
        if not genre:
            raise ValueError("genre is required when based_on='genre'")
        try:
            hits = _client.list_titles_by_genre(genre, limit)
        except DataServiceError as exc:
            raise ToolError(str(exc)) from exc
        results = [
            {"id": h["id"], "title": h["title"], "reason": f"Matches genre '{genre}'"}
            for h in hits
        ]
        return {"results": cast(list[RecommendationHit], results)}
    try:
        watchlist = _client.list_watchlist()
    except DataServiceError as exc:
        raise ToolError(str(exc)) from exc
    watchlisted_ids = {item["title_id"] for item in watchlist}

    genre_counts: Counter[str] = Counter()
    for item in watchlist:
        try:
            details = _client.get_title(item["title_id"])
        except DataServiceError as exc:
            raise ToolError(str(exc)) from exc
        genre_counts.update(g["name"] for g in details.get("genres", []))

    if not genre_counts:
        return {"results": []}

    top_genre, _count = genre_counts.most_common(1)[0]
    try:
        hits = _client.list_titles_by_genre(top_genre, limit)
    except DataServiceError as exc:
        raise ToolError(str(exc)) from exc
    results = [
        {
            "id": h["id"],
            "title": h["title"],
            "reason": f"Because your watchlist favors '{top_genre}'",
        }
        for h in hits
        if h["id"] not in watchlisted_ids
    ][:limit]
    return {"results": cast(list[RecommendationHit], results)}
