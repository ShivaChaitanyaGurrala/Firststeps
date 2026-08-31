"""Inbound throttling defense — protects data_service's own endpoints from
being overwhelmed by its own callers (today: the MCP server; eventually,
M7: multiple independent tenants at once).

This is the opposite direction from tmdb_client.py's retry/backoff, which
is about data_service being a well-behaved *client* toward TMDB.

Implemented as a sliding window: each key (currently the caller's IP —
there's no per-tenant identity until M7) tracks the timestamps of its
recent requests; a request is allowed only if fewer than `max_requests`
timestamps fall within the last `window_seconds`. Chosen over a token
bucket for this project because it's simpler to reason about and to test
(no separate refill-rate concept to get right) — the point here is
learning the mechanism, not tuning production thresholds for a solo-user
lab.

Wired into data_service/main.py as an `@app.middleware("http")` function.

Note: `slowapi` (a FastAPI port of Flask-Limiter, built on the `limits`
package) wraps this exact pattern as a ready-made middleware/dependency if
you'd rather use a library than hand-roll the counter in a real project —
hand-rolling here is deliberate, for the learning value.
"""

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds
        timestamps = self._requests[key]

        while timestamps and timestamps[0] < window_start:
            timestamps.popleft()

        if len(timestamps) >= self.max_requests:
            return False

        timestamps.append(now)
        return True
