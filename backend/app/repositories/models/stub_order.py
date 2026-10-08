"""Stub orders created upon accepting a rebalance proposal (rebalancing_spec §3, AC-07, NFR-02)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import DecimalText
from app.repositories.base import Base
from app.repositories.guards import protect_append_only
from app.repositories.models._columns import new_uuid, utcnow


class StubOrder(Base):
    __tablename__ = "stub_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    rebalancing_recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("rebalancing_recommendations.id"), index=True, nullable=False
    )
    asset_class_code: Mapped[str] = mapped_column(ForeignKey("asset_classes.code"), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)  # BUY | SELL
    quantity: Mapped[Decimal] = mapped_column(DecimalText(4), nullable=False)
    nav: Mapped[Decimal] = mapped_column(DecimalText(4), nullable=False)
    trade_value: Mapped[Decimal] = mapped_column(DecimalText(2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="FILLED_STUB", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


protect_append_only(StubOrder)
