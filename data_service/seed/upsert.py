"""Shared upsert logic for turning TMDB movie detail payloads into ORM rows.

Used by both bulk_seed.py (initial enrichment) and daily_sync.py (freshness
refresh of already-tracked movies), so the mapping lives in one place.
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from data_service.models.catalog import Credit, Genre, Person, Title

_CAST_LIMIT = 20
_CREW_LIMIT = 15
# Deliberately narrow slice of the ~200+ distinct crew job titles TMDB
# returns per movie — director, cinematographer, writers, producer.
_CREW_JOB_WHITELIST = {
    "Director",
    "Director of Photography",
    "Writer",
    "Screenplay",
    "Story",
    "Producer",
}


def upsert_title(db: Session, payload: dict[str, Any]) -> Title:
    title = db.get(Title, payload["id"])
    if title is None:
        title = Title(id=payload["id"])
        db.add(title)

    title.title = payload.get("title") or payload.get("original_title") or ""
    title.original_title = payload.get("original_title")
    title.overview = payload.get("overview")
    title.release_date = _parse_date(payload.get("release_date"))
    title.runtime = payload.get("runtime")
    title.status = payload.get("status")
    title.popularity = payload.get("popularity")
    title.vote_average = payload.get("vote_average")
    title.vote_count = payload.get("vote_count")
    title.poster_path = payload.get("poster_path")
    title.backdrop_path = payload.get("backdrop_path")
    title.original_language = payload.get("original_language")
    title.adult = payload.get("adult", False)
    title.softcore = payload.get("softcore", False)

    collection = payload.get("belongs_to_collection")
    title.collection_id = collection["id"] if collection else None
    title.collection_name = collection["name"] if collection else None

    title.raw_json = payload
    title.last_synced_at = datetime.utcnow()

    _sync_title_genres(db, title, payload.get("genres", []))
    _sync_credits(db, title, payload.get("credits", {}))
    return title


def _sync_title_genres(db: Session, title: Title, genres: list[dict[str, Any]]) -> None:
    for g in genres:
        genre = db.get(Genre, g["id"])
        if genre is None:
            genre = Genre(id=g["id"], name=g["name"])
            db.add(genre)
        if genre not in title.genres:
            title.genres.append(genre)


def _sync_credits(db: Session, title: Title, credits_payload: dict[str, Any]) -> None:
    # Re-syncing a title replaces its credit rows outright rather than diffing,
    # since credits have no stable id of their own to diff against.
    db.query(Credit).filter(Credit.title_id == title.id).delete()

    cast = credits_payload.get("cast", [])[:_CAST_LIMIT]
    crew = credits_payload.get("crew", [])
    crew_credits = [c for c in crew if c.get("job") in _CREW_JOB_WHITELIST][:_CREW_LIMIT]

    # The same person can appear in both cast and crew (e.g. an actor who
    # also directed). Upsert each unique person exactly once *before*
    # creating any Credit rows — calling _upsert_person_stub twice for the
    # same id in one unflushed batch would try to INSERT that person twice
    # and violate the primary key, since neither add is visible to the
    # other's db.get() lookup until a flush happens.
    people_by_id: dict[int, dict[str, Any]] = {}
    for entry in (*cast, *crew_credits):
        people_by_id.setdefault(entry["id"], entry)
    person_by_id = {pid: _upsert_person_stub(db, payload) for pid, payload in people_by_id.items()}

    for c in cast:
        db.add(
            Credit(
                title_id=title.id,
                person_id=person_by_id[c["id"]].id,
                role="cast",
                character=c.get("character"),
                order=c.get("order"),
            )
        )
    for c in crew_credits:
        db.add(
            Credit(
                title_id=title.id,
                person_id=person_by_id[c["id"]].id,
                role="crew",
                job=c.get("job"),
            )
        )


def _upsert_person_stub(db: Session, payload: dict[str, Any]) -> Person:
    """Builds/refreshes a Person from the partial info embedded in a credits
    list entry (id, name, popularity, profile_path, known_for_department) —
    avoids an extra API call per credit just to seed a placeholder row."""
    person = db.get(Person, payload["id"])
    if person is None:
        person = Person(id=payload["id"], name=payload.get("name", ""))
        db.add(person)
    person.name = payload.get("name", person.name)
    person.known_for_department = payload.get("known_for_department")
    person.popularity = payload.get("popularity")
    person.profile_path = payload.get("profile_path")
    return person


def upsert_person_details(db: Session, payload: dict[str, Any]) -> Person:
    """Full enrichment from GET /person/{id} — used by daily_sync when a
    person id shows up in /person/changes."""
    person = db.get(Person, payload["id"])
    if person is None:
        person = Person(id=payload["id"], name=payload.get("name", ""))
        db.add(person)
    person.name = payload.get("name", person.name)
    person.known_for_department = payload.get("known_for_department")
    person.popularity = payload.get("popularity")
    person.profile_path = payload.get("profile_path")
    person.raw_json = payload
    person.last_synced_at = datetime.utcnow()
    return person


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None
