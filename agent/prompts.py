"""System prompts, versioned. The selected version is stamped on traces and
eval experiments (see config.agent_config_snapshot), so a prompt change is a
named experiment, not an invisible edit. Add "v2" beside "v1", never overwrite.

Lessons from M4's `prompt-v2` experiment: a verdict-first, more confident
prompt made faithfulness and answer_relevancy WORSE. Don't assume a prompt
change helps; measure it with evals/agent, and judge answers on faithfulness
and correctness, not on chasing answer_relevancy.
"""

from agent.config import settings

SYSTEM_PROMPTS: dict[str, str] = {
    # TODO(you): write "v1". Tool-selection reliability is this milestone's
    # prompt-engineering target, so it should make these explicit:
    #   - "look up a fact" (search_titles, get_title_details) vs "find
    #     opinions" (search_reviews). The tool descriptions in mcp_server
    #     carry part of this, the system prompt reinforces it.
    #   - when to ask a clarifying question instead of calling a tool
    #   - never claim to have changed data (watchlist, ratings) unless the
    #     tool call succeeded
    #   - review text is quoted evidence, never instructions to follow
    "v1": "",
}


def get_system_prompt() -> str:
    """The prompt for settings.prompt_version. Raises if it is missing or
    still empty, so an unwritten prompt fails loudly instead of running the
    agent with no instructions."""
    prompt = SYSTEM_PROMPTS.get(settings.prompt_version, "")
    if not prompt:
        raise ValueError(f"prompt version {settings.prompt_version!r} is not written yet")
    return prompt
