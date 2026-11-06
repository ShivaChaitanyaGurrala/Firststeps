"""The agent's ONLY door to the outside world: mcp_server's tools, fetched
over the MCP protocol and handed to LangGraph as LangChain tools.

mcp_server exposes 13 tools. Read-only: search_titles, get_title_details,
get_recommendations, list_watchlist, sync_status, search_reviews,
generate_watchlist_blurb. Mutating: add_to_watchlist, remove_from_watchlist,
rate_title, create_list, add_to_list, trigger_sync.
"""

from langchain_core.tools import BaseTool


async def load_tools() -> list[BaseTool]:
    """Connect to settings.mcp_server_url, run `tools/list`, and return the
    tools as LangChain BaseTools the agent can bind to a model.

    TODO(you): DECIDE how (unresolved on purpose):
      A. Hand-convert with the MCP SDK's own client (`from mcp import Client`,
         connect over Streamable HTTP, `list_tools()`, then wrap each tool in
         a `StructuredTool` whose coroutine calls `client.call_tool(...)`).
         More code, but you see the protocol: schemas, structured_content,
         error results. Best for the learning goal.
      B. `langchain-mcp-adapters` (`MultiServerMCPClient`), the production
         shortcut. Try it second and compare what it hides.
    Whichever you pick, do these:
    1. Apply settings.mcp_timeout_seconds to the connection and every call.
    2. Keep the tool descriptions exactly as mcp_server wrote them. M4's
       docstring said the agent never sees code comments, only descriptions,
       so tool selection quality depends on them (search_reviews = opinions,
       search_titles = structured lookup).
    3. Map an MCP tool error result to something the model can read and
       recover from, not a raw exception (M3's error normalization already
       shapes these on the server side).
    4. Hold ONE client for the whole session (package docstring, rule 2).
    """
    raise NotImplementedError


def is_mutating(tool: BaseTool) -> bool:
    """True if calling this tool changes data, so guardrails.py must ask a
    human first.

    TODO(you): do NOT hardcode the six names above here. The tool's owner
    should say so, via MCP tool annotations:
    1. In mcp_server/tools/*.py, pass annotations to `@mcp.tool(...)`, e.g.
       `ToolAnnotations(readOnlyHint=True)` on reads and
       `destructiveHint=True` on remove_from_watchlist (check the SDK's
       `mcp.types.ToolAnnotations` for the exact fields). Currently NO tool
       declares any annotation.
    2. Carry the annotation through your tool conversion (for example into
       `tool.metadata`) and read it here.
    3. Default to True (mutating) when a tool has no annotation, so a new
       tool is gated until someone marks it read-only. Fail closed.
    """
    raise NotImplementedError
