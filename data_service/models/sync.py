from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from data_service.models.base import Base


class SyncRun(Base):
    """Audit log for bulk-seed and daily-sync jobs — the lifecycle-monitoring surface."""

    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_type: Mapped[str] = mapped_column(String(20))  # "bulk_seed" | "daily_sync"
    entity_type: Mapped[str] = mapped_column(String(20))  # "movie" | "person" | "movie+person"
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    ids_examined: Mapped[int] = mapped_column(Integer, default=0)
    ids_upserted: Mapped[int] = mapped_column(Integer, default=0)
    ids_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
