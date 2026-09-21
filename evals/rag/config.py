"""Settings for evals/rag/run_ragas_eval.py only.

Kept separate from rag_service.config.Settings deliberately: rag_service
never calls OpenAI in production (Voyage for embeddings, Cohere for
reranking) — OpenAI is used only by this eval harness, as (1) the answer
generator for the per-question answer step and (2) RAGAS's internal judge.
Folding openai_api_key/openai_model into rag_service's Settings would leak
an eval-only credential into a service config surface that never reads it
at runtime. See .env.example's OPENAI_API_KEY/OPENAI_MODEL comment.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Name of the LangSmith Dataset sync_dataset.py mirrors eval_set.json
    # into, and run_ragas_eval.py's evaluate() call reads examples from.
    eval_dataset_name: str = "tmdb-rag-eval-set"

    # Cohere's trial key allows 10 req/min; diagnose_retrieval.py pauses this
    # long after each Cohere call so its per-case loop doesn't 429.
    cohere_wait_seconds: float = 7.0


settings = Settings()
