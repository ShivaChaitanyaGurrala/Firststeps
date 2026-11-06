"""Short-term (conversation) and long-term (persisted preferences) memory.

Ownership decision, made here to avoid repeating M4's boundary mistake: the
agent OWNS conversation state and learned preferences (its own store, in its
own storage). It does not write them into data_service's Postgres, and it
does not open that database. Real domain records (ratings, watchlist, lists)
stay in data_service and are reached through MCP tools. If you later think a
preference belongs in data_service, that is a new MCP tool owned by the
backend side, not a shortcut around it.
"""

from typing import Any


def get_checkpointer() -> Any:
    """Short-term memory: per-conversation state, keyed by a `thread_id`.

    TODO(you):
    1. Start with `InMemorySaver` (`langgraph.checkpoint.memory`). It resets
       on restart, which is fine while building.
    2. Then make it survive restarts. `langgraph.checkpoint.sqlite` is NOT
       installed (add `langgraph-checkpoint-sqlite` if you choose SQLite).
       Decide SQLite vs Postgres on a real reason and note it here.
    3. Pass it to `graph.compile(checkpointer=...)` in each graph. Human
       approval in guardrails.py depends on this.
    4. Decide when a long conversation gets trimmed or summarised so the
       context doesn't grow without bound (LangChain's `trim_messages`).
    """
    raise NotImplementedError


def get_store() -> Any:
    """Long-term memory: facts that outlive a conversation, such as "prefers
    sci-fi, dislikes horror", scoped per user.

    TODO(you):
    1. Start with `InMemoryStore` (`langgraph.store.memory`) and a namespace
       like ("preferences", user_id).
    2. Decide WHAT gets written and WHEN (an explicit "remember that..." from
       the user, or extracted automatically at the end of a turn?). Automatic
       extraction can store wrong things, so consider showing what was saved.
    3. Decide how memories reach the prompt (retrieved at the start of a turn
       and added to the system message).
    4. Privacy: this is personal data. Note what is stored and how to delete
       it (the M8 security milestone will ask).
    """
    raise NotImplementedError
