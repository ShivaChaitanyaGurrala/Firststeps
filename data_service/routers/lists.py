from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from data_service.db import get_db
from data_service.schemas.user_data import ListCreate, ListDetailOut, ListItemCreate, ListOut
from data_service.services import lists_service

router = APIRouter(prefix="/lists", tags=["lists"])


@router.get("", response_model=list[ListOut])
def list_lists(db: Session = Depends(get_db)):
    return lists_service.list_lists(db)


@router.post("", response_model=ListOut, status_code=201)
def create_list(payload: ListCreate, db: Session = Depends(get_db)):
    return lists_service.create_list(db, payload.name, payload.description)


@router.get("/{list_id}", response_model=ListDetailOut)
def get_list(list_id: int, db: Session = Depends(get_db)) -> ListDetailOut:
    list_entity = lists_service.get_list(db, list_id)
    return lists_service.to_list_detail(list_entity)


@router.post("/{list_id}/items", response_model=ListDetailOut, status_code=201)
def add_list_item(
    list_id: int, payload: ListItemCreate, db: Session = Depends(get_db)
) -> ListDetailOut:
    list_entity = lists_service.add_list_item(db, list_id, payload.title_id)
    return lists_service.to_list_detail(list_entity)


@router.delete("/{list_id}/items/{title_id}", status_code=204)
def remove_list_item(list_id: int, title_id: int, db: Session = Depends(get_db)) -> None:
    lists_service.remove_list_item(db, list_id, title_id)
