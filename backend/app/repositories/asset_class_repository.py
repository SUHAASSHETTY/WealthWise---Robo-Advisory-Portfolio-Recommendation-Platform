"""Data access for asset class master (admin_versioning_spec §2.5, AC-10)."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.models.reference import AssetClass


def list_all(session: Session) -> Sequence[AssetClass]:
    """List all asset classes ordered by display_order."""
    stmt = select(AssetClass).order_by(AssetClass.display_order.asc(), AssetClass.code.asc())
    return session.scalars(stmt).all()


def list_active(session: Session) -> Sequence[AssetClass]:
    """List active asset classes ordered by display_order."""
    stmt = (
        select(AssetClass)
        .where(AssetClass.is_active.is_(True))
        .order_by(AssetClass.display_order.asc(), AssetClass.code.asc())
    )
    return session.scalars(stmt).all()


def get_by_code(session: Session, code: str) -> AssetClass | None:
    """Get asset class by uppercase code."""
    return session.scalars(select(AssetClass).where(AssetClass.code == code)).first()


def create(session: Session, asset_class: AssetClass) -> AssetClass:
    """Create a new asset class."""
    session.add(asset_class)
    session.flush()
    return asset_class
