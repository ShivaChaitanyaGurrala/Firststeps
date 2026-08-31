"""Normalized error types for the MCP tool layer.

data_service.main already turns any domain NotFoundError into a clean
`{"detail": "<message>"}` JSON body on a 404 — see
data_service/services/exceptions.py and data_service/main.py's
not_found_handler. The gap M3 closes is on THIS side: http_client.py
currently lets httpx.HTTPStatusError and httpx.TransportError escape
straight out of DataServiceClient methods, which means a tool call either
crashes with a raw httpx traceback, or an uncaught exception's internal
text (stack frames, hostnames, driver errors) reaches the LLM — exactly what
the M3 plan's "normalized error shapes... never raw stack traces" rules out.

TODO(you):
1. Flesh out the exception hierarchy below. `NotFoundError` and
   `UpstreamError` are a reasonable minimum split (a tool can decide to
   surface a 404 differently from "the data service errored"), but decide
   for yourself whether more subclasses earn their keep.
2. Implement `from_httpx_error`: read `exc.response.status_code` and try
   `exc.response.json()["detail"]` for the message (data_service's shape),
   falling back to `exc.response.text` if the body isn't JSON — then return
   the right subclass instance. Keep the message short and LLM-safe.
3. In http_client.py, route `response.raise_for_status()` through this —
   catch `httpx.HTTPStatusError` and `raise from_httpx_error(exc) from exc`.
   Decide whether that belongs in every method individually or behind one
   shared request helper (see the TODO at the top of http_client.py).
4. In each tools/*.py module, catch these exceptions and re-raise as
   `mcp.server.mcpserver.exceptions.ToolError(str(exc))` — the SDK's own
   error type (.venv/Lib/site-packages/mcp/server/mcpserver/exceptions.py),
   which the SDK turns into a clean `is_error: True` tool result instead of
   an unhandled-exception traceback reaching the client.
"""

import httpx


class DataServiceError(Exception):
    """Base for every normalized error DataServiceClient can raise."""


class NotFoundError(DataServiceError):
    """The data_service returned 404 — the requested entity doesn't exist."""


class UpstreamError(DataServiceError):
    """The data_service returned an unexpected 4xx/5xx."""


def from_httpx_error(exc: httpx.HTTPStatusError) -> DataServiceError:
    try:
        message = exc.response.json()["detail"]
    except Exception:
        message = exc.response.text
    if exc.response.status_code == 404:
        return NotFoundError(message)
    return UpstreamError(message)
