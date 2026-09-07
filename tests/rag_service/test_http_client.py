"""Same httpx.MockTransport pattern as tests/data_service/test_tmdb_client.py,
adapted for DataServiceClient's sync httpx.Client (rag_service never uses
async httpx, unlike data_service's TmdbClient).
"""

import httpx
import pytest

from rag_service.errors import UpstreamError
from rag_service.http_client import DataServiceClient


def _client_with_handler(handler) -> DataServiceClient:
    client = DataServiceClient()
    client._client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://test")
    return client


def test_list_reviews_returns_parsed_json_with_correct_params():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/reviews"
        assert request.url.params["limit"] == "50"
        assert request.url.params["offset"] == "100"
        return httpx.Response(200, json=[{"id": "abc", "title": "Inception"}])

    client = _client_with_handler(handler)
    result = client.list_reviews(limit=50, offset=100)
    assert result == [{"id": "abc", "title": "Inception"}]


def test_list_reviews_raises_normalized_error_on_http_status_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "db down"})

    client = _client_with_handler(handler)
    with pytest.raises(UpstreamError, match="db down"):
        client.list_reviews()
