from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from data_service.models.base import Base, TimestampMixin


class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"
    __table_args__ = (UniqueConstraint("title_id", name="uq_watchlist_title"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id"))
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    title: Mapped["Title"] = relationship()  # noqa: F821


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("title_id", name="uq_rating_title"),
        CheckConstraint("score >= 1 AND score <= 10", name="ck_rating_score_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id"))
    score: Mapped[int] = mapped_column(Integer)
    review: Mapped[str | None] = mapped_column(Text, nullable=True)
    rated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    title: Mapped["Title"] = relationship()  # noqa: F821


class ListEntity(Base, TimestampMixin):
    __tablename__ = "list_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list["ListItem"]] = relationship(back_populates="list_entity")


class ListItem(Base):
    __tablename__ = "list_items"
    __table_args__ = (UniqueConstraint("list_id", "title_id", name="uq_list_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("list_entities.id"))
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id"))
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    list_entity: Mapped["ListEntity"] = relationship(back_populates="items")
    title: Mapped["Title"] = relationship()  # noqa: F821
