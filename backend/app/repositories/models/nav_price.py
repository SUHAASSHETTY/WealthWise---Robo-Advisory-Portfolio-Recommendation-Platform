"""Historical asset class NAV prices (admin_versioning_spec §3, holdings_spec §3)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import DecimalText
from app.repositories.base import Base
from app.repositories.models._columns import new_uuid, utcnow


class NavPrice(Base):
    __tablename__ = "nav_prices"
    __table_args__ = (UniqueConstraint("asset_class_code", "nav_date", name="uq_nav_prices_asset_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    asset_class_code: Mapped[str] = mapped_column(ForeignKey("asset_classes.code"), nullable=False)
    nav_date: Mapped[date] = mapped_column(Date, nullable=False)
    nav: Mapped[Decimal] = mapped_column(DecimalText(4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
