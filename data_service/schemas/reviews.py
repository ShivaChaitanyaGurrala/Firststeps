from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReviewOut(BaseModel):
    """`title` is denormalized here the same way WatchlistOut/RatingOut
    denormalize it (see services/reviews_service.to_review_out) — this is
    the shape rag_service pulls in bulk to build Chroma's denormalized
    chunk metadata, so it needs the title name without a second round trip
    back to GET /titles/{id}."""

    model_config = ConfigDict(from_attributes=True)
    id: str
    title_id: int
    title: str
    author: str
    content: str
    rating: float | None = None
    url: str | None = None
    tmdb_created_at: datetime | None = None
