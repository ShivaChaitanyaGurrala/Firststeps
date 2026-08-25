"""Incremental sync: ask TMDB's /changes endpoints which ids changed since the
last successful run, and refresh only those that already exist locally.

Deliberately does NOT expand the tracked catalog — freshness only. Growing
the curated set is a separate concern (re-run bulk_seed with a larger N).

Usage:
    python -m data_service.seed.daily_sync
"""

import asyncio
from datetime import date, datetime, timedelta

from sqlalchemy import select

from data_service.db import SessionLocal
from data_service.models import Person, SyncRun, Title
from data_service.seed.upsert import upsert_person_details, upsert_title
from data_service.tmdb_client import TmdbClient

_CONCURRENCY = 15
_MAX_WINDOW_DAYS = 14  # TMDB /changes caps the start/end date span at 14 days


def _date_windows(start: date, end: date):
    cur = start
    while cur <= end:
        window_end = min(cur + timedelta(days=_MAX_WINDOW_DAYS - 1), end)
        yield cur, window_end
        cur = window_end + timedelta(days=1)


async def _collect_changed_ids(
    client: TmdbClient, entity_type: str, start: date, end: date
) -> set[int]:
    changed: set[int] = set()
    for window_start, window_end in _date_windows(start, end):
        page = 1
        while True:
            resp = await client.get_changes(entity_type, window_start, window_end, page=page)
            changed.update(r["id"] for r in resp.get("results", []))
            total_pages = resp.get("total_pages", 1)
            if page >= total_pages:
                break
            page += 1
    return changed


async def _refresh_ids(
    client: TmdbClient, entity_type: str, ids: list[int]
) -> tuple[int, int, list[str]]:
    semaphore = asyncio.Semaphore(_CONCURRENCY)
    upserted = 0
    failed = 0
    errors: list[str] = []

    async def _fetch(entity_id: int) -> tuple[int, dict | None, str | None]:
        async with semaphore:
            try:
                if entity_type == "movie":
                    payload = await client.get_movie_details(entity_id)
                else:
                    payload = await client.get_person_details(entity_id)
                return entity_id, payload, None
            except Exception as exc:  # noqa: BLE001 - collected as a failure, not raised
                # repr(), not str() — see the matching comment in bulk_seed.py.
                return entity_id, None, repr(exc)

    results = await asyncio.gather(*(_fetch(i) for i in ids))

    db = SessionLocal()
    try:
        for entity_id, payload, error in results:
            if error is not None or payload is None:
                failed += 1
                if len(errors) < 10:
                    errors.append(f"{entity_id}: {error}")
                continue
            if entity_type == "movie":
                upsert_title(db, payload)
            else:
                upsert_person_details(db, payload)
            # Flush so shared Genre/Person rows referenced by a later entity
            # in this batch are already persistent when db.get() looks them
            # up (see the matching comment in bulk_seed.py for why).
            db.flush()
            upserted += 1
        db.commit()
    finally:
        db.close()

    return upserted, failed, errors


def _last_sync_start_date() -> date:
    db = SessionLocal()
    try:
        last = db.execute(
            select(SyncRun)
            .where(SyncRun.run_type == "daily_sync", SyncRun.status == "success")
            .order_by(SyncRun.finished_at.desc())
            .limit(1)
        ).scalar_one_or_none()
    finally:
        db.close()
    if last is None or last.finished_at is None:
        return date.today() - timedelta(days=1)
    return last.finished_at.date()


def _locally_tracked_ids(entity_type: str, changed_ids: set[int]) -> list[int]:
    if not changed_ids:
        return []
    db = SessionLocal()
    try:
        if entity_type == "movie":
            rows = db.execute(
                select(Title.id).where(Title.id.in_(changed_ids))
            ).scalars().all()
        else:
            rows = db.execute(
                select(Person.id).where(Person.id.in_(changed_ids))
            ).scalars().all()
    finally:
        db.close()
    return list(rows)


async def run(*, run_id: int | None = None) -> None:
    """If run_id is given (API-triggered path), reuses that already-created
    SyncRun row instead of creating a new one (CLI path creates its own)."""
    start_date = _last_sync_start_date()
    end_date = date.today()
    params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}

    db = SessionLocal()
    if run_id is None:
        sync_run = SyncRun(
            run_type="daily_sync",
            entity_type="movie+person",
            started_at=datetime.utcnow(),
            status="running",
            params=params,
        )
        db.add(sync_run)
        db.commit()
        db.refresh(sync_run)
        run_id = sync_run.id
    else:
        sync_run = db.get(SyncRun, run_id)
        sync_run.status = "running"
        sync_run.started_at = datetime.utcnow()
        sync_run.params = params
        db.commit()
    db.close()

    total_examined = 0
    total_upserted = 0
    total_failed = 0
    all_errors: list[str] = []

    client = TmdbClient()
    try:
        try:
            for entity_type in ("movie", "person"):
                print(f"Checking /{entity_type}/changes from {start_date} to {end_date}...")
                changed_ids = await _collect_changed_ids(
                    client, entity_type, start_date, end_date
                )
                tracked_ids = _locally_tracked_ids(entity_type, changed_ids)
                total_examined += len(tracked_ids)
                print(
                    f"  {len(changed_ids)} changed upstream, "
                    f"{len(tracked_ids)} tracked locally, refreshing..."
                )

                upserted, failed, errors = await _refresh_ids(client, entity_type, tracked_ids)
                total_upserted += upserted
                total_failed += failed
                all_errors.extend(errors)
                print(f"  {entity_type}: upserted={upserted} failed={failed}")
        except Exception as exc:
            # Unexpected (non-per-item) failure: still close out the audit
            # row as "failed" rather than leaving it stuck at "running".
            db = SessionLocal()
            sync_run = db.get(SyncRun, run_id)
            sync_run.finished_at = datetime.utcnow()
            sync_run.ids_examined = total_examined
            sync_run.ids_upserted = total_upserted
            sync_run.ids_failed = total_failed
            sync_run.status = "failed"
            sync_run.error_summary = str(exc)
            db.commit()
            db.close()
            raise
    finally:
        await client.aclose()

    db = SessionLocal()
    sync_run = db.get(SyncRun, run_id)
    sync_run.finished_at = datetime.utcnow()
    sync_run.ids_examined = total_examined
    sync_run.ids_upserted = total_upserted
    sync_run.ids_failed = total_failed
    sync_run.status = "success" if total_failed == 0 else "partial"
    if all_errors:
        sync_run.error_summary = "; ".join(all_errors)
    db.commit()
    db.close()

    print(f"Done. examined={total_examined} upserted={total_upserted} failed={total_failed}")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
