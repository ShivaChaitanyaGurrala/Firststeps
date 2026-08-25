from datetime import date

from pydantic import BaseModel, ConfigDict


class GenreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class CastMemberOut(BaseModel):
    person_id: int
    name: str
    character: str | None = None
    order: int | None = None


class CrewMemberOut(BaseModel):
    person_id: int
    name: str
    job: str | None = None


class TitleSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    release_date: date | None = None
    popularity: float | None = None
    vote_average: float | None = None


class TitleDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    overview: str | None = None
    release_date: date | None = None
    runtime: int | None = None
    status: str | None = None
    vote_average: float | None = None
    vote_count: int | None = None
    adult: bool = False
    softcore: bool = False
    collection_id: int | None = None
    collection_name: str | None = None
    genres: list[GenreOut] = []
    cast: list[CastMemberOut] = []
    crew: list[CrewMemberOut] = []


class PersonSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    known_for_department: str | None = None
    popularity: float | None = None


class PersonDetail(PersonSummary):
    profile_path: str | None = None
