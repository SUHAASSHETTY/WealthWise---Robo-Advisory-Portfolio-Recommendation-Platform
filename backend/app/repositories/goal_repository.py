"""Goal queries and updates scoped to customer (goal_tracker_spec §3, AC-03)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.models import Goal


def list_for_customer(session: Session, customer_id: str) -> list[Goal]:
    """Return all goals for a customer."""
    return list(session.scalars(select(Goal).where(Goal.customer_id == customer_id)))


def get_for_customer(session: Session, customer_id: str, goal_id: str) -> Goal | None:
    """Return specific goal for a customer or None."""
    return session.scalars(select(Goal).where(Goal.id == goal_id, Goal.customer_id == customer_id)).first()


def create(session: Session, goal: Goal) -> Goal:
    """Insert a new goal."""
    session.add(goal)
    session.flush()
    return goal
