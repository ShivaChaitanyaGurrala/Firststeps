"""Settings for the agent. Same pattern as rag_service/config.py: every
tunable is an env-overridable field, and agent_config_snapshot() stamps the
active values onto traces so runs stay attributable.

Provider is decided (OpenAI-compatible via langchain-openai's ChatOpenAI,
see llm.py) and cheap/strong now map to one model at two reasoning-effort
levels, not two different models. cheap_model/strong_model are still left
empty on purpose — set both to the same value ("gpt-6-luna" or whatever you
land on) in .env; llm.py raises loudly if either is empty rather than
silently reusing one for the other.
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # mcp_server must be running with MCP_TRANSPORT=streamable-http. The path
    # suffix is the SDK's default, verify it with the MCP Inspector.
    mcp_server_url: str = "http://127.0.0.1:8010/mcp"
    mcp_timeout_seconds: float = 30.0

    llm_provider: str = "openai"  # ChatOpenAI; works for direct OpenAI or Azure
    llm_api_key: str = ""
    cheap_model: str = ""  # search/routing steps; same model as strong_model
    strong_model: str = ""  # recommendation reasoning; same model as cheap_model

    # Role is expressed as reasoning effort on one model, not a model swap.
    # See llm.py's get_llm TODO for why low/high were picked over the
    # cheaper non-reasoning tier and the pricier xhigh/max tiers. Verify
    # these literal strings against the model's actual accepted values.
    cheap_reasoning_effort: str = "low"
    strong_reasoning_effort: str = "high"

    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2
    max_iterations: int = 8  # hard cap on graph steps per turn (guardrails.py)
    prompt_version: str = "v1"  # key into prompts.SYSTEM_PROMPTS

    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    # Own env var (not LANGSMITH_PROJECT) so agent traces don't land in
    # rag_service's project when both read the same .env.
    agent_langsmith_project: str = "tmdb-agent"


settings = Settings()

# The LangSmith SDK reads os.environ, not Settings, and pydantic-settings does
# not write .env into os.environ. Doing it here guarantees it runs before any
# entry point (cli.py, evals) first touches a traced function.
if settings.langsmith_tracing:
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
    os.environ.setdefault("LANGSMITH_PROJECT", settings.agent_langsmith_project)


def agent_config_snapshot() -> dict[str, int | str]:
    """Active knob values, for trace and eval-experiment metadata."""
    return {
        "llm_provider": settings.llm_provider,
        "cheap_model": settings.cheap_model,
        "cheap_reasoning_effort": settings.cheap_reasoning_effort,
        "strong_model": settings.strong_model,
        "strong_reasoning_effort": settings.strong_reasoning_effort,
        "prompt_version": settings.prompt_version,
        "max_iterations": settings.max_iterations,
    }
