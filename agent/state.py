"""Graph state and the validated final output.

State is the contract between graph nodes, the same way response models were
M3's contract with data_service. Keep it small and explicit.
"""

from langgraph.graph import MessagesState
from pydantic import BaseModel


class AgentState(MessagesState):
    """`messages` (with the add_messages reducer) comes from MessagesState.

    TODO(you): add only the fields a graph really needs, and note which
    graph uses each:
      - plan_execute needs a `plan: list[str]` and the index of the current
        step.
      - supervisor needs which worker was chosen (`next_worker`).
      - react needs nothing beyond `messages`.
    Prefer per-graph state subclasses over one big shared dict.
    """


class FinalAnswer(BaseModel):
    """The structured, validated result the agent returns to a caller (the
    M6 UI will render it).

    TODO(you): define the fields. Suggestions to argue for or against:
      - `answer: str`
      - `titles: list[...]` the movies the answer is about (title id + name)
      - `sources`: review ids or tool names the answer relied on, so the UI
        and evals can show where a claim came from
      - `confidence` or `needs_clarification: bool`
    Then wire it up with the model's structured output
    (`llm.with_structured_output(FinalAnswer)`) at the last node, and decide
    what happens when validation fails (retry once, then a plain-text
    fallback, never a crash).
    """
