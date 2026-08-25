from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    tmdb_api_token: str = ""
    database_url: str = "postgresql+psycopg2://tmdb_app:tmdb_local_dev_pw@localhost:5432/tmdb_local"
    log_level: str = "INFO"


settings = Settings()
