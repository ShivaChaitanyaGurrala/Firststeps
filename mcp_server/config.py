"""Settings for the MCP server: where to find the running FastAPI data service.

TODO(you): define a pydantic-settings class here, same pattern as
data_service/config.py (BaseSettings + SettingsConfigDict(env_file=".env")).

Field needed:
  data_service_base_url: str, default "http://127.0.0.1:8000"

Then instantiate it as `settings = ...` at module level, same as data_service does.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_service_base_url: str = "http://127.0.0.1:8000"


settings = Settings()
