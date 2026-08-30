"""Read-only catalog data exposed as addressable Resources, not Tools.

M2 teaching point: Resources and Tools both expose data, but they answer a
different question. A Tool is something the *agent* decides to call as an
action ("search for X"). A Resource is addressable context — a URI a *client*
(or a Prompt, see prompts/catalog_prompts.py) can pull in ambiently, list,
subscribe to, or attach to a conversation without the model having to reason
about which tool call produces it. Same backend data, different consumption
model. `list_watchlist` (a Tool, from M1) and `tmdb://watchlist` (a Resource,
below) return overlapping data on purpose — compare them once both work and
think about which one you'd reach for from an MCP host UI vs. from an agent.

TODO(you), for each resource function below:
1. Call the matching DataServiceClient method (add `get_person` to
   http_client.py first — there's a TODO there now, same pattern as the
   other methods).
2. Return the parsed dict/list directly (not a JSON string) — mime_type is
   already set to "application/json" below, so the SDK serializes it for you.
3. Run `mcp dev server.py` and check `resources/list` in the Inspector, then
   `resources/read` with a concrete URI (e.g. "tmdb://title/27205") — compare
   the JSON-RPC frames here to the `tools/call` frames from M1.

Docs: https://modelcontextprotocol.io/docs/concepts/resources
"""

from typing import Any

from mcp_instance import mcp
from http_client import DataServiceClient

_client = DataServiceClient()


@mcp.resource(
    "tmdb://title/{title_id}",
    name="title",
    description="Full details for one movie in the local catalog.",
    mime_type="application/json",
)
def get_title_resource(title_id: str) -> dict[str, Any]:
    """Template resource — title_id arrives as a str (RFC 6570 URI templates
    are string-only on the wire); cast it before calling the client, the same
    way get_title_details does in tools/catalog_tools.py.
    """
    return _client.get_title(int(title_id))


@mcp.resource(
    "tmdb://person/{person_id}",
    name="person",
    description="Full details for one person (cast/crew member) in the local catalog.",
    mime_type="application/json",
)
def get_person_resource(person_id: str) -> dict[str, Any]:
    return _client.get_person(int(person_id))


@mcp.resource(
    "tmdb://watchlist",
    name="watchlist",
    description="The current watchlist, as ambient context rather than a tool call.",
    mime_type="application/json",
)
def get_watchlist_resource() -> list[dict[str, Any]]:
    """Static resource — no {param} in the URI, so this takes no arguments.

    This is the same underlying data list_watchlist (a Tool, in
    tools/watchlist_tools.py) already returns. TODO: return _client.list_watchlist().
    """
    return _client.list_watchlist()
