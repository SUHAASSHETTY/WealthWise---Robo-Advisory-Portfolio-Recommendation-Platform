"""Risk assessments — append-only (risk_profile_spec §3, NFR-02)."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.bands import RiskBand
from app.repositories.base import Base
from app.repositories.guards import protect_append_only
from app.repositories.models._columns import new_uuid, utcnow

_BAND = Enum(RiskBand, native_enum=False, length=16)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    risk_policy_version_id: Mapped[str] = mapped_column(ForeignKey("risk_policy_versions.id"), nullable=False)
    answers: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_band: Mapped[RiskBand] = mapped_column(_BAND, nullable=False)
    assigned_band: Mapped[RiskBand] = mapped_column(_BAND, nullable=False)
    applied_caps: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


protect_append_only(RiskAssessment)
