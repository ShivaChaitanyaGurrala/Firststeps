"""Evaluation harness for the M5 agent. Same shape as evals/rag/run_ragas_eval.py
so the pattern (and its hard-won lessons) carries over: a LangSmith Dataset,
`langsmith.evaluate()` running the agent once per case, one named experiment
per run, results snapshotted to a JSON file, and evals/rag's compare and plot
scripts adapted to diff runs.

Build this alongside the agent, not after it. Without it you can't tell
whether a prompt or graph change helped (M4's noise floor was about +/-0.02).

Usage (once implemented):
    python -m evals.agent.run_agent_eval --graph react
"""

# TODO(you): imports you will need: langsmith (evaluate, traceable), agent
# (GRAPHS, mcp_tools, config), and ragas.metrics.collections (see below).


def _target(inputs: dict) -> dict:
    """Run ONE eval case through the agent graph and return what evaluators
    need.

    TODO(you): signature stays (inputs: dict) -> dict for langsmith.evaluate.
    1. Run the graph on inputs["question"] with a fresh thread_id per case.
    2. Return {"answer": ..., "tool_calls": [{"name":..., "args":...}, ...],
       "asked_for_approval": bool}. The tool calls come from the graph's
       messages, not from the model's prose.
    3. Auto-DENY every approval interrupt here (record that one was raised).
       An eval must never really change watchlist or rating data.
    4. Every client needs a timeout, and load tools/clients once, reusing one
       event loop (package docstring rules 1 and 2). M4 hung at case 54/55
       from breaking rule 2.
    5. If the target fails, return a marked error output so evaluators score
       None, and print a WARNING listing cases with missing scores. Never let
       a failure look like a score of 0.
    """
    raise NotImplementedError


# TODO(you): evaluators, cheapest and most reliable first. Signature is
# (inputs, outputs, reference_outputs) -> dict, same as evals/rag.
#   1. tool_selection: were the expected tools called and the forbidden ones
#      not? Deterministic, no LLM judge, so it has no judge noise. Start here.
#   2. approval_before_mutation: a mutating call happened only after an
#      approval interrupt. This is a safety property, so aim for 100%.
#   3. injection_resisted: for kind == "injection", no forbidden tool ran.
#   4. answer_faithfulness: for opinion answers, reuse ragas Faithfulness
#      against the search_reviews results the agent actually saw.
#   5. Optional: ragas.metrics.collections also ships ToolCallAccuracy,
#      ToolCallF1 and AgentGoalAccuracy. Try them, but compare against your
#      deterministic evaluators before trusting them.
# Don't tune prompts to chase answer_relevancy (M4's prompt-v2 lesson).


def run() -> None:
    """Sync the dataset (adapt evals/rag/sync_dataset.py), run
    langsmith.evaluate with an experiment_prefix that names the graph and
    prompt version, stamp agent_config_snapshot() into the experiment
    metadata, and write results_<name>.json.

    TODO(you): repeat the same configuration at least twice before comparing
    two graphs, so you know the noise floor for this eval.
    """
    raise NotImplementedError


if __name__ == "__main__":
    run()
