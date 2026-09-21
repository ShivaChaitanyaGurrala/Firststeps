"""Diff two RAGAS results.json snapshots — the actual "did this tuning
change help?" tool. Tuning a RAG pipeline (chunk_size/chunk_overlap,
embedding_model, fetch_k, rerank_model/rerank_top_n — see config.py) is
inherently a before/after comparison: change one knob in .env, re-ingest,
re-run run_ragas_eval.py, then run this against the old and new
results.json to see the actual delta instead of eyeballing two JSON files.

Usage:
    # before changing anything:
    cp evals/rag/results.json evals/rag/results_baseline.json

    # change a knob in .env, e.g. CHUNK_SIZE=600, then:
    python -m data_service.seed... (n/a) — actually: re-run ingest + eval:
        python -m rag_service.ingest
        python -m evals.rag.run_ragas_eval

    # compare:
    python -m evals.rag.compare_runs evals/rag/results_baseline.json evals/rag/results.json
"""

import json
import sys
from pathlib import Path

_METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
_REGRESSION_THRESHOLD = 0.05  # a per-case drop bigger than this gets flagged


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text())


def compare(before_path: str, after_path: str) -> None:
    before = _load(before_path)
    after = _load(after_path)

    print(f"=== Aggregate: {before_path} -> {after_path} ===")
    for metric in _METRICS:
        b = before["aggregate"].get(metric)
        a = after["aggregate"].get(metric)
        if b is None or a is None:
            continue
        delta = a - b
        arrow = "up" if delta > 0.001 else "down" if delta < -0.001 else "="
        print(f"  {metric:<20} {b:.3f} -> {a:.3f}  ({delta:+.3f}, {arrow})")

    before_by_id = {row["custom_id"]: row for row in before["rows"]}
    after_by_id = {row["custom_id"]: row for row in after["rows"]}

    print("\n=== Per-case regressions (> "
          f"{_REGRESSION_THRESHOLD} drop on any metric) ===")
    regressions = 0
    for custom_id, after_row in after_by_id.items():
        before_row = before_by_id.get(custom_id)
        if before_row is None:
            continue
        drops = []
        for metric in _METRICS:
            b, a = before_row.get(metric), after_row.get(metric)
            if b is None or a is None:
                continue
            if b - a > _REGRESSION_THRESHOLD:
                drops.append(f"{metric} {b:.2f}->{a:.2f}")
        if drops:
            regressions += 1
            print(f"  {custom_id} ({after_row.get('category', '?')}): {', '.join(drops)}")
    if regressions == 0:
        print("  none")

    print("\n=== Per-case improvements (> "
          f"{_REGRESSION_THRESHOLD} gain on any metric) ===")
    improvements = 0
    for custom_id, after_row in after_by_id.items():
        before_row = before_by_id.get(custom_id)
        if before_row is None:
            continue
        gains = []
        for metric in _METRICS:
            b, a = before_row.get(metric), after_row.get(metric)
            if b is None or a is None:
                continue
            if a - b > _REGRESSION_THRESHOLD:
                gains.append(f"{metric} {b:.2f}->{a:.2f}")
        if gains:
            improvements += 1
            print(f"  {custom_id} ({after_row.get('category', '?')}): {', '.join(gains)}")
    if improvements == 0:
        print("  none")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m evals.rag.compare_runs <before_results.json> <after_results.json>")
        sys.exit(1)
    compare(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
