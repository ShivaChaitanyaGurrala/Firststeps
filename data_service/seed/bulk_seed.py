"""Initial catalog seed: download the daily TMDB movie ID export file, curate
a manageable subset by popularity, and enrich each via the details endpoint.

Movies only — see Title/Genre model docstrings for why TV was dropped.

Usage:
    python -m data_service.seed.bulk_seed --movies 1500
"""

import argparse
import asyncio
from datetime import datetime

from data_service.db import SessionLocal
from data_service.models import SyncRun
from data_service.seed.curation import curate_top_n
from data_service.seed.upsert import upsert_title
from data_service.tmdb_client import TmdbClient

_CONCURRENCY = 15


async def _enrich_ids(client: TmdbClient, ids: list[int]) -> tuple[int, int, list[str]]:
    """Fetches details for each id with bounded concurrency, upserting as
    results complete. Returns (upserted_count, failed_count, error_samples)."""
    semaphore = asyncio.Semaphore(_CONCURRENCY)
    upserted = 0
    failed = 0
    errors: list[str] = []

    async def _fetch(movie_id: int) -> tuple[int, dict | None, str | None]:
        async with semaphore:
            try:
                payload = await client.get_movie_details(movie_id)
                return movie_id, payload, None
            except Exception as exc:  # noqa: BLE001 - collected as a failure, not raised
                # repr(), not str() — httpx connection-level exceptions
                # (timeouts, pool errors) often stringify to an empty
                # message, which makes the sync_runs audit trail useless.
                return movie_id, None, repr(exc)

    results = await asyncio.gather(*(_fetch(mid) for mid in ids))

    db = SessionLocal()
    try:
        for movie_id, payload, error in results:
            if error is not None or payload is None:
                failed += 1
                if len(errors) < 10:
                    errors.append(f"{movie_id}: {error}")
                continue
            upsert_title(db, payload)
            # Flush (not commit) after each title so shared Genre/Person rows
            # referenced by a LATER title in this same batch are already
            # persistent by the time db.get() looks them up — without this,
            # two titles sharing a cast member both try to INSERT that
            # person and the second one violates the primary key.
            db.flush()
            upserted += 1
        db.commit()
    finally:
        db.close()

    return upserted, failed, errors


async def run(movies_n: int, *, run_id: int | None = None) -> None:
    """If run_id is given (API-triggered path), reuses that already-created
    SyncRun row instead of creating a new one (CLI path creates its own)."""
    db = SessionLocal()
    if run_id is None:
        sync_run = SyncRun(
            run_type="bulk_seed",
            entity_type="movie",
            started_at=datetime.utcnow(),
            status="running",
            params={"movies_n": movies_n},
        )
        db.add(sync_run)
        db.commit()
        db.refresh(sync_run)
        run_id = sync_run.id
    else:
        sync_run = db.get(SyncRun, run_id)
        sync_run.status = "running"
        sync_run.started_at = datetime.utcnow()
        sync_run.params = {"movies_n": movies_n}
        db.commit()
    db.close()

    total_examined = 0
    total_upserted = 0
    total_failed = 0
    all_errors: list[str] = []

    client = TmdbClient()
    try:
        try:
            print("Downloading daily movie export...")
            export_rows = [row async for row in client.download_daily_export("movie")]
            print(f"  {len(export_rows)} ids in export")

            curated_ids = curate_top_n(export_rows, movies_n)
            total_examined = len(curated_ids)
            print(f"  curated top {len(curated_ids)} by popularity, enriching...")

            total_upserted, total_failed, all_errors = await _enrich_ids(client, curated_ids)
            print(f"  upserted={total_upserted} failed={total_failed}")
        except Exception as exc:
            # Unexpected (non-per-item) failure: still close out the audit
            # row as "failed" rather than leaving it stuck at "running"
            # forever — the sync_runs log is the lifecycle-monitoring
            # surface, so it needs to reflect reality even on a crash.
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
    parser = argparse.ArgumentParser(description="Bulk-seed the local TMDB movie catalog.")
    parser.add_argument("--movies", type=int, default=1500, help="Number of top movies to seed")
    args = parser.parse_args()
    asyncio.run(run(args.movies))


if __name__ == "__main__":
    main()
