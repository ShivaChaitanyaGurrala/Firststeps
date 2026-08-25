from sqlalchemy.orm import Session

from data_service.models.catalog import Genre, Title
from data_service.schemas.catalog import CastMemberOut, CrewMemberOut, GenreOut, TitleDetail
from data_service.services.exceptions import TitleNotFoundError


def list_titles(
    db: Session,
    *,
    genre: str | None = None,
    q: str | None = None,
    sort: str = "popularity",
    limit: int = 20,
    offset: int = 0,
) -> list[Title]:
    query = db.query(Title)
    if genre:
        query = query.join(Title.genres).filter(Genre.name.ilike(genre))
    if q:
        query = query.filter(Title.title.ilike(f"%{q}%"))

    sort_column = getattr(Title, sort)
    query = query.order_by(sort_column.desc() if sort != "title" else sort_column.asc())

    return query.offset(offset).limit(limit).all()


def get_title(db: Session, title_id: int) -> Title:
    title = db.get(Title, title_id)
    if title is None:
        raise TitleNotFoundError(f"Title {title_id} not found")
    return title


def to_title_detail(title: Title) -> TitleDetail:
    cast = sorted(
        (c for c in title.credits if c.role == "cast"),
        key=lambda c: c.order if c.order is not None else 999,
    )
    crew = [c for c in title.credits if c.role == "crew"]
    return TitleDetail(
        id=title.id,
        title=title.title,
        overview=title.overview,
        release_date=title.release_date,
        runtime=title.runtime,
        status=title.status,
        vote_average=title.vote_average,
        vote_count=title.vote_count,
        adult=title.adult,
        softcore=title.softcore,
        collection_id=title.collection_id,
        collection_name=title.collection_name,
        genres=[GenreOut(id=g.id, name=g.name) for g in title.genres],
        cast=[
            CastMemberOut(
                person_id=c.person_id, name=c.person.name, character=c.character, order=c.order
            )
            for c in cast[:10]
        ],
        crew=[CrewMemberOut(person_id=c.person_id, name=c.person.name, job=c.job) for c in crew],
    )
