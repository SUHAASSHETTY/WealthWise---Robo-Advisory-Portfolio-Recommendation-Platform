"""Goal progress snapshots — append-only (goal_tracker_spec §3, NFR-02)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import DecimalText
from app.repositories.base import Base
from app.repositories.guards import protect_append_only
from app.repositories.models._columns import new_uuid, utcnow


class GoalProgressSnapshot(Base):
    __tablename__ = "goal_progress_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id"), index=True, nullable=False)
    nav_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_value: Mapped[Decimal] = mapped_column(DecimalText(2), nullable=False)
    funding_share_pct: Mapped[Decimal] = mapped_column(DecimalText(2), nullable=False)
    current_goal_value: Mapped[Decimal] = mapped_column(DecimalText(2), nullable=False)
    percent_complete: Mapped[Decimal] = mapped_column(DecimalText(2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


protect_append_only(GoalProgressSnapshot)
