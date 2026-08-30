"""Reusable prompt templates — user-invokable, not agent-invokable.

M2 teaching point: a Prompt is a canned, named request for a *set of
messages*, the way a slash command is a canned request for a chat message.
A Prompt often *embeds* Resource content directly into the messages it
returns (see summarize_watchlist below) rather than just naming a URI and
hoping the model goes and fetches it — the prompt author controls exactly
what context ships with the request.

TODO(you), for each prompt below:
1. Fill in the body per its own TODO.
2. Run `mcp dev server.py`, check `prompts/list` in the Inspector, then
   `prompts/get` with arguments and inspect the returned messages array.

Docs: https://modelcontextprotocol.io/docs/concepts/prompts
"""

from typing import Any

from mcp_instance import mcp
from http_client import DataServiceClient

_client = DataServiceClient()


@mcp.prompt()
def summarize_watchlist() -> list[dict[str, Any]]:
    """Ask the model to summarize the current watchlist.

    TODO: call _client.list_watchlist(), format it into a short text block
    (title + notes per entry is enough), and return one user message whose
    content embeds that text — e.g.:

        [{
            "role": "user",
            "content": {
                "type": "resource",
                "resource": {"uri": "tmdb://watchlist", "text": <your formatted text>},
            },
        }]

    Note this deliberately mirrors resources/catalog_resources.py's
    get_watchlist_resource — the prompt fetches and embeds the content
    itself rather than assuming the client will dereference the URI on its
    own. (Optional extension once this works: try ctx.read_resource(uri)
    instead of calling _client directly, so the prompt reuses the Resource
    handler rather than duplicating the fetch — add `ctx: Context` as a
    parameter to do that.)
    """

    watchlist_out = _client.list_watchlist()
    formatted_text = "\n".join(
        f"{entry['title']} - {entry.get('notes', '') or ''}" for entry in watchlist_out
    )
    output_message = [
        {
            "role": "user",
            "content": {
                "type": "resource",
                "resource": {"uri": "tmdb://watchlist", "text": formatted_text},
            },
        }
    ]
    return output_message


@mcp.prompt()
def recommend_for_mood(mood: str) -> list[dict[str, Any]]:
    """Ask the agent to pick titles matching a mood, using the get_recommendations tool.

    TODO: write the instruction text yourself (this one's prompt-engineering
    practice, not an API question) — return one user message whose content
    is a string telling the agent: the user is in `mood`-mood, please use the
    get_recommendations tool to find suitable titles and explain why each
    recommendation fits the user's mood. (Optional extension once this works:
    add a second user message that asks the agent to return its recommendations
    in a numbered list, with each entry including the title and a one-sentence
    explanation of why it fits the mood.)
    """
    prompt_text = f"""You are a movie recommendation agent. The user is in a '{mood}' mood. 
        Call get_recommendations with based_on='genre', first picking the single genre from list of genres your 
        catalog actually has that best matches the mood, then explain why each result fits users mood."""
    return [{"role": "user", "content": prompt_text}]
