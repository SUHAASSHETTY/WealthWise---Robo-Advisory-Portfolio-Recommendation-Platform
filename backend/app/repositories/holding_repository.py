"""Data access for customer holdings (holdings_spec §3)."""

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.models.holding import Holding


def list_for_customer(session: Session, customer_id: str) -> Sequence[Holding]:
    """Return all holdings for a customer, ordered by asset class code."""
    stmt = select(Holding).where(Holding.customer_id == customer_id).order_by(Holding.asset_class_code.asc())
    return session.scalars(stmt).all()


def set_units(
    session: Session,
    customer_id: str,
    asset_class_code: str,
    units: Decimal,
) -> Holding:
    """Insert or update holding units for a customer and asset class."""
    stmt = select(Holding).where(
        Holding.customer_id == customer_id,
        Holding.asset_class_code == asset_class_code,
    )
    existing = session.scalars(stmt).first()
    if existing is not None:
        existing.units = units
        session.flush()
        return existing

    holding = Holding(
        customer_id=customer_id,
        asset_class_code=asset_class_code,
        units=units,
    )
    session.add(holding)
    session.flush()
    return holding
