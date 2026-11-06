"""RagServiceClient's wait times and failure handling, over httpx.MockTransport
so nothing needs rag_service running."""

import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError

import errors
import rag_client
import tools.rag_tools as rag_tools


def _client_with(handler) -> rag_client.RagServiceClient:
    client = rag_client.RagServiceClient()
    client._client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://test"
    )
    return client


def test_timeouts_are_explicit():
    timeout = rag_client.RagServiceClient()._client.timeout
    assert timeout.read == 20.0
    assert timeout.connect == 2.0


@pytest.mark.parametrize(
    "exc", [httpx.ReadTimeout("internal host detail"), httpx.ConnectError("internal host detail")]
)
def test_transport_failure_becomes_a_normalized_error(exc):
    def handler(request):
        raise exc

    with pytest.raises(errors.UpstreamError) as exc_info:
        _client_with(handler).search_reviews("pacing")

    assert "internal host detail" not in str(exc_info.value)


def test_503_detail_reaches_the_caller():
    def handler(request):
        return httpx.Response(
            503,
            json={"detail": "Review search is rate limited right now. Retry in about 60 seconds."},
            headers={"Retry-After": "60"},
        )

    with pytest.raises(errors.UpstreamError, match="Retry in about 60 seconds"):
        _client_with(handler).search_reviews("pacing")


def test_tool_turns_a_timeout_into_a_tool_error(monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("internal host detail")

    monkeypatch.setattr(rag_tools, "_client", _client_with(handler))

    with pytest.raises(ToolError, match="timed out or is unreachable"):
        rag_tools.search_reviews("pacing")
