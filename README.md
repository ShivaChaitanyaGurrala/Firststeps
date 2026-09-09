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

`evals/rag/run_ragas_eval.py` is M4's acceptance bar: 55 hand-written
`(question, ground_truth)` cases in `evals/rag/eval_set.json`, each grounded
in 1-3 real fetched reviews. For each case it retrieves context via
`rag_service`, generates an answer through an OpenAI Batch API job (a
deliberately minimal, non-agentic generation step — M5's real agent is the
first real generation layer), then scores the full pipeline with RAGAS:

```
uv run python -m evals.rag.run_ragas_eval
```

Results (aggregate + all 55 per-row scores, tagged by question `category` for
failure-mode breakdown) are written to `evals/rag/results.json`, not stdout —
built for a future UI to visualize rather than eyeballing a terminal dump.

Latest run:

| Metric | Score |
|---|---|
| Faithfulness | 0.734 |
| Answer relevancy | 0.723 |
| Context precision | 0.731 |
| Context recall | 0.691 |

## Testing

```
uv run pytest
```

Unit/integration tests per service (`tests/data_service/`, `tests/mcp_server/`,
`tests/rag_service/`) — isolated Postgres transactions (rolled back per test),
mocked TMDB/Cohere/Chroma calls, no real network access required.
