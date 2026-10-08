"""Advisor risk band overrides (advisor_workbench_spec §3, AC-09, NFR-02)."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.advisor_override_rules import OverrideReasonCode
from app.domain.bands import RiskBand
from app.repositories.base import Base
from app.repositories.guards import protect_append_only
from app.repositories.models._columns import new_uuid, utcnow


class RiskBandOverride(Base):
    __tablename__ = "risk_band_overrides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    previous_band: Mapped[RiskBand] = mapped_column(Enum(RiskBand, native_enum=False, length=16), nullable=False)
    new_band: Mapped[RiskBand] = mapped_column(Enum(RiskBand, native_enum=False, length=16), nullable=False)
    reason_code: Mapped[OverrideReasonCode] = mapped_column(
        Enum(OverrideReasonCode, native_enum=False, length=32), nullable=False
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(16), default="ADVISOR", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


protect_append_only(RiskBandOverride)
