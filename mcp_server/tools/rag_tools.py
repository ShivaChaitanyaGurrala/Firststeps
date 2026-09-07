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
        Field(description="TODO(you): write a description an LLM can use to "
              "tell this apart from search_titles — see this file's module "
              "docstring."),
    ],
    title_id: Annotated[
        int | None,
        Field(default=None, description="TODO(you): describe the scoping behavior."),
    ] = None,
    limit: Annotated[
        int, Field(default=5, ge=1, le=20, description="Max review chunks to return.")
    ] = 5,
) -> SearchReviewsResult:
    """TODO(you): write the tool docstring (this is also LLM-visible, same
    as the Field descriptions above).

    Body TODO(you) — identical shape to search_titles in catalog_tools.py:
        try:
            response = _client.search_reviews(query, title_id, limit)
        except DataServiceError as exc:
            raise ToolError(str(exc)) from exc
        return cast(SearchReviewsResult, response)
    """
    raise NotImplementedError
