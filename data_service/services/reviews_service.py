from sqlalchemy.orm import Session

from data_service.models.reviews import Review
from data_service.schemas.reviews import ReviewOut


def list_reviews(
    db: Session, *, title_id: int | None = None, limit: int = 20, offset: int = 0
) -> list[Review]:
    """title_id=None lists across every movie, paginated via limit/offset —
    this is the bulk-pull mode rag_service's ingest.py uses to walk the
    whole `reviews` table; title_id set is the single-movie mode
    routers/reviews.py's GET /reviews?title_id= uses."""
    query = db.query(Review)
    if title_id is not None:
        query = query.filter(Review.title_id == title_id)
    return (
        query.order_by(Review.id).offset(offset).limit(limit).all()
    )


def to_review_out(review: Review) -> ReviewOut:
    # Built field-by-field, not ReviewOut.model_validate(review) — Review.title
    # is the related Title ORM object (via the relationship), not the plain
    # string ReviewOut.title expects, so from_attributes alone can't bridge
    # them; same denormalization shape as watchlist_service/ratings_service.
    return ReviewOut(
        id=review.id,
        title_id=review.title_id,
        title=review.title.title,
        author=review.author,
        content=review.content,
        rating=review.rating,
        url=review.url,
        tmdb_created_at=review.tmdb_created_at,
    )
