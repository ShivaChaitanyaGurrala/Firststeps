from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data_service.models.base import Base, TimestampMixin


class Title(Base, TimestampMixin):
    """A movie. Project is scoped to movies only (no TV) — this removed the
    ambiguity around genre id reuse across media types and a TMDB data gap
    where TV runtime data isn't reliably available via episode_run_time."""

    __tablename__ = "titles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    title: Mapped[str] = mapped_column(String(500))
    original_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    runtime: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    popularity: Mapped[float | None] = mapped_column(Float, nullable=True)
    vote_average: Mapped[float | None] = mapped_column(Float, nullable=True)
    vote_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    backdrop_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    adult: Mapped[bool] = mapped_column(Boolean, default=False)
    softcore: Mapped[bool] = mapped_column(Boolean, default=False)
    collection_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    collection_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    genres: Mapped[list["Genre"]] = relationship(
        secondary="title_genres", back_populates="titles"
    )
    credits: Mapped[list["Credit"]] = relationship(back_populates="title")


class Genre(Base):
    """TMDB genre ids are global (e.g. Drama=18 means the same thing for
    every title), so there's no per-media-type ambiguity to model here."""

    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(100))

    titles: Mapped[list["Title"]] = relationship(
        secondary="title_genres", back_populates="genres"
    )


class TitleGenre(Base):
    __tablename__ = "title_genres"

    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id"), primary_key=True)
    genre_id: Mapped[int] = mapped_column(ForeignKey("genres.id"), primary_key=True)


class Person(Base, TimestampMixin):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(255))
    known_for_department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    popularity: Mapped[float | None] = mapped_column(Float, nullable=True)
    profile_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Credit(Base):
    __tablename__ = "credits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id"))
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"))
    role: Mapped[str] = mapped_column(String(10))  # "cast" | "crew"
    character: Mapped[str | None] = mapped_column(Text, nullable=True)
    # crew job, e.g. "Director", "Director of Photography", "Writer",
    # "Screenplay", "Story", "Producer" — see _CREW_JOB_WHITELIST in upsert.py
    job: Mapped[str | None] = mapped_column(String(100), nullable=True)
    order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    title: Mapped["Title"] = relationship(back_populates="credits")
    person: Mapped["Person"] = relationship()
