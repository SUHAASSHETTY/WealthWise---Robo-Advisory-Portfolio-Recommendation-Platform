"""Goal domain rules: validation, ordering, and primary goal (goal_tracker_spec §2, AC-03)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain.goal import GoalType


@dataclass(frozen=True)
class GoalInput:
    name: str
    goal_type: GoalType | str
    target_amount: Decimal
    target_date: date
    priority: int
    funding_share_pct: Decimal
    id: str | None = None
    created_at: datetime | None = None


class GoalValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_goal(
    goal: GoalInput,
    existing_goals: Sequence[GoalInput],
    today: date,
    updating_goal_id: str | None = None,
) -> None:
    """Validate goal fields and enforce cumulative funding share constraint (≤ 100.00%)."""
    name = goal.name.strip()
    if not name or len(name) > 80:
        raise GoalValidationError("GOAL_NAME_INVALID", "Goal name must be between 1 and 80 characters.")

    if isinstance(goal.goal_type, str):
        try:
            GoalType(goal.goal_type)
        except ValueError:
            raise GoalValidationError("GOAL_TYPE_INVALID", f"Invalid goal type: {goal.goal_type}") from None

    if goal.target_amount <= Decimal("0.00") or goal.target_amount > Decimal("999999999999.99"):
        raise GoalValidationError(
            "TARGET_AMOUNT_INVALID", "Target amount must be greater than 0.00 and <= 999999999999.99."
        )

    if goal.target_date <= today:
        raise GoalValidationError("TARGET_DATE_NOT_FUTURE", "Target date must be strictly in the future.")

    if not (1 <= goal.priority <= 5):
        raise GoalValidationError("PRIORITY_INVALID", "Priority must be an integer between 1 and 5.")

    if goal.funding_share_pct < Decimal("0.00") or goal.funding_share_pct > Decimal("100.00"):
        raise GoalValidationError("FUNDING_SHARE_INVALID", "Funding share percentage must be between 0.00 and 100.00.")

    # Check total share across other goals + this goal
    other_total = sum(
        (g.funding_share_pct for g in existing_goals if updating_goal_id is None or g.id != updating_goal_id),
        Decimal("0.00"),
    )
    if other_total + goal.funding_share_pct > Decimal("100.00"):
        raise GoalValidationError(
            "FUNDING_SHARE_EXCEEDS_100",
            f"Total funding share ({other_total + goal.funding_share_pct}%) exceeds 100.00%.",
        )


def order_goals[T](goals: Sequence[T]) -> list[T]:
    """Order goals by priority ASC, target_date ASC, created_at ASC."""
    epoch = datetime.min
    return sorted(
        goals,
        key=lambda g: (
            getattr(g, "priority", 5),
            getattr(g, "target_date", date.max),
            getattr(g, "created_at", epoch) or epoch,
        ),
    )


def primary_goal[T](goals: Sequence[T]) -> T | None:
    """Return the customer's primary goal (first in priority order) or None."""
    ordered = order_goals(goals)
    return ordered[0] if ordered else None
