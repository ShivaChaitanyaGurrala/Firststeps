"""RAGAS scoring harness for the M4 RAG pipeline — this milestone's
acceptance bar. Scores: faithfulness, answer_relevancy, context_precision,
context_recall against eval_set.json's fixed (question, ground_truth) pairs.

Decision this script does NOT make for you: RAGAS's metrics need an LLM in
two roles — (1) generating an answer from the retrieved context for each
question (there is no "answer" yet at this point in the pipeline — M4 only
built retrieval, not generation; that's a deliberately small, non-agentic
generation step just for this eval, distinct from M5's real LangGraph
agent), and (2) acting as the judge RAGAS itself uses internally to score
faithfulness/answer_relevancy (RAGAS defaults to an OpenAI model for this
unless you wrap a different one). Decide which LLM plays both roles before
writing this in — using Claude via ragas.llms.LangchainLLMWrapper wrapping
a langchain_anthropic ChatAnthropic instance is one reasonable option (also
keeps you off a second, third-party judge-model dependency), OpenAI is
RAGAS's zero-config default. Either way, whatever key that needs isn't yet
in data_service/config.py — decide where it belongs (a new setting there,
or just an env var this standalone script reads directly, given it's not
part of the FastAPI app).

pip install: ragas (+ its LLM-wrapper dependency, depends on which LLM you
pick above) — not yet in pyproject.toml.

Usage (once implemented):
    python -m evals.rag.run_ragas_eval
"""

import json
from pathlib import Path

_EVAL_SET_PATH = Path(__file__).parent / "eval_set.json"


def _load_eval_set() -> list[dict]:
    data = json.loads(_EVAL_SET_PATH.read_text())
    return data["cases"]


def _retrieve(question: str, title_id: int | None) -> list[str]:
    """Get the retrieved context strings for one question.

    TODO(you): call rag_service.retriever.search directly (in-process,
    since this script is standalone Python, not another service) OR hit the
    running rag_service's GET /search over HTTP, same call
    mcp_server/rag_client.py makes. Either is fine for a standalone eval
    script; pick whichever is less setup. Return just the chunk_text
    strings, in the order search returned them (RAGAS's context_precision
    metric is order-sensitive — it rewards relevant context ranked higher).
    """
    raise NotImplementedError


def _generate_answer(question: str, contexts: list[str]) -> str:
    """Ask an LLM to answer `question` using only `contexts` as grounding —
    the "small, non-agentic generation step" from this file's module
    docstring. A short prompt (system: answer using only the given context;
    user: context + question) is enough; this isn't the place for
    prompt-engineering depth, that's M5's job.

    TODO(you): call whichever LLM you picked in the module docstring.
    """
    raise NotImplementedError


def run() -> None:
    """TODO(you):
    1. cases = _load_eval_set()
    2. For each case: contexts = _retrieve(...), answer = _generate_answer(...)
    3. Assemble RAGAS's expected input shape — as of RAGAS's current API
       this is typically a HuggingFace `Dataset` (or their own dataset
       wrapper) with columns: question, contexts (list[str] per row),
       answer, ground_truth. Check RAGAS's current docs for the exact shape
       expected — this has changed across RAGAS versions.
    4. `from ragas import evaluate`
       `from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall`
       `result = evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_precision, context_recall], llm=<your wrapped judge LLM>)`
    5. Print the per-metric scores (result gives you both an aggregate and
       a per-row breakdown — the per-row view is far more useful for
       actually debugging which question the pipeline handles badly).
    """
    raise NotImplementedError


if __name__ == "__main__":
    run()
