"""Fetch TMDB reviews for locally-tracked movies and upsert them into the
`reviews` table — the unstructured-text corpus the M4 RAG pipeline chunks,
embeds, and retrieves over.

This is a sibling of bulk_seed.py/daily_sync.py, not a modification of
either: it doesn't touch `titles`, it doesn't call /movie/changes, and it
has no "freshness" concept — a review, once posted, doesn't change. Its
whole job is: for movies already in the catalog, pull whatever reviews
TMDB has and store them locally so rag/ingest.py has something to embed.

Usage:
    python -m data_service.seed.fetch_reviews [--limit N]
"""

import argparse
import asyncio
from datetime import datetime

from sqlalchemy import select

from data_service.db import SessionLocal
from data_service.models import Review, SyncRun, Title
from data_service.tmdb_client import TmdbClient

_CONCURRENCY = 10


def _movie_ids_to_fetch(limit: int | None) -> list[int]:
    """Locally-tracked movie ids, most popular first (mirrors bulk_seed's
    curation rule — popular movies are also the ones most likely to have
    real reviews worth embedding)."""
    db = SessionLocal()
    try:
        stmt = select(Title.id).order_by(Title.popularity.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(db.execute(stmt).scalars().all())
    finally:
        db.close()


async def _fetch_reviews_for_movie(
    client: TmdbClient, movie_id: int
) -> list[dict]:
    """All review objects for one movie, across every page."""
    results: list[dict] = []
    page = 1
    while True:
        resp = await client.get_movie_reviews(movie_id, page=page)
        results.extend(resp.get("results", []))
        total_pages = resp.get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1
    return results


def _upsert_review(db, movie_id: int, payload: dict) -> None:
    """Insert-or-update one Review row from a single TMDB review object."""
    review = db.get(Review, payload["id"])
    if review is None:
        review = Review(id=payload["id"], title_id=movie_id)
        db.add(review)

    review.title_id = movie_id
    review.author = payload.get("author", "")
    review.content = payload.get("content", "")

    author_details = payload.get("author_details") or {}
    review.rating = author_details.get("rating")

    review.url = payload.get("url")
    review.tmdb_created_at = _parse_datetime(payload.get("created_at"))
    review.raw_json = payload


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    # TMDB sends "2020-05-12T03:11:33.123Z" — fromisoformat wants "+00:00".
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def run(*, limit: int | None = None, run_id: int | None = None) -> None:
    """Top-level orchestration, mirroring daily_sync.py's run()."""
    db = SessionLocal()
    if run_id is None:
        sync_run = SyncRun(
            run_type="fetch_reviews",
            entity_type="review",
            started_at=datetime.utcnow(),
            status="running",
            params={"limit": limit},
        )
        db.add(sync_run)
        db.commit()
        db.refresh(sync_run)
        run_id = sync_run.id
    else:
        sync_run = db.get(SyncRun, run_id)
        sync_run.status = "running"
        sync_run.started_at = datetime.utcnow()
        sync_run.params = {"limit": limit}
        db.commit()
    db.close()

    movie_ids = _movie_ids_to_fetch(limit)
    print(f"Fetching reviews for {len(movie_ids)} movies...")

    semaphore = asyncio.Semaphore(_CONCURRENCY)
    errors: list[str] = []
    failed = 0

    async def _fetch(client: TmdbClient, movie_id: int) -> tuple[int, list[dict] | None, str | None]:
        async with semaphore:
            try:
                reviews = await _fetch_reviews_for_movie(client, movie_id)
                return movie_id, reviews, None
            except Exception as exc:  # noqa: BLE001 - collected as a failure, not raised
                return movie_id, None, repr(exc)

    client = TmdbClient()
    try:
        results = await asyncio.gather(*(_fetch(client, mid) for mid in movie_ids))
    finally:
        await client.aclose()

    upserted = 0
    db = SessionLocal()
    try:
        for movie_id, reviews, error in results:
            if error is not None or reviews is None:
                failed += 1
                if len(errors) < 10:
                    errors.append(f"{movie_id}: {error}")
                continue
            for payload in reviews:
                _upsert_review(db, movie_id, payload)
                upserted += 1
            # Flush after each movie in case the same review id ever repeats
            # across pages/movies (see upsert.py's matching comment).
            db.flush()
        db.commit()
    finally:
        db.close()

    print(f"  fetched: movies_examined={len(movie_ids)} reviews_upserted={upserted} failed={failed}")

    db = SessionLocal()
    sync_run = db.get(SyncRun, run_id)
    sync_run.finished_at = datetime.utcnow()
    sync_run.ids_examined = len(movie_ids)
    sync_run.ids_upserted = upserted
    sync_run.ids_failed = failed
    sync_run.status = "success" if failed == 0 else "partial"
    if errors:
        sync_run.error_summary = "; ".join(errors)
    db.commit()
    db.close()

    print(f"Done. examined={len(movie_ids)} upserted={upserted} failed={failed}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    asyncio.run(run(limit=args.limit))


if __name__ == "__main__":
    main()
