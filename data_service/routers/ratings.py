from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from data_service.db import get_db
from data_service.schemas.user_data import RatingCreate, RatingOut, RatingUpdate
from data_service.services import ratings_service

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.get("", response_model=list[RatingOut])
def list_ratings(db: Session = Depends(get_db)):
    return [ratings_service.to_rating_out(r) for r in ratings_service.list_ratings(db)]


@router.post("", response_model=RatingOut, status_code=201)
def rate_title(payload: RatingCreate, db: Session = Depends(get_db)):
    rating = ratings_service.rate_title(db, payload.title_id, payload.score, payload.review)
    return ratings_service.to_rating_out(rating)


@router.put("/{rating_id}", response_model=RatingOut)
def update_rating(rating_id: int, payload: RatingUpdate, db: Session = Depends(get_db)):
    rating = ratings_service.update_rating(db, rating_id, score=payload.score, review=payload.review)
    return ratings_service.to_rating_out(rating)


@router.delete("/{rating_id}", status_code=204)
def delete_rating(rating_id: int, db: Session = Depends(get_db)) -> None:
    ratings_service.delete_rating(db, rating_id)
