"""One-time (or after a model change) schema creation.

Deliberately NOT wired into app startup — booting the API shouldn't touch DDL
or require a live DB connection (that broke tests, which use their own
in-memory schema and should never need the real DATABASE_URL reachable).

Usage:
    python -m data_service.init_db
"""

from data_service.db import engine
from data_service.models import Base


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print(f"Tables created/verified against {engine.url}")


if __name__ == "__main__":
    main()
