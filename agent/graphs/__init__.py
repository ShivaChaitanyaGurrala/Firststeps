"""The three agent architectures M5 compares on the SAME tools, prompt and
eval set, so the comparison is about structure, not about accidental setup
differences. Add a graph here once it exists and cli.py / evals pick it up.
"""

from collections.abc import Callable
from typing import Any

# name -> builder returning a compiled LangGraph graph
GRAPHS: dict[str, Callable[..., Any]] = {}
