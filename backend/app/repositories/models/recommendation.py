"""Recommendations and their allocation rows — append-only (recommendation_spec §3, NFR-02).

Every recommendation pins the template version it was computed from (AC-10.5 in-flight rule).
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import DecimalText
from app.domain.bands import RiskBand
from app.domain.policy import RecommendationSource
from app.repositories.base import Base
from app.repositories.guards import protect_append_only
from app.repositories.models._columns import new_uuid, utcnow


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    source: Mapped[RecommendationSource] = mapped_column(
        Enum(RecommendationSource, native_enum=False, length=16), nullable=False
    )
    risk_band: Mapped[RiskBand] = mapped_column(Enum(RiskBand, native_enum=False, length=16), nullable=False)
    risk_band_source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    template_version_id: Mapped[str] = mapped_column(ForeignKey("template_versions.id"), nullable=False)
    goal_id: Mapped[str | None] = mapped_column(ForeignKey("goals.id"), nullable=True)
    horizon_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    horizon_rule: Mapped[str] = mapped_column(String(20), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RecommendationAllocation(Base):
    __tablename__ = "recommendation_allocations"

    recommendation_id: Mapped[str] = mapped_column(ForeignKey("recommendations.id"), primary_key=True)
    asset_class_code: Mapped[str] = mapped_column(ForeignKey("asset_classes.code"), primary_key=True)
    target_pct: Mapped[Decimal] = mapped_column(DecimalText(2), nullable=False)


protect_append_only(Recommendation)
protect_append_only(RecommendationAllocation)
