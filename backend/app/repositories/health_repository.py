"""Database connectivity probe used by the health service."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def ping(session: Session) -> None:
    """Execute `SELECT 1`; raises sqlalchemy.exc.SQLAlchemyError if the database is unreachable."""
    session.execute(text("SELECT 1"))
