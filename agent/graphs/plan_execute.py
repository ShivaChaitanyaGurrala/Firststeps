"""Graph 2: planner-executor. One node writes a multi-step plan up front,
an executor carries out each step with tools, and a final node composes the
answer. Better for multi-part requests ("compare these three movies and add
the best one to my watchlist"), at the cost of more model calls and a plan
that can go stale when a step's result changes what should happen next.
"""

from typing import Any

from langchain_core.tools import BaseTool


def build_graph(tools: list[BaseTool]) -> Any:
    """Build and compile the planner-executor graph.

    TODO(you):
    1. Extend AgentState (state.py) with `plan` and the current step index.
    2. Node `planner`: strong model, returns the plan as validated structured
       output (a list of steps), not free text you have to parse.
    3. Node `executor`: for the current step, run a small tool-using loop
       (reuse react.build_graph as a subgraph if it fits).
    4. Node `replan`: after each step decide continue, revise the plan, or
       finish. The failure mode to test for is "plan says X, step 1's result
       makes X pointless, agent does X anyway".
    5. Same guardrails as ReAct: approval before mutating tools, and a step
       budget.
    Register it: GRAPHS["plan_execute"] = build_graph in graphs/__init__.py.
    """
    raise NotImplementedError
