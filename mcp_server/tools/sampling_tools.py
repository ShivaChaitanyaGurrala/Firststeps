"""M2 Sampling demo: a tool that asks the *client's* LLM to do work, instead
of doing it locally.

Background (worth reading before touching the TODO): the original MCP spec
had a standalone `sampling/createMessage` server-to-client request. As of
protocol revision 2026-07-28 (SEP-2577), that's deprecated — this SDK now
unifies sampling with elicitation into one `InputRequiredResult` /
`input_requests` round trip. You don't hand-roll either wire format though:
this SDK gives you a small dependency-injection layer for it —

    Annotated[CreateMessageResult, Resolve(some_fn)]

— where `some_fn` (a "resolver") returns a `Sample(...)` marker describing
what to ask the client's LLM. The framework runs the round trip (whichever
wire format the connected client's protocol version needs) and injects the
resulting `CreateMessageResult` into your tool parameter. Your tool body
never sees the protocol machinery at all.

TODO(you):
1. Fill in `_sample_blurb` below — it's the resolver, and it's the only
   thing in this file that isn't already wired up.
2. Test it: `mcp dev server.py`, call `generate_watchlist_blurb` from the
   Inspector. Check whether the Inspector build you have implements the
   `sampling` client capability / the 2026-07-28 InputRequiredResult flow —
   if it doesn't yet, fall back to the in-memory `Client(mcp,
   sampling_callback=...)` pattern already used in tests/mcp_server/
   (Client's sampling_callback answers CreateMessageRequests programmatically,
   so you can exercise this tool without a real LLM in the loop).

Docs: https://modelcontextprotocol.io/docs/concepts/sampling
"""

from typing import Annotated

from typing_extensions import TypedDict

from mcp_types import CreateMessageResult, SamplingMessage, TextContent
from mcp.server.mcpserver import Context, Resolve, Sample

from mcp_instance import mcp
from http_client import DataServiceClient

_client = DataServiceClient()


def _sample_blurb(ctx: Context) -> Sample:
    """Ask the client's LLM to write a one-paragraph blurb for the watchlist.

    If the watchlist is empty, return a "nothing on your watchlist yet" blurb.
    """
    list_to_watch = _client.list_watchlist()
    if not list_to_watch:
        return Sample(
            messages=[
                SamplingMessage(
                    role="user",
                    content=TextContent(
                        text="Write a single sentence blurb stating that the watchlist is empty"
                    ),
                )
            ],
            max_tokens=200,
            system_prompt="You are responder Agent, Maintain a professional tone. "
            "limit the response to one sentence.",
        )
    formatted_text = "\n".join(
        f"{entry['title']} - {entry.get('notes', '') or ''}" for entry in list_to_watch
    )
    return Sample(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(
                    text=f"Write a single sentence blurb for the following watchlist:\n{formatted_text}"
                ),
            )
        ],
        max_tokens=200,
        system_prompt="You are responder Agent, Maintain a professional tone. ",
    )


class BlurbResult(TypedDict):
    blurb: str
    model: str


@mcp.tool()
def generate_watchlist_blurb(
    sampled: Annotated[CreateMessageResult, Resolve(_sample_blurb)],
) -> BlurbResult:
    """Write a one-paragraph blurb for the current watchlist, using the
    connected client's own LLM rather than any model call this server makes
    itself.

    Nothing to fill in here — this is the "consumer" side of the resolver
    pattern, given to you so you can see the shape once _sample_blurb is
    implemented. `sampled` doesn't exist until the client has answered the
    sampling request; call_tool() on the client side blocks/retries through
    that automatically.
    """
    if not isinstance(sampled.content, TextContent):
        raise ValueError(
            f"Expected text content from sampling, got {type(sampled.content).__name__}"
        )
    return {"blurb": sampled.content.text, "model": sampled.model}
