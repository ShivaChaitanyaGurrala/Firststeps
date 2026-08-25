from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from data_service.db import get_db
from data_service.schemas.catalog import PersonDetail, PersonSummary
from data_service.services import people_service

router = APIRouter(prefix="/people", tags=["people"])


@router.get("", response_model=list[PersonSummary])
def list_people(
    q: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return people_service.list_people(db, q=q, limit=limit, offset=offset)


@router.get("/{person_id}", response_model=PersonDetail)
def get_person(person_id: int, db: Session = Depends(get_db)):
    return people_service.get_person(db, person_id)
