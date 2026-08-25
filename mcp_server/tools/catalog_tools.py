"""Read-oriented catalog tools: search, detail lookup, and recommendations.

Build these first (per the plan's M1 build order) — they're read-only and
lowest-risk, good for validating that @mcp.tool() schema derivation from
type hints works before touching any write tools.
"""

from server import mcp
from http_client import DataServiceClient

_client = DataServiceClient()


@mcp.tool()
def search_titles(query: str, limit: int = 10) -> dict:
    """Search the local movie catalog by title text.

    Args:
        query: free-text search term matched against title.
        limit: max results to return (default 10).

    Returns:
        {"results": [{"id", "title", "release_date", "popularity", "vote_average"}, ...]}
    """
    # TODO(you): call _client.search_titles(...) and shape the response dict.
    raise NotImplementedError


@mcp.tool()
def get_title_details(title_id: int) -> dict:
    """Get full details for one movie, including genres, cast, and crew.

    Args:
        title_id: the TMDB id of the movie.

    Returns:
        {"id", "title", "overview", "release_date", "runtime", "status",
         "vote_average", "adult", "softcore", "collection_name",
         "genres": [...], "cast": [...] (top 10),
         "crew": [...] (director/cinematographer/writers/producer)}
    """
    # TODO(you): call _client.get_title(title_id) and shape the response dict.
    raise NotImplementedError


@mcp.tool()
def get_recommendations(based_on: str, genre: str | None = None, limit: int = 10) -> dict:
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
