"""Graph 1: ReAct. The model reasons, calls a tool, sees the result, and
repeats until it can answer. Simplest architecture, and the baseline the
other two must beat to justify their extra structure.
"""

from typing import Any

from langchain_core.tools import BaseTool


def build_graph(tools: list[BaseTool]) -> Any:
    """Build and compile the ReAct graph.

    TODO(you): build it BY HAND with `StateGraph(AgentState)` first, so you
    see the loop. Do not start from `create_react_agent`.
    1. Node `agent`: call get_llm("cheap" or "strong", your choice, justify
       it) with `.bind_tools(tools)` and the system prompt from prompts.py.
    2. Node `tools`: langgraph.prebuilt's `ToolNode(tools)` is fine to use.
       Wrap tool output with guardrails.wrap_untrusted.
    3. Edges: START -> agent, then a conditional edge (`tools_condition` or
       your own) to `tools` or END, and `tools` -> agent. Put
       guardrails.approval_node between agent and tools, and end the turn
       when guardrails.within_budget returns False.
    4. Return `graph.compile(checkpointer=memory.get_checkpointer())`, with
       run metadata from config.agent_config_snapshot().
    5. Only once it works, rebuild it with the prebuilt agent and write down
       what the prebuilt one gives you and what it hides.
    Then register it: GRAPHS["react"] = build_graph in graphs/__init__.py.
    """
    raise NotImplementedError
