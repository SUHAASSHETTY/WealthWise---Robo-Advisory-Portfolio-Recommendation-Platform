"""Data access for advisor risk band overrides (advisor_workbench_spec §3, AC-09, NFR-02)."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.models.risk_band_override import RiskBandOverride


def create(session: Session, override: RiskBandOverride) -> RiskBandOverride:
    """Insert a new risk band override."""
    session.add(override)
    session.flush()
    return override


def get_latest_for_customer(session: Session, customer_id: str) -> RiskBandOverride | None:
    """Get the most recent risk band override for a customer."""
    stmt = (
        select(RiskBandOverride)
        .where(RiskBandOverride.customer_id == customer_id)
        .order_by(RiskBandOverride.created_at.desc(), RiskBandOverride.id.desc())
        .limit(1)
    )
    return session.scalars(stmt).first()


def list_for_customer(session: Session, customer_id: str) -> Sequence[RiskBandOverride]:
    """Get all risk band overrides for a customer, newest first."""
    stmt = (
        select(RiskBandOverride)
        .where(RiskBandOverride.customer_id == customer_id)
        .order_by(RiskBandOverride.created_at.desc(), RiskBandOverride.id.desc())
    )
    return session.scalars(stmt).all()
