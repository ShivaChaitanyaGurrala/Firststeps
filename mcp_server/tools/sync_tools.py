"""Lifecycle-monitoring tools: check sync history, kick off a new sync.

Second in the M1 build order — mostly read-oriented (sync_status), and
exercises the M0 sync_runs audit log end-to-end through MCP.
"""

from server import mcp
from http_client import DataServiceClient

_client = DataServiceClient()


@mcp.tool()
def sync_status(run_id: int | None = None) -> dict:
    """Check the status of sync jobs (bulk_seed / daily_sync runs).

    Args:
        run_id: optional — if given, return just that one run; otherwise
            return the most recent runs.

    Returns:
        {"runs": [{"id", "run_type", "status", "started_at", "finished_at", "ids_upserted"}, ...]}
    """
    # TODO(you): call _client.list_sync_runs(run_id) and shape the response dict.
    raise NotImplementedError


@mcp.tool()
def trigger_sync(run_type: str) -> dict:
    """Kick off a bulk_seed or daily_sync job in the background.

    Args:
        run_type: "bulk_seed" or "daily_sync".

    Returns:
        {"run_id": <int>, "status": "started"}
    """
    # TODO(you): call _client.trigger_sync(run_type) and shape the response dict.
    raise NotImplementedError
