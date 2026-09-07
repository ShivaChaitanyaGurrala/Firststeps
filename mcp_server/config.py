"""Settings for the MCP server: where to find the running FastAPI data service.

TODO(you): define a pydantic-settings class here, same pattern as
data_service/config.py (BaseSettings + SettingsConfigDict(env_file=".env")).

Field needed:
  data_service_base_url: str, default "http://127.0.0.1:8000"

Then instantiate it as `settings = ...` at module level, same as data_service does.
"""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_service_base_url: str = "http://127.0.0.1:8000"
    # M4: rag_service is a separate backend service (owns Chroma/Voyage/
    # Cohere), not part of data_service — see rag_service/config.py's
    # docstring for why. rag_tools.py's search_reviews tool calls this one
    # instead of data_service_base_url.
    rag_service_base_url: str = "http://127.0.0.1:8020"

    # M2: which transport __main__ starts with. stdio stays the default so
    # `mcp dev server.py` / `mcp run server.py` behave exactly as in M1;
    # override via MCP_TRANSPORT=streamable-http in .env (or the env var
    # directly) to test the HTTP transport instead.
    mcp_transport: Literal["stdio", "streamable-http"] = "stdio"
    mcp_http_host: str = "127.0.0.1"
    mcp_http_port: int = 8010


settings = Settings()
