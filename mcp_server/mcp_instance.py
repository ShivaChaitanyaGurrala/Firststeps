"""The single shared MCPServer instance.

Lives in its own module, separate from server.py, so that no matter how
server.py gets loaded (as __main__, as "server_module" via the mcp CLI's
importlib loader, etc.) every tools/*.py module that does
`from mcp_instance import mcp` resolves to the SAME object. If this
instance lived in server.py itself, a sibling module importing "server"
by name could trigger Python to re-import and re-execute server.py under
a different module identity, creating a second, disconnected MCPServer
that tools would register onto instead of the one actually being run.
"""

from mcp.server import MCPServer

mcp = MCPServer("Firststeps MCP Server")
