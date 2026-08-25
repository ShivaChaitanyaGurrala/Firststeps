from sqlalchemy.orm import Session

from data_service.models.catalog import Title
from data_service.models.user_data import Rating
from data_service.services.exceptions import RatingNotFoundError, TitleNotFoundError


def list_ratings(db: Session) -> list[Rating]:
    return db.query(Rating).order_by(Rating.rated_at.desc()).all()


def rate_title(db: Session, title_id: int, score: int, review: str | None = None) -> Rating:
    title = db.get(Title, title_id)
    if title is None:
        raise TitleNotFoundError(f"Title {title_id} not found")

    rating = db.query(Rating).filter_by(title_id=title_id).one_or_none()
    if rating is None:
        rating = Rating(title_id=title_id, score=score, review=review)
        db.add(rating)
    else:
        rating.score = score
        rating.review = review
    db.commit()
    db.refresh(rating)
    return rating


def update_rating(
    db: Session, rating_id: int, *, score: int | None = None, review: str | None = None
) -> Rating:
    rating = db.get(Rating, rating_id)
    if rating is None:
        raise RatingNotFoundError(f"Rating {rating_id} not found")
    if score is not None:
        rating.score = score
    if review is not None:
        rating.review = review
    db.commit()
    db.refresh(rating)
    return rating


def delete_rating(db: Session, rating_id: int) -> None:
    rating = db.get(Rating, rating_id)
    if rating is None:
        raise RatingNotFoundError(f"Rating {rating_id} not found")
    db.delete(rating)
    db.commit()
