"""Users and customers lookups."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.models import Customer, User


def get_by_id(session: Session, customer_id: str) -> Customer | None:
    return session.scalars(select(Customer).where(Customer.id == customer_id)).first()


def get_by_user_id(session: Session, user_id: str) -> Customer | None:
    return session.scalars(select(Customer).where(Customer.user_id == user_id)).first()


def get_by_username(session: Session, username: str) -> Customer | None:
    stmt = select(Customer).join(User, User.id == Customer.user_id).where(User.username == username)
    return session.scalars(stmt).first()


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.scalars(select(User).where(User.username == username)).first()


def get_user_by_id(session: Session, user_id: str) -> User | None:
    return session.scalars(select(User).where(User.id == user_id)).first()


def list_assigned_customers_for_advisor(session: Session, advisor_user_id: str) -> list[Customer]:
    """Get all customers assigned to an advisor."""
    stmt = (
        select(Customer)
        .where(Customer.advisor_user_id == advisor_user_id)
        .order_by(Customer.display_name.asc(), Customer.id.asc())
    )
    return list(session.scalars(stmt))


def list_all_customers(session: Session) -> list[Customer]:
    """Get all customers."""
    return list(session.scalars(select(Customer).order_by(Customer.display_name.asc())))


def active_asset_class_codes(session: Session) -> list[str]:
    from app.repositories.models import AssetClass

    stmt = select(AssetClass.code).where(AssetClass.is_active.is_(True)).order_by(AssetClass.display_order)
    return list(session.scalars(stmt))
