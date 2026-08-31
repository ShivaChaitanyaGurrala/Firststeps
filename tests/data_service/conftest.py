import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from data_service.config import settings
from data_service.db import get_db
from data_service.main import app
from data_service.models import Base, Title

# Separate database, same Postgres server as the real app — created once via
# `docker exec ... psql -U tmdb_app -d tmdb_local -c "CREATE DATABASE tmdb_local_test;"`
TEST_DATABASE_URL = settings.database_url.rsplit("/", 1)[0] + "/tmdb_local_test"


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(test_engine):
    """Runs each test inside an outer transaction that's rolled back at the
    end. Routers call db.commit() freely, which would normally end the outer
    transaction early — so we restart a SAVEPOINT every time a transaction
    ends, keeping the whole test isolated in one rollback-able unit."""
    connection = test_engine.connect()
    outer_transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, transaction):
        if transaction.nested and not transaction._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """data_service.main's rate limiter is a module-level singleton shared
    across the whole test session (not per-test) — without resetting it,
    request counts accumulate across unrelated tests within the same
    sliding window and can trip a spurious 429 on a test that isn't even
    about rate limiting. Autouse so every test starts with a clean budget.
    """
    from data_service.main import _rate_limiter

    _rate_limiter._requests.clear()
    yield


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_title(db_session) -> Title:
    title = Title(
        id=27205,
        title="Inception",
        overview="A thief who steals corporate secrets through dream-sharing technology.",
        popularity=123.4,
        vote_average=8.4,
        vote_count=35000,
        adult=False,
    )
    db_session.add(title)
    db_session.commit()
    db_session.refresh(title)
    return title
