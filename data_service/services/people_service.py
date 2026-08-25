from sqlalchemy.orm import Session

from data_service.models.catalog import Person
from data_service.services.exceptions import PersonNotFoundError


def list_people(
    db: Session, *, q: str | None = None, limit: int = 20, offset: int = 0
) -> list[Person]:
    query = db.query(Person)
    if q:
        query = query.filter(Person.name.ilike(f"%{q}%"))
    return query.order_by(Person.popularity.desc()).offset(offset).limit(limit).all()


def get_person(db: Session, person_id: int) -> Person:
    person = db.get(Person, person_id)
    if person is None:
        raise PersonNotFoundError(f"Person {person_id} not found")
    return person
