"""Customer goals (goal_tracker_spec §3). Read-only in Sprint 1 (seeded); CRUD arrives with AC-03."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import DecimalText
from app.domain.goal import GoalType
from app.repositories.base import Base
from app.repositories.models._columns import new_uuid, utcnow


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    goal_type: Mapped[GoalType] = mapped_column(Enum(GoalType, native_enum=False, length=16), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(DecimalText(2), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    funding_share_pct: Mapped[Decimal] = mapped_column(DecimalText(2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
