from sqlalchemy.orm import Session

from data_service.models.catalog import Title
from data_service.models.user_data import ListEntity, ListItem
from data_service.schemas.user_data import ListDetailOut, ListItemOut
from data_service.services.exceptions import (
    ListItemNotFoundError,
    ListNotFoundError,
    TitleNotFoundError,
)


def list_lists(db: Session) -> list[ListEntity]:
    return db.query(ListEntity).order_by(ListEntity.created_at.desc()).all()


def create_list(db: Session, name: str, description: str | None = None) -> ListEntity:
    list_entity = ListEntity(name=name, description=description)
    db.add(list_entity)
    db.commit()
    db.refresh(list_entity)
    return list_entity


def get_list(db: Session, list_id: int) -> ListEntity:
    list_entity = db.get(ListEntity, list_id)
    if list_entity is None:
        raise ListNotFoundError(f"List {list_id} not found")
    return list_entity


def add_list_item(db: Session, list_id: int, title_id: int) -> ListEntity:
    list_entity = get_list(db, list_id)
    title = db.get(Title, title_id)
    if title is None:
        raise TitleNotFoundError(f"Title {title_id} not found")

    existing = db.query(ListItem).filter_by(list_id=list_id, title_id=title_id).one_or_none()
    if existing is None:
        db.add(ListItem(list_id=list_id, title_id=title_id))
        db.commit()
        db.refresh(list_entity)

    return list_entity


def remove_list_item(db: Session, list_id: int, title_id: int) -> None:
    item = db.query(ListItem).filter_by(list_id=list_id, title_id=title_id).one_or_none()
    if item is None:
        raise ListItemNotFoundError(f"List item not found for list {list_id}, title {title_id}")
    db.delete(item)
    db.commit()


def to_list_detail(list_entity: ListEntity) -> ListDetailOut:
    return ListDetailOut(
        id=list_entity.id,
        name=list_entity.name,
        description=list_entity.description,
        items=[
            ListItemOut(title_id=i.title_id, title=i.title.title, added_at=i.added_at)
            for i in list_entity.items
        ],
    )
