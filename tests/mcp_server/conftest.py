"""Wires the MCP tools to the isolated data_service test client instead of a
real running server, so these tests need no Docker/uvicorn to run — just the
same Postgres test DB (`tmdb_local_test`) the data_service suite already uses.

mcp_server/ isn't a proper importable package (tools/*.py use bare
`from mcp_instance import mcp`), so it must be on sys.path directly, not just
its parent, matching how `mcp dev server.py` / `mcp run server.py` are run
from inside that directory.
"""

import sys
from pathlib import Path

import pytest

_MCP_SERVER_DIR = Path(__file__).resolve().parents[2] / "mcp_server"
sys.path.insert(0, str(_MCP_SERVER_DIR))

from tests.data_service.conftest import client, db_session, sample_title, test_engine  # noqa: F401,E402

import server  # noqa: E402  (import-time side effect: registers all tools/resources/prompts onto mcp_instance.mcp)
import tools.catalog_tools as catalog_tools  # noqa: E402
import tools.list_tools as list_tools  # noqa: E402
import tools.rating_tools as rating_tools  # noqa: E402
import tools.sampling_tools as sampling_tools  # noqa: E402
import tools.sync_tools as sync_tools  # noqa: E402
import tools.watchlist_tools as watchlist_tools  # noqa: E402
import resources.catalog_resources as catalog_resources  # noqa: E402
import prompts.catalog_prompts as catalog_prompts  # noqa: E402
from mcp.client.client import Client  # noqa: E402
from mcp_instance import mcp  # noqa: E402

# Every module below holds a module-level `_client = DataServiceClient()` —
# these are the ones the mcp_client fixture repoints at the isolated test DB.
_TOOL_MODULES = (
    catalog_tools,
    sync_tools,
    watchlist_tools,
    rating_tools,
    list_tools,
    sampling_tools,
    catalog_resources,
    catalog_prompts,
)


@pytest.fixture()
def mcp_client(client, monkeypatch):
    """An *unentered* in-memory MCP Client wired to the real tool
    registrations, with every tool's DataServiceClient pointed at the
    per-test isolated data_service `client` (TestClient + SAVEPOINT-rolled-
    back db_session) instead of a real network call to a running uvicorn
    instance.

    Deliberately not opened here (no `async with` around a yield): anyio
    requires a task group's enter and exit to happen in the exact same
    asyncio Task, but pytest-asyncio runs an async fixture's setup and its
    post-yield teardown as two separate Tasks. Opening it here would split
    Client(mcp)'s task group across that boundary and fail on teardown with
    "cancel scope in a different task". Each test opens/closes it itself
    with `async with mcp_client as connected:` instead, keeping the whole
    lifecycle inside one unbroken coroutine/Task.
    """
    for module in _TOOL_MODULES:
        monkeypatch.setattr(module._client, "_client", client)

    return Client(mcp)


@pytest.fixture()
def mcp_sampling_client(client, monkeypatch):
    """Like mcp_client, but wired with a canned sampling_callback so tests can
    drive tools/sampling_tools.py's generate_watchlist_blurb without a real
    LLM or MCP host in the loop — the callback stands in for "the client's
    LLM" and answers every CreateMessageRequest with a fixed blurb.

    The received `params` on each call is recorded on
    `.captured_sampling_params` (a list, oldest first) so tests can assert on
    what _sample_blurb actually sent — e.g. that a missing `notes` field
    didn't leak a literal "None" into the formatted prompt text.
    """
    from mcp_types import CreateMessageResult, TextContent

    captured_sampling_params = []

    async def fake_sampling_callback(context, params):
        captured_sampling_params.append(params)
        return CreateMessageResult(
            role="assistant",
            content=TextContent(text="A canned test blurb."),
            model="test-model",
        )

    for module in _TOOL_MODULES:
        monkeypatch.setattr(module._client, "_client", client)

    sampling_client = Client(mcp, sampling_callback=fake_sampling_callback)
    sampling_client.captured_sampling_params = captured_sampling_params
    return sampling_client
