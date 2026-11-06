"""Terminal chat with the agent: the first way to run it, before M6's UI.

Usage (once implemented; mcp_server must be running with
MCP_TRANSPORT=streamable-http, plus data_service and rag_service):
    python -m agent.cli --graph react
"""

import argparse

from agent.graphs import GRAPHS


async def chat(graph_name: str) -> None:
    """Interactive loop.

    TODO(you):
    1. Load tools ONCE (mcp_tools.load_tools) and build the chosen graph
       from GRAPHS[graph_name]. Keep everything inside this one coroutine so
       the whole session shares a single event loop (package docstring,
       rule 2).
    2. Use a fresh `thread_id` per conversation in the graph config
       ({"configurable": {"thread_id": ...}}) so the checkpointer keeps
       history.
    3. Stream events (`graph.astream`) and print each tool call and its
       result as it happens. This trace view is the CLI's real value while
       you debug tool selection.
    4. When the graph pauses on an approval interrupt, show what is about to
       happen, read y/n, and resume with `Command(resume=...)`.
    5. Ctrl+C and errors must end the session cleanly (close the MCP
       connection), and a tool or model failure prints a readable message.
    """
    raise NotImplementedError


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with the TMDB agent")
    parser.add_argument("--graph", choices=sorted(GRAPHS) or ["react"], default="react")
    args = parser.parse_args()

    import asyncio

    asyncio.run(chat(args.graph))


if __name__ == "__main__":
    main()
