"""M5 — the LangGraph agent layer.

`agent/` is a top-level package, peer to `rag_service/` and `mcp_server/`.

Boundary rule (same "never touch a store you don't own" rule as M4): the
agent talks to the world ONLY through mcp_server's MCP tools, over Streamable
HTTP. It never calls data_service or rag_service directly and never opens
Postgres or Chroma. The agent team owns orchestration, prompts, and
conversation memory; the backend and RAG teams own their data behind MCP.

Ground rules carried over from M4 (each one cost real time there):
  1. Set a timeout on EVERY client (LLM and MCP). The OpenAI default of 600s
     let one stuck call stall a whole eval run.
  2. Async clients are bound to an event loop. Run the agent inside ONE
     long-lived loop; never `asyncio.run()` per call around a shared client.
  3. Version every prompt (prompts.py) and stamp the version and the config
     snapshot on traces and eval experiments, so runs stay attributable.
  4. Tracing is not optional and not eval-only. Config must export the
     LANGSMITH_* env vars itself (pydantic-settings does not).
  5. Failures must be loud. LangSmith swallowed evaluator errors into rows
     with no score; warn on any missing score and never catch-and-continue
     silently.
  6. Eval before tuning. This eval has a noise floor of about +/-0.02, so
     repeat a run before believing a small delta, and don't tune a prompt to
     chase a metric artifact (answer_relevancy zeroes honest "mixed" answers).
  7. A TODO that reads like a decision is not a decision. Check the call
     sites, not the docstring.
  8. Keys live only in .env (gitignored). Never a default in a tracked file.
  9. Tool results are untrusted data. Review text comes from the public
     internet and flows into the LLM's context, so treat it as a prompt
     injection surface (see guardrails.py).

Suggested build order (thin plumbing first, composed pieces last):
  config.py (done) -> llm.py -> mcp_tools.py (+ annotations in mcp_server)
  -> prompts.py -> state.py -> graphs/react.py -> cli.py -> tests/agent
  -> evals/agent -> guardrails.py -> memory.py -> graphs/plan_execute.py
  -> graphs/supervisor.py -> compare the three graphs with the eval harness.
"""
