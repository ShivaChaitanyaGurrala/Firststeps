"""Model routing: one place that turns a role ("cheap" or "strong") into a
configured chat model. Graphs ask for a role, never for a model name.

Why roles: M5's plan calls for a cheap model on search/routing steps and a
stronger one on recommendation reasoning. Keeping the mapping here means a
graph node says `get_llm("cheap")` and swapping a provider or model is a
.env change, not an edit across three graphs.
"""

from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel

Role = Literal["cheap", "strong"]


def get_llm(role: Role) -> BaseChatModel:
    """Return the chat model for `role`, built from config.settings.

    DECIDED: one model (gpt-6-luna) for both roles, via `langchain-openai`'s
    ChatOpenAI (already installed, 1.6.0 — supports the plain
    `reasoning_effort` kwarg directly, no need for the older
    `reasoning={"effort": ...}` dict form which needs >=1.4.1 anyway).
    Role is expressed as *reasoning effort*, not a different model:
      - cheap  -> settings.cheap_reasoning_effort  (default "low")
      - strong -> settings.strong_reasoning_effort (default "high")
    Chosen from Artificial Analysis's published numbers for this model: low
    is both cheaper AND scores higher than non-reasoning ($0.0045/task, index
    21, vs $0.01/task, index 18), so there's no reason to use non-reasoning.
    On the top end, high (index 32, $0.03) was picked over xhigh/max because
    cost accelerates faster than intelligence does above high ($0.04 for +2,
    then $0.07 for +3) — if evals/agent later show `high` isn't enough for a
    specific graph, bump strong_reasoning_effort, don't default to max.
    Still open: OpenAI direct vs an Azure OpenAI deployment for this model —
    both go through ChatOpenAI, Azure just adds `base_url`/a different
    api_key source. Decide when you have the actual account to use.

    CAUTION: "low"/"medium"/"high"/"xhigh" are LangChain's documented
    `reasoning_effort` values for OpenAI reasoning models generally. Verify
    gpt-6-luna accepts these exact strings (and what its top tier is
    literally called — "max" may be provider marketing for xhigh, or a real
    distinct value) against the actual API docs before trusting the .env
    defaults; this model is past my training data.

    Implement:
    1. Map role -> (settings.cheap_model or settings.strong_model,
       settings.cheap_reasoning_effort or settings.strong_reasoning_effort).
       Raise a clear error (not a silent default) if the model name is empty.
    2. ChatOpenAI(model=..., reasoning_effort=..., timeout=
       settings.llm_timeout_seconds, max_retries=settings.llm_max_retries,
       api_key=settings.llm_api_key or None).
    3. Cache per role (functools.lru_cache) so a graph doesn't rebuild the
       client each node. Bound clients belong to one event loop, see the
       package docstring's rule 2.
    4. Do NOT also set temperature: LangChain disables temperature/top_p/
       penalties automatically whenever reasoning_effort is active, so a
       temperature kwarg here would be silently ignored. The old "keep
       temperature low for routing" plan is moot for a reasoning model —
       effort is the comparability knob now; keep it fixed across runs the
       same way temperature would have been.
    """
    raise NotImplementedError
