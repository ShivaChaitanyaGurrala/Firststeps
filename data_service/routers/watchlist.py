from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from data_service.db import get_db
from data_service.schemas.user_data import WatchlistCreate, WatchlistOut
from data_service.services import watchlist_service

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistOut])
def list_watchlist(db: Session = Depends(get_db)) -> list[WatchlistOut]:
    entries = watchlist_service.list_watchlist(db)
    return [watchlist_service.to_watchlist_out(e) for e in entries]


@router.post("", response_model=WatchlistOut, status_code=201)
def add_to_watchlist(payload: WatchlistCreate, db: Session = Depends(get_db)) -> WatchlistOut:
    entry = watchlist_service.add_to_watchlist(db, payload.title_id, payload.notes)
    return watchlist_service.to_watchlist_out(entry)


@router.delete("/{watchlist_id}", status_code=204)
def remove_from_watchlist(watchlist_id: int, db: Session = Depends(get_db)) -> None:
    watchlist_service.remove_from_watchlist(db, watchlist_id)
