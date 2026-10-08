"""Data access for goal progress snapshots — append-only (goal_tracker_spec §3, NFR-02)."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.models.goal_progress_snapshot import GoalProgressSnapshot


def add_snapshots(session: Session, snapshots: Sequence[GoalProgressSnapshot]) -> None:
    """Insert new goal progress snapshots."""
    session.add_all(snapshots)
    session.flush()


def get_latest_for_goal(session: Session, goal_id: str) -> GoalProgressSnapshot | None:
    """Get the most recent progress snapshot for a goal."""
    stmt = (
        select(GoalProgressSnapshot)
        .where(GoalProgressSnapshot.goal_id == goal_id)
        .order_by(GoalProgressSnapshot.created_at.desc(), GoalProgressSnapshot.id.desc())
        .limit(1)
    )
    return session.scalars(stmt).first()


def list_for_goal(session: Session, goal_id: str) -> Sequence[GoalProgressSnapshot]:
    """Get all progress snapshots for a goal, newest first."""
    stmt = (
        select(GoalProgressSnapshot)
        .where(GoalProgressSnapshot.goal_id == goal_id)
        .order_by(GoalProgressSnapshot.created_at.desc(), GoalProgressSnapshot.id.desc())
    )
    return session.scalars(stmt).all()
