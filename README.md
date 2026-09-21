# TMDB MCP & Agentic Learning Lab

A hands-on lab for learning MCP protocol fundamentals, wrapping REST APIs as MCP
tools, retrieval-augmented generation, and (eventually) agent architecture —
built as one real running system on top of [TMDB](https://developer.themoviedb.org)
(The Movie Database) rather than toy examples. The project itself isn't the
point; the point is becoming able to build and lead agentic/MCP projects from
scratch.

Three services, one shared `pyproject.toml`:

| Service | Role | Port |
|---|---|---|
| `data_service` | FastAPI + Postgres — TMDB catalog (titles, people, credits, reviews), watchlist/ratings/lists, bulk seed + daily incremental sync | `8000` |
| `rag_service` | FastAPI — chunking, embeddings, ChromaDB vector store, Cohere reranking, `/search` over real review text | `8020` |
| `mcp_server` | MCP server (official Python MCP SDK) exposing both of the above as tools/resources/prompts | stdio by default, or `8010` over Streamable HTTP |

## Milestone status

| # | Milestone | Status |
|---|---|---|
| M0 | Foundation — DB models, bulk seed, daily sync, FastAPI CRUD | ✅ Done |
| M1 | MCP Server v1 — stdio transport, 11 catalog/watchlist/rating/list/sync tools | ✅ Done |
| M2 | Streamable HTTP transport, Resources, Prompts, Sampling, schema versioning | ✅ Done |
| M3 | API-wrapping robustness — pagination, backoff, idempotency, error normalization, response contract validation, inbound throttling | ✅ Done |
| M4 | RAG subsystem — ChromaDB + Voyage embeddings + Cohere reranker, `search_reviews` MCP tool, RAGAS eval harness | ✅ Done |
| M5 | LangGraph agent layer | ⏳ Next |
| M6–M11 | UI, multi-tenant, security, infra/devops, testing/evals, alternatives lab | Planned |

## Setup

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/), Docker.

1. Install dependencies:
   ```
   uv sync
   ```
2. Copy `.env.example` to `.env` and fill in real values — TMDB v4 bearer
   token, Postgres credentials, Voyage AI + Cohere keys (for `rag_service`),
   and OpenAI key (for the RAGAS eval harness only — see `evals/rag/`).
3. Start Postgres and Chroma:
   ```
   docker run -d --name tmdb-postgres -p 5432:5432 \
     -e POSTGRES_USER=tmdb_app -e POSTGRES_PASSWORD=tmdb_local_dev_pw -e POSTGRES_DB=tmdb_local \
     postgres:16
   docker run -d --name tmdb-chroma -p 8001:8000 chromadb/chroma
   ```
4. Initialize the schema and seed data:
   ```
   uv run python -m data_service.init_db
   uv run python -m data_service.seed.bulk_seed --movies 1500 --tv 500
   uv run python -m data_service.seed.fetch_reviews
   ```
5. Ingest reviews into the vector store:
   ```
   uv run python -m rag_service.ingest
   ```

## Running the services

```
uv run uvicorn data_service.main:app --port 8000
uv run uvicorn rag_service.main:app --port 8020
cd mcp_server && uv run mcp dev server.py     # MCP Inspector, stdio
```

Set `MCP_TRANSPORT=streamable-http` in `.env` to run `mcp_server` as an HTTP
server on port `8010` instead.

## MCP surface

**13 tools** — `search_titles`, `get_title_details`, `get_recommendations`,
`add_to_watchlist`, `remove_from_watchlist`, `list_watchlist`, `rate_title`,
`create_list`, `add_to_list`, `sync_status`, `trigger_sync`,
`generate_watchlist_blurb` (sampling), and `search_reviews` (M4 — semantic
search over real review text, distinct from `search_titles`'s structured
lookup).

**3 resources** (`tmdb://title/{id}`, `tmdb://person/{id}`, watchlist) and
**2 prompts** (`summarize_watchlist`, `recommend_for_mood`).

## Evals

`evals/rag/` is M4's acceptance bar and the tuning loop for the RAG pipeline:
55 hand-written `(question, ground_truth)` cases in `eval_set.json`, each
grounded in real fetched reviews. Scored with RAGAS (faithfulness, answer
relevancy, context precision, context recall) on the modern
`ragas.metrics.collections` API, with `gpt-4o-mini` as both answer generator
(temperature 0, so runs are comparable) and judge.

| Script | Role |
|---|---|
| `sync_dataset.py` | Mirrors `eval_set.json` into a LangSmith Dataset (idempotent: updates existing cases, creates new ones). Re-run whenever the eval set changes. |
| `run_ragas_eval.py` | `langsmith.evaluate()` harness: retrieve, generate, score per case with bounded concurrency. Each run is a named LangSmith experiment; scores also written to `results.json`. |
| `diagnose_retrieval.py` | For below-average cases, finds which stage lost each gold review: `not_ingested`, `embedding_miss` (Chroma), `reranker_demoted` (Cohere) or `retrieved_ok`. Tells you which knob to turn. |
| `compare_runs.py` | Diffs two `results.json` snapshots: aggregate deltas plus per-case regressions and improvements. |
| `plot_experiments.py` | Charts every `results_<name>.json` snapshot: writes `experiments.svg` (README chart) and `experiments.html` (interactive: trends, per-case before/after scatter with question on hover, per-category bars; open it in a browser). |

```
uv run python -m evals.rag.sync_dataset
uv run python -m evals.rag.run_ragas_eval
uv run python -m evals.rag.diagnose_retrieval
uv run python -m evals.rag.compare_runs evals/rag/results_baseline-02.json evals/rag/results_rerank-top8.json
uv run python -m evals.rag.plot_experiments
```

Traces land in LangSmith with a run type per stage (`chain`, `retriever`,
`tool`, `prompt`, `llm`, `embedding`), so each module can be filtered on its
own. Experiments live under Datasets & Experiments, then `tmdb-rag-eval-set`,
then the Experiments tab. They are not in the plain Tracing Projects list.

### Experiments

Tuning loop: change one knob in `.env`, set `_EXPERIMENT_PREFIX` in
`run_ragas_eval.py` to name the run, re-run, snapshot `results.json` as
`results_<name>.json` (`results.json` itself is gitignored), then diff with
`compare_runs.py` and re-run `plot_experiments.py`. Change one thing per
experiment so each delta has one cause.

| Experiment | What changed | Faithfulness | Answer relevancy | Context precision | Context recall |
|---|---|---|---|---|---|
| `previous` (old harness) | Legacy RAGAS `single_turn_score`, generation at default temperature 1.0. **Not comparable** to the rows below | 0.746 | 0.688 | 0.752 | 0.674 |
| `baseline-02` | New harness (modern RAGAS API, temp 0, `langsmith.evaluate`), `RERANK_TOP_N=5`, `FETCH_K=20`, chunks 400/100, `voyage-4-lite`, `rerank-v3.5` | 0.823 | 0.850 | 0.796 | 0.718 |
| `rerank-top8` | `RERANK_TOP_N` 5 to 8, nothing else | 0.888 | 0.916 | 0.764 | **0.850** |
| Change, baseline-02 to rerank-top8 | | +0.065 | +0.066 | -0.032 | **+0.132** |

![RAGAS metrics across experiments](evals/rag/experiments.svg)

**Why `RERANK_TOP_N` was the first knob.** `diagnose_retrieval.py` on the 37
below-average `baseline-02` cases (76 gold reviews) gave 47 `retrieved_ok`, 27
`reranker_demoted`, 2 `embedding_miss` and 0 `not_ingested`. Cohere found most
of the missing gold reviews but ranked them below position 5, and 23 cases lost
at least one this way. Ingestion and embedding were not the bottleneck, so the
reranker cutoff was.

**What `rerank-top8` did.** Context recall improved on 17 cases and dropped on
1. Precision dropped on 12 cases and rose on 7, the expected cost of handing
the model about 8 chunks instead of 5. Faithfulness and answer relevancy rose
because the answer now has the evidence it needs. Context recall by question
category, `baseline-02` to `rerank-top8`:

| Category (cases) | Recall before | Recall after |
|---|---|---|
| agreement (18) | 0.66 | 0.80 |
| disagreement (17) | 0.70 | 0.82 |
| comparison (12) | 0.76 | 0.89 |
| element_critique (4) | 0.83 | 0.92 |
| ending_analysis (2) | 0.67 | 1.00 |
| catalog_wide (2) | 1.00 | 1.00 |

Verdict: for this corpus, 8 beats 5. Recall gains 0.13 for 0.03 of precision.
The next experiments to try are `RERANK_TOP_N` 6-7 (a better precision/recall
tradeoff), then `FETCH_K` (2 cases were true embedding misses).

**Caveats.** One run per configuration, 55 cases, and an LLM judge, so small
per-case moves are noise; the `ending_analysis` and `catalog_wide` categories
have only 2 cases each. Some `answer_relevancy` scores are exactly 0.00 in one
run and not the other for the same case (`case_005`, `case_007`, `case_011`),
so treat that metric's changes as approximate. Six cases (`case_003`, `004`,
`008`, `011`, `021`, `028`) have broadened ground truth flagged with
`_ground_truth_note`; their `source_review_ids` still need backfilling.

### Harness notes

- `results.json` holds `{"aggregate", "rows"}`; every row is tagged with its
  question `category` and `custom_id`, ready for a future UI.
- Each evaluator call builds its own async OpenAI client and runs under a hard
  240-second timeout. Reusing one client across the fresh event loops that
  `asyncio.run` creates is the suspected cause of runs hanging at 54/55.
  Unconfirmed on a full clean run.
- Cohere's trial key allows 10 calls/min, so `rerank()` retries 429s with
  backoff and concurrency is capped at 2.
- OpenAI's Batch API was tried for answer generation and removed: it can't
  nest under a LangSmith trace and made tuning runs slow to re-run.

## Testing

```
uv run pytest
```

Unit/integration tests per service (`tests/data_service/`, `tests/mcp_server/`,
`tests/rag_service/`) — isolated Postgres transactions (rolled back per test),
mocked TMDB/Cohere/Chroma calls, no real network access required.
