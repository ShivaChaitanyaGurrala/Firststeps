from pydantic import BaseModel


class ReviewSearchHit(BaseModel):
    review_id: str
    title_id: int
    title: str
    chunk_text: str
    author: str
    rating: float | None = None
    score: float


class ReviewSearchResponse(BaseModel):
    query: str
    results: list[ReviewSearchHit]
