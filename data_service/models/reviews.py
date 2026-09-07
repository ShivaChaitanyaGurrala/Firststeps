from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data_service.models.base import Base, TimestampMixin
from data_service.models.catalog import Title


class Review(Base, TimestampMixin):
    """A user-written review for a movie, from GET /movie/{id}/reviews.

    Unlike every other TMDB entity in this project, review ids are NOT
    integers — TMDB assigns them opaque hex strings (Mongo ObjectId-style,
    e.g. "5488c29bc3a3686f4a00004a"), so `id` is a String primary key here,
    not the Integer/autoincrement=False pattern Title/Person/Credit use.

    No `embedded_at`/last-synced-style column here, deliberately: whether a
    review has been chunked+embedded is rag_service's concern, not
    data_service's — data_service doesn't touch Chroma at all (see the M4
    architecture note in rag_service/config.py). rag_service tracks its own
    ingestion state on its own side of that boundary.
    """

    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id"))
    author: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tmdb_created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    title: Mapped["Title"] = relationship()
