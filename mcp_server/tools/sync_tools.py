"""Lifecycle-monitoring tools: check sync history, kick off a new sync.

Second in the M1 build order — mostly read-oriented (sync_status), and
exercises the M0 sync_runs audit log end-to-end through MCP.
"""

from typing import Annotated, Literal, cast

from pydantic import Field
from typing_extensions import TypedDict

from mcp_instance import mcp
from http_client import DataServiceClient

_client = DataServiceClient()


class SyncRunOut(TypedDict):
    id: int
    run_type: str
    entity_type: str
    status: str
    started_at: str | None
    finished_at: str | None
    ids_examined: int | None
    ids_upserted: int | None
    ids_failed: int | None
    error_summary: str | None


class SyncStatusResult(TypedDict):
    runs: list[SyncRunOut]


@mcp.tool()
def sync_status(
    run_id: Annotated[
        int | None, Field(default=None, description="The ID of the sync run to check.")
    ] = None,
) -> SyncStatusResult:
    """Check the status of sync jobs (bulk_seed / daily_sync runs)"""
    response = _client.list_sync_runs(run_id)
    runs = response if isinstance(response, list) else [response]
    return {"runs": cast(list[SyncRunOut], runs)}


class TriggerSyncResult(TypedDict):
    run_id: int
    status: str


@mcp.tool()
def trigger_sync(
    run_type: Annotated[
        Literal["bulk_seed", "daily_sync"],
        Field(
            description="The type of sync to trigger (bulk_seed or daily_sync).",
        ),
    ],
) -> TriggerSyncResult:
    """Kick off a bulk_seed or daily_sync job in the background."""
    response = _client.trigger_sync(run_type)
    return cast(TriggerSyncResult, response)
