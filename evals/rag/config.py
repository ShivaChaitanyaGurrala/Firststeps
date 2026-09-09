"""Settings for evals/rag/run_ragas_eval.py only.

Kept separate from rag_service.config.Settings deliberately: rag_service
never calls OpenAI in production (Voyage for embeddings, Cohere for
reranking) — OpenAI is used only by this eval harness, as (1) the answer
generator for the batch-generation step and (2) RAGAS's internal judge.
Folding openai_api_key/openai_model into rag_service's Settings would leak
an eval-only credential into a service config surface that never reads it
at runtime. See .env.example's OPENAI_API_KEY/OPENAI_MODEL comment.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Cohere's rerank endpoint (called once per _retrieve during run()'s
    # per-case retrieval loop, via rag_service.retriever.search) is capped
    # at 10 requests/min on a trial key — pause this long between cases so
    # the loop doesn't 429. Not a rag_service setting: this throttle exists
    # for the eval harness's synchronous per-case loop, not for rag_service
    # itself, which has no such loop in its own request path.
    cohere_wait_seconds: float = 7.0


settings = Settings()
