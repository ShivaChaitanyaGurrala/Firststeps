"""RAGAS scoring harness for the M4 RAG pipeline. Scores faithfulness,
answer_relevancy, context_precision and context_recall against a LangSmith
Dataset mirroring eval_set.json (run sync_dataset.py first, and again
whenever eval_set.json changes).

OpenAI gpt-4o-mini plays two roles: the answer generator (M4 only built
retrieval, so this is a small non-agentic generation step just for the
eval) and the RAGAS judge. Cheap/fast is the right tradeoff for 55
questions over a small local corpus.

langsmith.evaluate() is the harness: it runs _target once per example with
bounded concurrency, traces each case as its own experiment run
(retrieve -> generate -> score in one place), and applies the evaluators
per example. RAGAS's own bulk evaluate() only produces one flat trace, and
a hand-rolled per-case loop loses concurrency. The same pattern fits M5's
LangGraph agent eval.

Metrics come from ragas.metrics.collections (the modern API, replacing the
legacy ragas.metrics/single_turn_score path). Each metric takes only the
fields it scores against (see _METRIC_ARGS); the judge is built with
llm_factory (instructor-backed structured output) and OpenAIEmbeddings, and
each metric may use a different LLM if needed. MetricResult carries .reason
as well as .value, which is surfaced as the LangSmith comment.

Usage:
    python -m evals.rag.sync_dataset   # whenever eval_set.json changes
    python -m evals.rag.run_ragas_eval
"""

import asyncio
from collections.abc import Callable
from functools import lru_cache
import json
from pathlib import Path

from langsmith import evaluate, traceable
from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI, OpenAI
from ragas.embeddings import OpenAIEmbeddings
from ragas.llms import llm_factory
from ragas.metrics.collections import (
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

import rag_service.retriever
from rag_service.config import retrieval_config_snapshot

from evals.rag.config import settings

_RESULTS_PATH = Path(__file__).parent / "results.json"

# Cohere's trial key allows 10 calls/min; concurrent cases can burst past it,
# which rerank() absorbs by retrying 429s with backoff. Keep this low so
# retries stay rare.
_MAX_CONCURRENCY = 2
_EXPERIMENT_PREFIX = "rerank-top8"
_REQUEST_TIMEOUT_SECONDS = 60  # the openai default is 600s, long enough to hang a whole run
_METRIC_TIMEOUT_SECONDS = 240  # hard cap: a hang becomes an error, not a stalled run
_METRIC_KEYS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")


def _retrieve(question: str, title_id: int | None) -> list[str]:
    """Get the retrieved context strings for one question"""
    client = rag_service.retriever
    results = client.search(question, title_id=title_id)
    return [result["chunk_text"] for result in results]


@lru_cache(maxsize=1)
def _generation_client() -> OpenAI:
    """wrap_openai makes each generation call a child llm span (with token
    usage) under eval_case."""
    return wrap_openai(
        OpenAI(api_key=settings.openai_api_key, timeout=_REQUEST_TIMEOUT_SECONDS),
        chat_name="generate_answer",
    )


@traceable(name="build_answer_prompt", run_type="prompt")
def _build_request_body(question: str, contexts: list[str]) -> dict:
    """The chat.completions.create() kwargs for one question, used by
    _target below."""
    return {
        "model": settings.openai_model,  # gpt-4o-mini, from .env
        "temperature": 0,  # keeps answers stable across tuning runs
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
    }


# rag_search and its children nest under this span via the call stack.
@traceable(name="eval_case", run_type="chain")
def _target(inputs: dict) -> dict:
    """langsmith.evaluate()'s target function — signature must
    be exactly (inputs: dict) -> dict, where `inputs` is one Dataset
    example's stored inputs (see sync_dataset.py: {"question": ...,
    "title_id": ...}).
    """
    contexts = _retrieve(inputs["question"], inputs.get("title_id"))
    response = _generation_client().chat.completions.create(
        **_build_request_body(inputs["question"], contexts)
    )
    answer = response.choices[0].message.content
    return {"contexts": contexts, "answer": answer}


_METRIC_ARGS: dict[str, Callable[[dict, dict, dict], dict]] = {
    "faithfulness": lambda inputs, outputs, _: {
        "user_input": inputs["question"],
        "response": outputs["answer"],
        "retrieved_contexts": outputs["contexts"],
    },
    "answer_relevancy": lambda inputs, outputs, _: {
        "user_input": inputs["question"],
        "response": outputs["answer"],
    },
    "context_precision": lambda inputs, outputs, reference_outputs: {
        "user_input": inputs["question"],
        "reference": reference_outputs["ground_truth"],
        "retrieved_contexts": outputs["contexts"],
    },
    "context_recall": lambda inputs, outputs, reference_outputs: {
        "user_input": inputs["question"],
        "retrieved_contexts": outputs["contexts"],
        "reference": reference_outputs["ground_truth"],
    },
}


def _make_ragas_evaluator(key: str):
    """Wrap one RAGAS metric as a LangSmith evaluator. Each call builds a fresh
    metric and OpenAI client: score() runs on a new event loop every time, and
    an async client's connection pool can't be shared across loops (reuse hung
    runs). wait_for is a hard cap so a stuck call fails instead of stalling."""
    build_args = _METRIC_ARGS[key]

    def _evaluator(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
        if "answer" not in outputs:
            return {"key": key, "score": None, "comment": "target failed, not scored"}
        metric = _build_metric(key)
        kwargs = build_args(inputs, outputs, reference_outputs)
        result = asyncio.run(
            asyncio.wait_for(metric.ascore(**kwargs), timeout=_METRIC_TIMEOUT_SECONDS)
        )
        return {"key": key, "score": result.value, "comment": result.reason}

    _evaluator.__name__ = f"ragas_{key}"
    return _evaluator


def _trace_judge(llm, metric_key: str):
    """Give one metric its own judge LLM whose every structured-output step is
    a named span (e.g. faithfulness.StatementGeneratorOutput, chain) wrapping
    the ragas_judge llm span, so steps are filterable per metric."""
    original = llm.agenerate

    async def agenerate(prompt, response_model):
        step = traceable(
            name=f"{metric_key}.{response_model.__name__}",
            run_type="chain",
            process_inputs=lambda _: {
                "prompt": prompt,
                "response_model": response_model.__name__,
            },
        )(original)
        return await step(prompt, response_model)

    llm.agenerate = agenerate
    return llm


def _trace_embeddings(embeddings):
    """Embedding calls as run_type="embedding" spans (wrap_openai only covers
    chat completions)."""
    for method in ("aembed_text", "aembed_texts"):
        setattr(
            embeddings,
            method,
            traceable(name=f"embedding.{method}", run_type="embedding")(
                getattr(embeddings, method)
            ),
        )
    return embeddings


def _summarize(results, metric_keys: list[str]) -> tuple[list[dict], dict]:
    """Flatten an evaluate() result into results.json rows plus per-metric means."""
    rows = []
    for item in results:
        example = item["example"]
        outputs = item["run"].outputs or {}
        row = {
            "user_input": (example.inputs or {}).get("question"),
            "retrieved_contexts": outputs.get("contexts"),
            "response": outputs.get("answer"),
            "reference": (example.outputs or {}).get("ground_truth"),
            "custom_id": (example.metadata or {}).get("custom_id"),
            "category": (example.metadata or {}).get("category"),
        }
        for feedback in item["evaluation_results"].get("results", []):
            row[feedback.key] = feedback.score
        rows.append(row)

    aggregate = {}
    for key in metric_keys:
        scores = [row[key] for row in rows if row.get(key) is not None]
        if scores:
            aggregate[key] = sum(scores) / len(scores)
    return rows, aggregate


def _build_metric(key: str):
    """One metric with its own traced judge LLM on a fresh async client."""
    judge_client = wrap_openai(
        AsyncOpenAI(api_key=settings.openai_api_key, timeout=_REQUEST_TIMEOUT_SECONDS),
        chat_name="ragas_judge",
    )
    llm = _trace_judge(llm_factory(settings.openai_model, client=judge_client), key)
    if key == "faithfulness":
        return Faithfulness(llm=llm)
    if key == "answer_relevancy":
        embeddings = _trace_embeddings(
            OpenAIEmbeddings(client=judge_client, model="text-embedding-ada-002")
        )
        return AnswerRelevancy(llm=llm, embeddings=embeddings)
    if key == "context_precision":
        return ContextPrecision(llm=llm)
    if key == "context_recall":
        return ContextRecall(llm=llm)
    raise ValueError(f"unknown metric key: {key}")


def run() -> None:
    """Evaluate every example in settings.eval_dataset_name and write
    results.json as {"aggregate", "rows"} (the shape compare_runs.py reads).
    """
    evaluators = [_make_ragas_evaluator(key) for key in _METRIC_KEYS]
    results = evaluate(
        _target,
        data=settings.eval_dataset_name,
        evaluators=evaluators,
        max_concurrency=_MAX_CONCURRENCY,
        experiment_prefix=_EXPERIMENT_PREFIX,
        metadata={**retrieval_config_snapshot(), "judge_model": settings.openai_model},
    )

    rows, aggregate = _summarize(results, list(_METRIC_KEYS))

    failed = [r["custom_id"] for r in rows if any(r.get(k) is None for k in _METRIC_KEYS)]
    if failed:
        print(f"WARNING: {len(failed)} cases missing a metric score: {failed}")

    output = {"aggregate": aggregate, "rows": rows}
    _RESULTS_PATH.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {_RESULTS_PATH}")
    for key, value in aggregate.items():
        print(f"  {key:<20} {value:.3f}")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
