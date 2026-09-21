"""Retrieval-stage diagnostic for the M4 RAG pipeline. For eval cases that
scored low in results.json, finds WHICH stage lost each gold review:
not ingested at all, missed by Chroma's similarity search (embedding model
or chunking), or demoted below top_n by Cohere's reranker. Each points at
a different knob; aggregate RAGAS scores alone can't tell them apart.

Usage:
    python -m evals.rag.diagnose_retrieval
"""

import json
import time
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document

from evals.rag.config import settings
from rag_service.config import settings as rag_settings
from rag_service.reranker import RerankedHit, rerank
from rag_service.retriever import _DEFAULT_FETCH_K  # keep in sync with retriever.py
from rag_service.vector_store import existing_review_ids, get_vector_store

_EVAL_SET_PATH = Path(__file__).parent / "eval_set.json"
_RESULTS_PATH = Path(__file__).parent / "results.json"


@dataclass
class SourceReviewDiagnosis:
    review_id: str
    ingested: bool
    in_raw_candidates: bool
    raw_rank: int | None  # 0-indexed position among the fetch_k candidates, if found
    survives_rerank: bool
    rerank_score: float | None
    verdict: str  # "not_ingested" | "embedding_miss" | "reranker_demoted" | "retrieved_ok"


def _load_eval_set() -> dict[str, dict]:
    data = json.loads(_EVAL_SET_PATH.read_text(encoding="utf-8"))
    return {f"case_{i:03d}": case for i, case in enumerate(data["cases"])}


def _load_failing_custom_ids() -> set[str]:
    """custom_ids from results.json whose context_recall or context_precision
    is below that metric's mean across the run."""
    data = json.loads(_RESULTS_PATH.read_text(encoding="utf-8"))
    recall_mean = data["aggregate"]["context_recall"]
    precision_mean = data["aggregate"]["context_precision"]
    failing = set()
    for row in data["rows"]:
        recall = row.get("context_recall")
        precision = row.get("context_precision")
        if (recall is not None and recall < recall_mean) or (
            precision is not None and precision < precision_mean
        ):
            failing.add(row["custom_id"])
    return failing


@lru_cache(maxsize=None)
def _rank_case(
    question: str, title_id: int | None
) -> tuple[tuple[Document, ...], tuple[RerankedHit, ...]]:
    """Chroma's fetch_k candidates and Cohere's full ranking of them for one
    question. Cached so a case with several source reviews costs one Chroma
    query and one Cohere call; sleeps after the Cohere call to respect the
    trial key's 10 req/min limit."""
    store = get_vector_store()
    candidates = store.similarity_search(
        question,
        k=_DEFAULT_FETCH_K,
        filter={"title_id": title_id} if title_id else None,  # type: ignore
    )
    hits = rerank(question, [c.page_content for c in candidates], top_n=len(candidates))
    time.sleep(settings.cohere_wait_seconds)
    return tuple(candidates), tuple(hits)


def diagnose_source_review(
    review_id: str,
    question: str,
    title_id: int | None,
    all_ingested_ids: set[str],
) -> SourceReviewDiagnosis:
    """Trace one gold review_id through ingestion, Chroma search and Cohere
    rerank for one eval question, stopping at the first stage that explains
    the miss. Fields for stages never reached stay at their defaults."""
    if review_id not in all_ingested_ids:
        return SourceReviewDiagnosis(review_id, False, False, None, False, None, "not_ingested")

    candidates, hits = _rank_case(question, title_id)
    matching = [
        i for i, doc in enumerate(candidates) if doc.metadata.get("review_id") == review_id
    ]
    if not matching:
        return SourceReviewDiagnosis(review_id, True, False, None, False, None, "embedding_miss")

    ranked = [(rank, hit) for rank, hit in enumerate(hits) if hit.index in matching]
    best_rank, best_hit = ranked[0]
    survives = best_rank < rag_settings.rerank_top_n
    return SourceReviewDiagnosis(
        review_id,
        True,
        True,
        min(matching),
        survives,
        best_hit.relevance_score,
        "retrieved_ok" if survives else "reranker_demoted",
    )


def diagnose_case(case: dict, all_ingested_ids: set[str]) -> list[SourceReviewDiagnosis]:
    """Run diagnose_source_review for every source_review_ids entry in one
    eval_set.json case. A case can fail because just ONE of its 2-4 source
    reviews didn't make it through even if the others did fine — report all
    of them, don't stop at the first failure.
    """
    return [
        diagnose_source_review(review_id, case["question"], case.get("title_id"), all_ingested_ids)
        for review_id in case.get("source_review_ids", [])
    ]


def check_chunk_boundary(review_id: str, needle: str) -> bool:
    """Is `needle` (a phrase that should be retrievable) fully inside one
    stored chunk of this review, or split across a chunk boundary? A split
    idea is represented by neither chunk's embedding, and only
    chunk_size/chunk_overlap can fix it. Not part of main()'s report; call
    it by hand for a specific phrase."""
    store = get_vector_store()
    result = store.get(where={"review_id": review_id})
    chunks = result["documents"] or []
    if any(needle.lower() in chunk.lower() for chunk in chunks):
        return True

    half = len(needle) // 2
    halves = (needle[:half].lower(), needle[half:].lower())
    for chunk in chunks:
        if any(part in chunk.lower() for part in halves):
            print(f"--- chunk holding part of the phrase ---\n{chunk}")
    return False


def main() -> None:
    failing_ids = _load_failing_custom_ids()
    eval_set = _load_eval_set()
    all_ingested_ids = existing_review_ids(get_vector_store())

    tally: Counter[str] = Counter()
    for custom_id in sorted(failing_ids):
        case = eval_set[custom_id]
        print(f"{custom_id} ({case['category']}): {case['question']}")
        for diagnosis in diagnose_case(case, all_ingested_ids):
            tally[diagnosis.verdict] += 1
            print(f"  {diagnosis.review_id}  {diagnosis.verdict}")

    print(f"\n=== Verdicts across {len(failing_ids)} failing cases ===")
    for verdict, count in tally.most_common():
        print(f"  {count:>3}  {verdict}")


if __name__ == "__main__":
    main()
