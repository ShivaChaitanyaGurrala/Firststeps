"""One test per MCP tool (11 total) — run this after any tool/backend change
to confirm nothing regressed. Uses the mcp_client fixture from conftest.py,
so it never touches a real running data_service or a real TMDB call.

Each test opens `mcp_client` itself with `async with` rather than receiving
an already-connected client — see the comment on the fixture in conftest.py
for why (anyio task-group vs. pytest-asyncio fixture-teardown Task mismatch).
"""


async def test_search_titles(mcp_client, sample_title):
    async with mcp_client as connected:
        result = await connected.call_tool("search_titles", {"query": "Inception"})
    assert not result.is_error
    assert result.structured_content["results"][0]["id"] == sample_title.id


async def test_get_title_details(mcp_client, sample_title):
    async with mcp_client as connected:
        result = await connected.call_tool("get_title_details", {"title_id": sample_title.id})
    assert not result.is_error
    assert result.structured_content["title"] == "Inception"


async def test_get_recommendations_by_genre(mcp_client):
    async with mcp_client as connected:
        result = await connected.call_tool(
            "get_recommendations", {"based_on": "genre", "genre": "Action"}
        )
    assert not result.is_error
    assert "results" in result.structured_content


async def test_get_recommendations_by_watchlist(mcp_client, sample_title):
    async with mcp_client as connected:
        await connected.call_tool("add_to_watchlist", {"title_id": sample_title.id})
        result = await connected.call_tool("get_recommendations", {"based_on": "watchlist"})
    assert not result.is_error
    assert "results" in result.structured_content


async def test_add_to_watchlist(mcp_client, sample_title):
    async with mcp_client as connected:
        result = await connected.call_tool(
            "add_to_watchlist", {"title_id": sample_title.id, "notes": "weekend"}
        )
    assert not result.is_error
    body = result.structured_content
    assert body["title_id"] == sample_title.id
    assert body["title"] == "Inception"
    assert body["notes"] == "weekend"


async def test_list_watchlist(mcp_client, sample_title):
    async with mcp_client as connected:
        await connected.call_tool("add_to_watchlist", {"title_id": sample_title.id})
        result = await connected.call_tool("list_watchlist", {})
    assert not result.is_error
    assert len(result.structured_content["items"]) == 1


async def test_remove_from_watchlist(mcp_client, sample_title):
    async with mcp_client as connected:
        added = await connected.call_tool("add_to_watchlist", {"title_id": sample_title.id})
        entry_id = added.structured_content["id"]
        result = await connected.call_tool("remove_from_watchlist", {"watchlist_id": entry_id})
    assert not result.is_error
    assert result.structured_content["success"] is True


async def test_rate_title(mcp_client, sample_title):
    async with mcp_client as connected:
        result = await connected.call_tool(
            "rate_title", {"title_id": sample_title.id, "score": 9, "review": "great"}
        )
    assert not result.is_error
    body = result.structured_content
    assert body["score"] == 9
    assert body["title"] == "Inception"


async def test_create_list(mcp_client):
    async with mcp_client as connected:
        result = await connected.call_tool("create_list", {"name": "Weekend picks"})
    assert not result.is_error
    assert result.structured_content["name"] == "Weekend picks"


async def test_add_to_list(mcp_client, sample_title):
    async with mcp_client as connected:
        created = await connected.call_tool("create_list", {"name": "Weekend picks"})
        list_id = created.structured_content["id"]
        result = await connected.call_tool(
            "add_to_list", {"list_id": list_id, "title_id": sample_title.id}
        )
    assert not result.is_error
    assert result.structured_content["items"][0]["title_id"] == sample_title.id


async def test_sync_status(mcp_client):
    async with mcp_client as connected:
        result = await connected.call_tool("sync_status", {})
    assert not result.is_error
    assert result.structured_content["runs"] == []


async def test_trigger_sync(mcp_client, monkeypatch):
    from data_service.routers import sync as sync_router

    calls = []

    async def fake_run(*args, run_id=None, **kwargs):
        calls.append(run_id)

    monkeypatch.setattr(sync_router.bulk_seed, "run", fake_run)

    async with mcp_client as connected:
        result = await connected.call_tool("trigger_sync", {"run_type": "bulk_seed"})
    assert not result.is_error
    body = result.structured_content
    assert body["status"] == "queued"
    assert calls == [body["run_id"]]
