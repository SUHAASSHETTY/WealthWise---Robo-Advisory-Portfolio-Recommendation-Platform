"""Maps an authenticated CUSTOMER principal to its customer id. Customer ids never come from the URL (NFR-04)."""

from sqlalchemy.orm import Session

from app.core.security import Principal, Role
from app.repositories import customer_repository
from app.services.errors import ServiceError


def customer_id_for(session: Session, principal: Principal) -> str:
    if principal.role != Role.CUSTOMER:
        raise ServiceError(403, "FORBIDDEN_ROLE", "Only customers have a customer profile.")
    customer = customer_repository.get_by_username(session, principal.username)
    if customer is None:
        raise ServiceError(403, "FORBIDDEN_ROLE", "No customer profile for this user.")
    return customer.id


def user_id_for(session: Session, principal: Principal) -> str | None:
    user = customer_repository.get_user_by_username(session, principal.username)
    return None if user is None else user.id
