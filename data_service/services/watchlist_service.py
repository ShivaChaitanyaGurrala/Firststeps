from sqlalchemy.orm import Session

from data_service.models.catalog import Title
from data_service.models.user_data import WatchlistEntry
from data_service.schemas.user_data import WatchlistOut
from data_service.services.exceptions import TitleNotFoundError, WatchlistEntryNotFoundError


def list_watchlist(db: Session) -> list[WatchlistEntry]:
    return db.query(WatchlistEntry).order_by(WatchlistEntry.added_at.desc()).all()


def add_to_watchlist(db: Session, title_id: int, notes: str | None = None) -> WatchlistEntry:
    title = db.get(Title, title_id)
    if title is None:
        raise TitleNotFoundError(f"Title {title_id} not found")

    existing = db.query(WatchlistEntry).filter_by(title_id=title_id).one_or_none()
    if existing is not None:
        return existing

    entry = WatchlistEntry(title_id=title_id, notes=notes)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def remove_from_watchlist(db: Session, watchlist_id: int) -> None:
    entry = db.get(WatchlistEntry, watchlist_id)
    if entry is None:
        raise WatchlistEntryNotFoundError(f"Watchlist entry {watchlist_id} not found")
    db.delete(entry)
    db.commit()


def to_watchlist_out(entry: WatchlistEntry) -> WatchlistOut:
    return WatchlistOut(
        id=entry.id,
        title_id=entry.title_id,
        title=entry.title.title,
        added_at=entry.added_at,
        notes=entry.notes,
    )
