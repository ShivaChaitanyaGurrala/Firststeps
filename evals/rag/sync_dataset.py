"""One-time/idempotent sync: upload eval_set.json's cases into a LangSmith
Dataset, so run_ragas_eval.py's langsmith.evaluate() call has a real
Dataset to run against.

Why this file needs to exist at all: langsmith.evaluate()'s `data=`
parameter takes a Dataset name/id (or an iterable of langsmith.schemas.
Example objects already tied to one) - it does NOT accept a plain list of
raw dicts the way the old ragas/HuggingFace Dataset.from_list() approach
did. eval_set.json stays the source of truth (still hand-edited, still
what eval_set_fixes/etc. touch) - this script just mirrors it into
LangSmith on demand, it's not meant to be the place you edit case content.

Run whenever eval_set.json changes:
    python -m evals.rag.sync_dataset
"""

import json
import uuid
from pathlib import Path

from langsmith import Client

import rag_service.config  # pylint: disable=unused-import  # side effect: exports LANGSMITH_* from .env
from evals.rag.config import settings

_EVAL_SET_PATH = Path(__file__).parent / "eval_set.json"

# Deterministic namespace for deriving each example's LangSmith id from its
# custom_id - arbitrary but fixed, so uuid5(...) is stable across runs.
_ID_NAMESPACE = uuid.UUID("f0e1d2c3-b4a5-4678-9abc-def012345678")


def _load_eval_set() -> list[dict]:
    data = json.loads(_EVAL_SET_PATH.read_text())
    return data["cases"]


def sync() -> None:
    """Mirror every eval_set.json case into the LangSmith Dataset. Example ids
    are derived from custom_id; ids already in the dataset are updated in
    place, new ones are created (create_examples alone 409s on existing ids,
    and upsert_examples_multipart is deprecated)."""
    client = Client()
    cases = _load_eval_set()
    if not client.has_dataset(dataset_name=settings.eval_dataset_name):
        client.create_dataset(
            settings.eval_dataset_name,
            description="TMDB review RAG eval set, mirrors eval_set.json",
        )

    examples = []
    for i, case in enumerate(cases):
        custom_id = case.get("custom_id", f"case_{i:03d}")
        examples.append(
            {
                "id": uuid.uuid5(_ID_NAMESPACE, custom_id),
                "inputs": {
                    "question": case["question"],
                    "title_id": case.get("title_id"),
                },
                "outputs": {"ground_truth": case["ground_truth"]},
                "metadata": {"category": case["category"], "custom_id": custom_id},
            }
        )
    existing_ids = {
        ex.id for ex in client.list_examples(dataset_name=settings.eval_dataset_name)
    }
    to_update = [ex for ex in examples if ex["id"] in existing_ids]
    to_create = [ex for ex in examples if ex["id"] not in existing_ids]
    if to_update:
        client.update_examples(dataset_name=settings.eval_dataset_name, updates=to_update)
    if to_create:
        client.create_examples(dataset_name=settings.eval_dataset_name, examples=to_create)
    print(
        f"Synced {len(examples)} examples to '{settings.eval_dataset_name}' "
        f"({len(to_update)} updated, {len(to_create)} created)"
    )


def main() -> None:
    sync()


if __name__ == "__main__":
    main()
