"""Graph 3: supervisor-worker. A supervisor routes each request to a
specialist worker that has only the tools it needs, and workers report back.

The natural split for THIS tool set (justify or change it):
  - catalog worker: search_titles, get_title_details, get_recommendations
  - reviews worker: search_reviews (the RAG tool, opinions)
  - library worker: watchlist, ratings, lists (the mutating tools)
Fewer tools per worker usually means better tool selection, and the library
worker is the natural place for the approval gate.
"""

from typing import Any

from langchain_core.tools import BaseTool


def build_graph(tools: list[BaseTool]) -> Any:
    """Build and compile the supervisor-worker graph.

    TODO(you):
    1. Partition `tools` by name into the worker groups above.
    2. Node `supervisor`: cheap model, structured output choosing
       `next_worker` or FINISH. Routing errors here are the main failure
       mode, so give the eval set cases that could go to two workers.
    3. One node per worker: a react-style loop over only that worker's tools.
       Consider handing back control with `Command(goto=...)`
       (`langgraph.types`).
    4. Decide what state a worker can see. Passing the whole history is
       simple but costs tokens, so weigh passing a short brief instead.
    5. Same guardrails and budgets as the other graphs.
    Register it: GRAPHS["supervisor"] = build_graph in graphs/__init__.py.
    """
    raise NotImplementedError
