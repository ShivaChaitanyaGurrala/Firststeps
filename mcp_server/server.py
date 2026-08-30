"""MCP server entry point for the TMDB local catalog.

TODO(you), in order:
1. Import MCPServer: `from mcp.server import MCPServer`
2. Instantiate it at module level: `mcp = MCPServer("TMDB Local")`
   (must happen before step 3 — the tool modules import this instance)
3. Import each tools/*.py module for its side effect (each one does
   `from server import mcp` then decorates functions with `@mcp.tool()`,
   which registers them onto this same `mcp` instance at import time):
     import tools.catalog_tools
     import tools.watchlist_tools
     import tools.rating_tools
     import tools.list_tools
     import tools.sync_tools
   Think about *why* these imports must come after step 2, not before —
   what would break if the order were reversed?
4. Add a `if __name__ == "__main__":` block that calls `mcp.run()` — no
   transport argument needed, stdio is the default.

Test with (from inside this mcp_server/ directory):
    mcp dev server.py
This launches the MCP Inspector web UI and spawns this server over stdio.
In the Inspector: confirm all 11 tools list correctly via `tools/list`, then
invoke each manually and watch the raw JSON-RPC request/response frames.

Sanity check standalone (should sit silent on stdin — any stray stdout output
means something is corrupting the protocol stream):
    mcp run server.py

M2 additions: resources/catalog_resources.py, prompts/catalog_prompts.py, and
tools/sampling_tools.py register onto this same `mcp` instance the same way
the M1 tool modules do — import for side effect, nothing else needed here.
Transport is chosen at the bottom via config.settings.mcp_transport (stdio by
default, so `mcp dev server.py` keeps working unmodified); set
MCP_TRANSPORT=streamable-http in .env to run this as an HTTP server instead
and test that transport with an HTTP-capable MCP client/Inspector session.
"""

from mcp_instance import mcp
from config import settings

import tools.catalog_tools
import tools.sync_tools
import tools.watchlist_tools
import tools.rating_tools
import tools.list_tools
import tools.sampling_tools

import resources.catalog_resources
import prompts.catalog_prompts

if __name__ == "__main__":

    if settings.mcp_transport == "streamable-http":
        mcp.run(
            transport="streamable-http",
            host=settings.mcp_http_host,
            port=settings.mcp_http_port,
        )
    else:
        mcp.run()
