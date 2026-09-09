"""RAGAS scoring harness for the M4 RAG pipeline — this milestone's
acceptance bar. Scores: faithfulness, answer_relevancy, context_precision,
context_recall against eval_set.json's fixed (question, ground_truth) pairs.

LLM decision (resolved, see .env's OPENAI_API_KEY/OPENAI_MODEL comment):
OpenAI gpt-4o-mini plays both roles RAGAS's metrics need an LLM for —
(1) generating an answer from the retrieved context for each question
(there is no "answer" yet at this point in the pipeline — M4 only built
retrieval, not generation; that's a deliberately small, non-agentic
generation step just for this eval, distinct from M5's real LangGraph
agent), and (2) acting as the judge RAGAS itself uses internally to score
faithfulness/answer_relevancy. gpt-4o-mini specifically because this eval
is 55 questions over a small local movie-review corpus, not a production
judge workload — cheap/fast is the right tradeoff here.

Batching decision: role (1), the per-question answer generation, is what
this script directly controls and pays for one call per eval case — so it
goes through OpenAI's Batch API (https://platform.openai.com/docs/guides/batch)
instead of 55 synchronous chat.completions.create() calls. The Batch API
takes a JSONL file of requests, runs them together, and is billed at ~50%
of the equivalent synchronous cost in exchange for a completion window (up
to 24h, though small batches like this one typically finish in minutes) —
a good trade for a batch eval run that isn't on any interactive path. Role
(2), RAGAS's internal judge calls inside evaluate(), is NOT batched this
way — RAGAS drives those itself via its own async concurrency once you hand
it an LLM wrapper, and doesn't expose a hook to route them through the
Batch API instead. Only the answer-generation step below is restructured
for batching; RAGAS's own judge cost is a separate, smaller concern (it's
scoring already-short answer/context pairs, not generating long text).

pip install: ragas==0.4.3, langchain-community<0.4 (pinned together — see
pyproject.toml's comment for why), openai>=1.0.0, datasets — all already in
pyproject.toml as of the dependency-check pass.

Usage (once implemented):
    python -m evals.rag.run_ragas_eval
"""

import json
import time
from pathlib import Path
from typing import Literal, cast

from datasets import Dataset
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from openai import OpenAI
from pydantic import SecretStr
from ragas import evaluate
from ragas.dataset_schema import EvaluationResult
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.run_config import RunConfig

# Deliberately the legacy ragas.metrics (deprecated-but-functional in 0.4.3,
# not ragas.metrics.collections): evaluate() does `isinstance(m, Metric)`
# against the legacy base class internally, so collections-API metric
# instances (a different, unrelated base class for the newer .ascore()-based
# API) fail that check with "All metrics must be initialised metric
# objects" even though they're valid, constructed instances. Paired with
# LangchainLLMWrapper/LangchainEmbeddingsWrapper (not llm_factory/
# embedding_factory's modern objects) for the same reason: the modern
# embeddings object is missing the legacy embed_query() method these metrics
# call (AttributeError), and the modern LLM's own retry logic doesn't go
# through ragas's RunConfig-based backoff, so a single rate-limited call
# fails outright instead of retrying. Fully-legacy end to end avoids both.
from ragas.metrics import (
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

import rag_service.retriever

from evals.rag.config import settings

# Columns that come from our own dataset construction, not from a RAGAS
# metric score — whatever's left in result.to_pandas() after excluding
# these (plus custom_id/category, added after the fact) is a metric score
# column. Covers both v0.3-style ("question"/"answer"/...) and v0.4-style
# ("user_input"/"response"/...) column naming, since which one to_pandas()
# emits isn't pinned down across ragas patch versions.
_INPUT_COLUMNS = {
    "question",
    "answer",
    "contexts",
    "ground_truth",
    "user_input",
    "response",
    "retrieved_contexts",
    "reference",
}

_EVAL_SET_PATH = Path(__file__).parent / "eval_set.json"
_BATCH_INPUT_PATH = Path(__file__).parent / "batch_input.jsonl"
_RESULTS_PATH = Path(__file__).parent / "results.json"
_BATCH_ENDPOINT: Literal["/v1/chat/completions"] = "/v1/chat/completions"
_BATCH_COMPLETION_WINDOW: Literal["24h"] = (
    "24h"  # OpenAI's minimum/only supported window as of this writing.
)


def _load_eval_set() -> list[dict]:
    data = json.loads(_EVAL_SET_PATH.read_text())
    return data["cases"]


def _retrieve(question: str, title_id: int | None) -> list[str]:
    """Get the retrieved context strings for one question"""
    client = rag_service.retriever
    results = client.search(question, title_id=title_id)
    return [result["chunk_text"] for result in results]


def _build_batch_requests(cases_with_contexts: list[dict]) -> list[dict]:
    """Turn each case into one Batch API request line."""
    results = []
    for i, case in enumerate(cases_with_contexts):
        question = case["question"]
        contexts = case["contexts"]
        custom_id = case.get("custom_id", f"case_{i:03d}")

        request_dict = {
            "custom_id": custom_id,
            "method": "POST",
            "url": _BATCH_ENDPOINT,
            "body": {
                "model": settings.openai_model,  # gpt-4o-mini, from .env
                "messages": [
                    {
                        "role": "system",
                        "content": "Answer using only the given context.",
                    },
                    {
                        "role": "user",
                        "content": "\n".join(contexts) + "\nQuestion: " + question,
                    },
                ],
            },
        }
        results.append(request_dict)
    return results


def _submit_batch(requests: list[dict]) -> str:
    """Upload the batch request file and start the batch job. Returns the
    batch id to poll.

    TODO(you):
    1. Write `requests` to _BATCH_INPUT_PATH as JSONL (one json.dumps(...)
       request per line) — this is the file format the Batch API expects.
    2. `client = OpenAI(api_key=settings.openai_api_key)`
    3. `batch_file = client.files.create(file=open(_BATCH_INPUT_PATH, "rb"), purpose="batch")`
    4. `batch = client.batches.create(input_file_id=batch_file.id, endpoint=_BATCH_ENDPOINT, completion_window=_BATCH_COMPLETION_WINDOW)`
    5. Return `batch.id`.
    """
    with open(_BATCH_INPUT_PATH, "w") as f:
        for request in requests:
            f.write(json.dumps(request) + "\n")
    client = OpenAI(api_key=settings.openai_api_key)
    batch_file = client.files.create(
        file=open(_BATCH_INPUT_PATH, "rb"), purpose="batch"
    )
    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint=_BATCH_ENDPOINT,
        completion_window=_BATCH_COMPLETION_WINDOW,
    )
    return batch.id


_TERMINAL_BATCH_STATUSES = {"completed", "failed", "expired", "cancelled"}
_BATCH_POLL_SECONDS = 600  # 10 min — batches have a 24h SLA, no need to poll faster


def _wait_for_batch(batch_id: str) -> str:
    """Poll the batch job until it reaches a terminal status. Returns the
    output_file_id to download results from.
    """
    client = OpenAI(api_key=settings.openai_api_key)
    while True:
        batch = client.batches.retrieve(batch_id)
        counts = batch.request_counts
        completed = counts.completed if counts else 0
        total = counts.total if counts else 0
        print(f"Batch {batch_id}: {batch.status} ({completed}/{total} completed)")

        if batch.status == "completed":
            if not batch.output_file_id:
                raise RuntimeError(
                    f"Batch {batch_id} completed but has no output_file_id "
                    f"(errors: {batch.errors})"
                )
            return batch.output_file_id

        if batch.status in _TERMINAL_BATCH_STATUSES:
            raise RuntimeError(
                f"Batch {batch_id} ended with status {batch.status!r}: {batch.errors}"
            )

        time.sleep(_BATCH_POLL_SECONDS)


def _collect_batch_results(output_file_id: str) -> dict[str, str]:
    """Download the batch's output file and return {custom_id: answer_text}."""
    client = OpenAI(api_key=settings.openai_api_key)
    content = client.files.content(output_file_id)

    answers_by_id: dict[str, str] = {}
    for line in content.text.splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        custom_id = record["custom_id"]
        if record.get("error"):
            raise RuntimeError(f"Batch request {custom_id} failed: {record['error']}")
        body = record["response"]["body"]
        answers_by_id[custom_id] = body["choices"][0]["message"]["content"]
    return answers_by_id


def run() -> None:
    """Retrieve contexts per case, batch-generate answers via OpenAI, score
    everything with RAGAS, and write results to _RESULTS_PATH (not stdout —
    the UI reads this file for visualization rather than parsing a print).
    """
    cases = _load_eval_set()

    cases_with_contexts: list[dict] = []
    for i, case in enumerate(cases):
        contexts = _retrieve(case["question"], case.get("title_id"))
        cases_with_contexts.append({**case, "contexts": contexts})
        if i < len(cases) - 1:
            # Cohere rerank (hit inside _retrieve, via rag_service.retriever)
            # is capped at 10 req/min on a trial key — see config.py's
            # cohere_wait_seconds docstring.
            time.sleep(settings.cohere_wait_seconds)

    requests = _build_batch_requests(cases_with_contexts)
    batch_id = _submit_batch(requests)
    output_file_id = _wait_for_batch(batch_id)
    answers_by_id = _collect_batch_results(output_file_id)

    dataset_rows = [
        {
            "question": case["question"],
            "contexts": case["contexts"],
            "answer": answers_by_id[request["custom_id"]],
            "ground_truth": case["ground_truth"],
        }
        for case, request in zip(cases_with_contexts, requests)
    ]
    dataset = Dataset.from_list(dataset_rows)

    api_key = SecretStr(settings.openai_api_key)
    judge_llm = LangchainLLMWrapper(ChatOpenAI(model=settings.openai_model, api_key=api_key))
    judge_embeddings = LangchainEmbeddingsWrapper(
        OpenAIEmbeddings(model="text-embedding-ada-002", api_key=api_key)
    )
    metrics = [
        Faithfulness(llm=judge_llm),
        AnswerRelevancy(llm=judge_llm, embeddings=judge_embeddings),
        ContextPrecision(llm=judge_llm),
        ContextRecall(llm=judge_llm),
    ]
    # 55 rows x 4 metrics = 220 judge calls at RunConfig's default
    # max_workers=16 blew through our gpt-4o-mini tier's 200k TPM budget and
    # caused mass 429s — capping concurrency keeps us under it; ragas's own
    # tenacity-based retry/backoff (via this fully-legacy LLM/embeddings
    # pairing) handles the rest.
    # evaluate()'s declared return type is EvaluationResult | Executor (the
    # latter only when return_executor=True, which we never pass) — cast to
    # the type it actually is here so .to_pandas() below type-checks.
    result = cast(
        EvaluationResult,
        evaluate(dataset=dataset, metrics=metrics, run_config=RunConfig(max_workers=4)),
    )

    df = result.to_pandas()
    df["custom_id"] = [request["custom_id"] for request in requests]
    df["category"] = [case["category"] for case in cases_with_contexts]

    metric_columns = [
        column
        for column in df.columns
        if column not in _INPUT_COLUMNS and column not in ("custom_id", "category")
    ]
    output = {
        "aggregate": df[metric_columns].mean(numeric_only=True).to_dict(),
        "rows": df.to_dict(orient="records"),
    }
    _RESULTS_PATH.write_text(json.dumps(output, indent=2, default=str))
    print(f"Wrote RAGAS results ({len(dataset_rows)} rows) to {_RESULTS_PATH}")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
