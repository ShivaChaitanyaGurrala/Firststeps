"""Test stubs for M5. Same rule as the other suites: no real LLM, no real
MCP server, no network. Fake the chat model (LangChain ships
`GenericFakeChatModel` in langchain_core.language_models.fake_chat_models)
and fake the MCP client. Un-skip each test as you implement its module.

M3's lesson: writing the tests is what exposed a documented decision that
had never actually been implemented. Write them as you go, not at the end.
"""

import pytest

TODO = pytest.mark.skip(reason="TODO: implement the module first")


@TODO
def test_get_llm_raises_when_the_model_for_a_role_is_not_configured():
    """llm.get_llm should fail loudly, not fall back to a default model."""


@TODO
def test_load_tools_returns_every_mcp_tool_with_its_description_unchanged():
    """mcp_tools.load_tools against a fake MCP client."""


@TODO
def test_is_mutating_fails_closed_for_a_tool_with_no_annotation():
    """An unannotated tool must be treated as mutating."""


@TODO
def test_mutating_tool_call_pauses_for_approval_and_denial_skips_the_call():
    """guardrails.approval_node with a fake mutating tool call."""


@TODO
def test_graph_stops_at_the_iteration_budget_with_a_clear_message():
    """A fake model that always calls a tool must not loop forever."""


@TODO
def test_get_system_prompt_raises_for_an_unwritten_version():
    """prompts.get_system_prompt with an empty or unknown version."""
