"""Customer holdings per asset class (holdings_spec §3)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import DecimalText
from app.repositories.base import Base
from app.repositories.models._columns import new_uuid, utcnow


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (UniqueConstraint("customer_id", "asset_class_code", name="uq_holdings_customer_asset_class"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    asset_class_code: Mapped[str] = mapped_column(ForeignKey("asset_classes.code"), nullable=False)
    units: Mapped[Decimal] = mapped_column(DecimalText(4), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
