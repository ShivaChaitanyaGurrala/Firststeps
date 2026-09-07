import httpx

from rag_service.errors import NotFoundError, UpstreamError, from_httpx_error


def _status_error(status_code: int, *, json=None, text: str | None = None) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "http://test/reviews")
    if json is not None:
        response = httpx.Response(status_code, json=json, request=request)
    else:
        response = httpx.Response(status_code, text=text or "", request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


def test_404_maps_to_not_found_error():
    exc = _status_error(404, json={"detail": "review not found"})
    err = from_httpx_error(exc)
    assert isinstance(err, NotFoundError)
    assert str(err) == "review not found"


def test_500_maps_to_upstream_error():
    exc = _status_error(500, json={"detail": "internal error"})
    err = from_httpx_error(exc)
    assert isinstance(err, UpstreamError)
    assert str(err) == "internal error"


def test_non_json_body_falls_back_to_response_text():
    exc = _status_error(502, text="Bad Gateway")
    err = from_httpx_error(exc)
    assert isinstance(err, UpstreamError)
    assert str(err) == "Bad Gateway"
