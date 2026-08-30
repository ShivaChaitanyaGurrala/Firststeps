"""M2 tests — run these after filling in each TODO to check your work.

Same pattern as test_tools.py: each test opens its Client fixture itself
with `async with` (see conftest.py's mcp_client docstring for why), and
nothing here touches a real running data_service or a real LLM.
"""

import json


async def test_get_title_resource(mcp_client, sample_title):
    async with mcp_client as connected:
        result = await connected.read_resource(f"tmdb://title/{sample_title.id}")
    body = json.loads(result.contents[0].text)
    assert body["title"] == "Inception"


async def test_get_watchlist_resource(mcp_client, sample_title):
    async with mcp_client as connected:
        await connected.call_tool("add_to_watchlist", {"title_id": sample_title.id})
        result = await connected.read_resource("tmdb://watchlist")
    body = json.loads(result.contents[0].text)
    assert len(body) == 1
    assert body[0]["title_id"] == sample_title.id


async def test_summarize_watchlist_prompt(mcp_client, sample_title):
    async with mcp_client as connected:
        # No `notes` passed here on purpose — a title with no notes is the
        # regression case for a `None`-vs-missing-key formatting bug.
        await connected.call_tool("add_to_watchlist", {"title_id": sample_title.id})
        result = await connected.get_prompt("summarize_watchlist")
    assert len(result.messages) >= 1
    assert result.messages[0].role == "user"
    embedded_text = result.messages[0].content.resource.text
    assert sample_title.title in embedded_text
    assert "None" not in embedded_text


async def test_recommend_for_mood_prompt(mcp_client):
    async with mcp_client as connected:
        result = await connected.get_prompt("recommend_for_mood", {"mood": "cozy"})
    assert len(result.messages) >= 1
    assert "cozy" in str(result.messages[0].content).lower()


async def test_generate_watchlist_blurb(mcp_sampling_client, sample_title):
    async with mcp_sampling_client as connected:
        # No `notes` passed here on purpose — same regression case as
        # test_summarize_watchlist_prompt, but for _sample_blurb's formatting.
        await connected.call_tool("add_to_watchlist", {"title_id": sample_title.id})
        result = await connected.call_tool("generate_watchlist_blurb", {})
    assert not result.is_error
    assert result.structured_content["blurb"] == "A canned test blurb."
    assert result.structured_content["model"] == "test-model"
    sent_text = mcp_sampling_client.captured_sampling_params[-1].messages[0].content.text
    assert sample_title.title in sent_text
    assert "None" not in sent_text
