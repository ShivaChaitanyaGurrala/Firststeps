from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from data_service.db import get_db
from data_service.schemas.catalog import TitleDetail, TitleSummary
from data_service.services import titles_service

router = APIRouter(prefix="/titles", tags=["titles"])


@router.get("", response_model=list[TitleSummary])
def list_titles(
    genre: str | None = None,
    q: str | None = None,
    sort: str = Query(
        default="popularity", pattern="^(popularity|vote_average|release_date|title)$"
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return titles_service.list_titles(db, genre=genre, q=q, sort=sort, limit=limit, offset=offset)


@router.get("/{title_id}", response_model=TitleDetail)
def get_title(title_id: int, db: Session = Depends(get_db)) -> TitleDetail:
    title = titles_service.get_title(db, title_id)
    return titles_service.to_title_detail(title)
