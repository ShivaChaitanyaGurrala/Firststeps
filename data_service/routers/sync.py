from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from data_service.db import get_db
from data_service.schemas.sync import SyncRunOut, SyncTriggerRequest, SyncTriggerResponse
from data_service.seed import bulk_seed, daily_sync
from data_service.services import sync_service

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/runs", response_model=list[SyncRunOut])
def list_sync_runs(
    run_type: str | None = None,
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return sync_service.list_sync_runs(db, run_type=run_type, status=status, limit=limit)


@router.get("/runs/{run_id}", response_model=SyncRunOut)
def get_sync_run(run_id: int, db: Session = Depends(get_db)):
    return sync_service.get_sync_run(db, run_id)


@router.post("/trigger", response_model=SyncTriggerResponse, status_code=202)
def trigger_sync(
    payload: SyncTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> SyncTriggerResponse:
    """Queues the SyncRun row via the service, then hands the actual work off
    to a background task — deciding *which* task to run is an HTTP-request
    concern (BackgroundTasks is FastAPI-specific), so it stays here rather
    than in the service."""
    sync_run = sync_service.queue_sync_run(db, payload.run_type)

    if payload.run_type == "bulk_seed":
        background_tasks.add_task(bulk_seed.run, 1500, run_id=sync_run.id)
    else:
        background_tasks.add_task(daily_sync.run, run_id=sync_run.id)

    return SyncTriggerResponse(run_id=sync_run.id, status="queued")
