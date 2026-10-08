"""Data access for asset class NAV prices (admin_versioning_spec §3, holdings_spec §3)."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.repositories.models.nav_price import NavPrice


def get_latest_nav_date(session: Session) -> date | None:
    """Return the most recent NAV date stored in nav_prices."""
    stmt = select(func.max(NavPrice.nav_date))
    return session.scalar(stmt)


def get_navs_for_date(session: Session, nav_date: date) -> dict[str, Decimal]:
    """Return asset class -> NAV mapping for the specified date."""
    stmt = select(NavPrice).where(NavPrice.nav_date == nav_date)
    rows = session.scalars(stmt).all()
    return {row.asset_class_code: row.nav for row in rows}


def get_latest_navs(session: Session) -> tuple[date | None, dict[str, Decimal]]:
    """Return (latest_nav_date, asset_class -> NAV mapping)."""
    latest_date = get_latest_nav_date(session)
    if latest_date is None:
        return None, {}
    return latest_date, get_navs_for_date(session, latest_date)


def has_date(session: Session, nav_date: date) -> bool:
    """Check if any NAV prices exist for the given date."""
    stmt = select(NavPrice.id).where(NavPrice.nav_date == nav_date).limit(1)
    return session.scalar(stmt) is not None


def add_nav_prices(session: Session, prices: Sequence[NavPrice]) -> None:
    """Add new NAV price records."""
    session.add_all(prices)
    session.flush()
