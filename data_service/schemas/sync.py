from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class SyncRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    run_type: str
    entity_type: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    ids_examined: int
    ids_upserted: int
    ids_failed: int
    error_summary: str | None = None


class SyncTriggerRequest(BaseModel):
    run_type: Literal["bulk_seed", "daily_sync"]


class SyncTriggerResponse(BaseModel):
    run_id: int
    status: str
