"""Rebalancing recommendations and allocation lines (rebalancing_spec §3, AC-06, AC-07, NFR-02)."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import DecimalText
from app.repositories.base import Base
from app.repositories.guards import protect_append_only
from app.repositories.models._columns import new_uuid, utcnow

if TYPE_CHECKING:
    from app.repositories.models.rebalancing_decision import RebalancingDecision


class RebalancingRecommendation(Base):
    __tablename__ = "rebalancing_recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    based_on_recommendation_id: Mapped[str] = mapped_column(ForeignKey("recommendations.id"), nullable=False)
    template_version_id: Mapped[str] = mapped_column(ForeignKey("template_versions.id"), nullable=False)
    nav_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_value: Mapped[Decimal] = mapped_column(DecimalText(2), nullable=False)
    drift_threshold_pct: Mapped[Decimal] = mapped_column(DecimalText(2), nullable=False)
    post_trade_cash: Mapped[Decimal] = mapped_column(DecimalText(2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    lines: Mapped[list["RebalancingLine"]] = relationship(
        "RebalancingLine", back_populates="recommendation", cascade="all, delete-orphan"
    )
    decision: Mapped["RebalancingDecision | None"] = relationship(
        "RebalancingDecision", back_populates="recommendation", uselist=False
    )


class RebalancingLine(Base):
    __tablename__ = "rebalancing_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    rebalancing_recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("rebalancing_recommendations.id"), index=True, nullable=False
    )
    asset_class_code: Mapped[str] = mapped_column(ForeignKey("asset_classes.code"), nullable=False)
    current_value: Mapped[Decimal] = mapped_column(DecimalText(2), nullable=False)
    current_pct: Mapped[Decimal | None] = mapped_column(DecimalText(2), nullable=True)
    target_pct: Mapped[Decimal | None] = mapped_column(DecimalText(2), nullable=True)
    drift_pct: Mapped[Decimal | None] = mapped_column(DecimalText(2), nullable=True)
    target_value: Mapped[Decimal | None] = mapped_column(DecimalText(2), nullable=True)
    nav: Mapped[Decimal] = mapped_column(DecimalText(4), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)  # BUY | SELL | NONE | SETTLEMENT
    quantity: Mapped[Decimal | None] = mapped_column(DecimalText(4), nullable=True)
    trade_value: Mapped[Decimal | None] = mapped_column(DecimalText(2), nullable=True)

    recommendation: Mapped[RebalancingRecommendation] = relationship(
        "RebalancingRecommendation", back_populates="lines"
    )


protect_append_only(RebalancingRecommendation)
protect_append_only(RebalancingLine)
