from datetime import datetime

from sqlalchemy.orm import Session

from data_service.models.sync import SyncRun
from data_service.services.exceptions import SyncRunNotFoundError


def list_sync_runs(
    db: Session, *, run_type: str | None = None, status: str | None = None, limit: int = 20
) -> list[SyncRun]:
    query = db.query(SyncRun)
    if run_type:
        query = query.filter(SyncRun.run_type == run_type)
    if status:
        query = query.filter(SyncRun.status == status)
    return query.order_by(SyncRun.started_at.desc()).limit(limit).all()


def get_sync_run(db: Session, run_id: int) -> SyncRun:
    sync_run = db.get(SyncRun, run_id)
    if sync_run is None:
        raise SyncRunNotFoundError(f"Sync run {run_id} not found")
    return sync_run


def queue_sync_run(db: Session, run_type: str) -> SyncRun:
    """Creates a 'queued' SyncRun row synchronously — the router hands the
    actual work off to a background task keyed on this row's id, and that
    background job (bulk_seed.run / daily_sync.run) updates the row itself
    as it progresses."""
    entity_type = "movie" if run_type == "bulk_seed" else "movie+person"
    sync_run = SyncRun(
        run_type=run_type,
        entity_type=entity_type,
        started_at=datetime.utcnow(),
        status="queued",
    )
    db.add(sync_run)
    db.commit()
    db.refresh(sync_run)
    return sync_run
