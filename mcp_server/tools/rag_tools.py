"""M4's one new MCP tool: search_reviews, backed by rag_service's GET
/search — a SEPARATE backend service from data_service (see
rag_service/config.py's docstring for why), reached via rag_client.py
rather than http_client.py.

Read tools/catalog_tools.py's search_titles first — same shape (thin
wrapper: call DataServiceClient, catch DataServiceError, raise ToolError,
return a TypedDict). The new thing to think about here isn't the plumbing,
it's the tool DESCRIPTION: search_titles and search_reviews sound similar
("search for X about a movie") but answer fundamentally different questions
— search_titles does exact/fuzzy matching over structured fields (find
which movie), search_reviews does semantic retrieval over free-text opinion
content (find what people said about a movie). Once M5 gives an agent both
tools plus the catalog tools together, its tool-selection has to tell "look
this fact up" apart from "find opinions/context about this" from the
docstring/description ALONE — the agent never sees this file's comments,
only what @mcp.tool() and Field(description=...) expose. Write descriptions
that make that distinction obvious now, while you can see both tools
side by side, rather than patching it up in M5 once you observe an agent
picking the wrong one.
"""

from typing import Annotated, cast

from pydantic import Field
from typing_extensions import TypedDict

from mcp_instance import mcp
from rag_client import RagServiceClient
from mcp.server.mcpserver.exceptions import ToolError
from errors import DataServiceError

_client = RagServiceClient()


class ReviewHit(TypedDict):
    review_id: str
    title_id: int
    title: str
    chunk_text: str
    author: str
    rating: float | None
    score: float


class SearchReviewsResult(TypedDict):
    query: str
    results: list[ReviewHit]


@mcp.tool()
def search_reviews(
    query: Annotated[
        str,
        Field(
            description=(
                "Free-text description of an OPINION, sentiment, or theme to "
                "look for in what viewers wrote about a movie (e.g. 'criticism "
                "of the pacing', 'comparisons to the book', 'thoughts on the "
                "ending'). Matched by semantic similarity against real review "
                "text, not exact keywords. Use this to find what people SAID "
                "about a movie; use search_titles instead to find WHICH movie "
                "matches a title."
            )
        ),
    ],
    title_id: Annotated[
        int | None,
        Field(
            default=None,
            description=(
                "Restrict results to reviews of this one movie (its TMDB id, "
                "e.g. from search_titles/get_title_details). Omit to search "
                "review text across the whole catalog."
            ),
        ),
    ] = None,
    limit: Annotated[
        int, Field(default=5, ge=1, le=20, description="Max review chunks to return.")
    ] = 5,
) -> SearchReviewsResult:
    """Semantically search real viewer review text for opinions, sentiment, or
    themes — not a title/catalog lookup. Use search_titles to find a movie by
    name; use this to find what viewers said about one.
    """
    try:
        response = _client.search_reviews(query, title_id, limit)
    except DataServiceError as exc:
        raise ToolError(str(exc)) from exc
    return cast(SearchReviewsResult, response)
