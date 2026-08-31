"""Response contract validation — the M3 gap on top of error normalization
(see errors.py).

Every method in http_client.py currently does `return response.json()` and
hands the raw dict straight to a tool, with no check that data_service
actually sent back the shape a tool expects. If data_service's response
shape ever drifts (a renamed field, a dropped column, a type change)
nothing here catches it — a malformed dict silently reaches the tool layer
and either crashes somewhere unrelated to the real cause, or gets
serialized straight into a misleading tool result for the LLM.

data_service already defines the canonical shapes as Pydantic models in
data_service/schemas/*.py (TitleSummary, TitleDetail, WatchlistOut,
RatingOut, ListOut/ListDetailOut, PersonDetail, SyncRunOut,
SyncTriggerResponse). Mirror the ones http_client.py needs here rather than
importing data_service's models directly — the MCP server should depend on
data_service's HTTP *contract*, not its Python internals. Same "decouple
across the boundary" principle versioning.py argues for for tool/resource
*identity*, applied here to response *shape*.

Models (implemented): all of TitleSummary, TitleDetail, WatchlistOut,
RatingOut, ListOut/ListDetailOut, PersonDetail, SyncRunOut,
SyncTriggerResponse are defined below, mirroring data_service/schemas/*.py
field-for-field. Defined locally rather than imported from data_service —
see the decoupling note above.

TODO(you):
1. In http_client.py, replace each `return response.json()` with
   `return TitleSummary.model_validate(response.json())` (or
   `TypeAdapter(list[TitleSummary]).validate_python(response.json())` for
   the list-returning methods) using the matching model, and update that
   method's return type hint from `dict[str, Any]` / `list[dict[str, Any]]`
   to the real Pydantic type.
2. Decide what a validation failure should mean for a tool call. Letting
   pydantic.ValidationError propagate up into errors.py's normalization
   path (treat it as an UpstreamError — data_service sent something that
   doesn't match its own contract) is a reasonable default; don't swallow
   it silently.
"""

from datetime import date, datetime

from pydantic import BaseModel


class TitleSummary(BaseModel):
    id: int
    title: str
    release_date: date | None = None
    popularity: float | None = None
    vote_average: float | None = None


class GenreOut(BaseModel):
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


class TitleDetail(BaseModel):
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


class WatchlistOut(BaseModel):

    id: int
    title_id: int
    title: str
    added_at: datetime
    notes: str | None = None


class RatingOut(BaseModel):
    id: int
    title_id: int
    title: str
    score: int
    review: str | None = None
    rated_at: datetime


class ListOut(BaseModel):
    id: int
    name: str
    description: str | None = None


class ListItemOut(BaseModel):
    title_id: int
    title: str
    added_at: datetime


class ListDetailOut(ListOut):
    items: list[ListItemOut] = []


class PersonDetail(BaseModel):
    id: int
    name: str
    known_for_department: str | None = None
    popularity: float | None = None
    profile_path: str | None = None


class SyncRunOut(BaseModel):
    id: int
    run_type: str
    entity_type: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    ids_examined: int
    ids_upserted: int
    ids_failed: int
    error_summary: str | None = None


class SyncTriggerResponse(BaseModel):
    run_id: int
    status: str
