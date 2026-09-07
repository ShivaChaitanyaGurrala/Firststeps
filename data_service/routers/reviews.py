from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from data_service.db import get_db
from data_service.schemas.reviews import ReviewOut
from data_service.services import reviews_service

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewOut])
def list_reviews(
    title_id: int | None = None,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """title_id omitted lists across the whole catalog, paginated — this is
    the bulk-pull mode rag_service/ingest.py uses; title_id set scopes to
    one movie's reviews (e.g. for a "show reviews for this title" UI view)."""
    reviews = reviews_service.list_reviews(db, title_id=title_id, limit=limit, offset=offset)
    return [reviews_service.to_review_out(r) for r in reviews]
