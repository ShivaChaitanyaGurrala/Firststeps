from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WatchlistCreate(BaseModel):
    title_id: int
    notes: str | None = None


class WatchlistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title_id: int
    title: str
    added_at: datetime
    notes: str | None = None


class RatingCreate(BaseModel):
    title_id: int
    score: int = Field(ge=1, le=10)
    review: str | None = None


class RatingUpdate(BaseModel):
    score: int | None = Field(default=None, ge=1, le=10)
    review: str | None = None


class RatingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title_id: int
    title: str
    score: int
    review: str | None = None
    rated_at: datetime


class ListCreate(BaseModel):
    name: str
    description: str | None = None


class ListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None


class ListItemCreate(BaseModel):
    title_id: int


class ListItemOut(BaseModel):
    title_id: int
    title: str
    added_at: datetime


class ListDetailOut(ListOut):
    items: list[ListItemOut] = []
