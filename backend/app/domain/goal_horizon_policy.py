"""Goal horizon rules (recommendation_spec §2.2, AC-04): completed calendar months, rule selection, primary goal.

Pure functions: `as_of` always comes from the caller's injected clock; rules come from the template version.
"""

from collections.abc import Sequence
from datetime import date

from app.domain.goal import GoalSnapshot
from app.domain.template_version_validator import HorizonRule


def horizon_months(as_of: date, target: date) -> int:
    """Completed calendar months from `as_of` to `target`; 0 when `target <= as_of`."""
    if target <= as_of:
        return 0
    months = (target.year - as_of.year) * 12 + (target.month - as_of.month)
    return months - 1 if target.day < as_of.day else months


def select_rule(rules: Sequence[HorizonRule], months: int | None) -> HorizonRule | None:
    """The rule whose [min_months, max_months] covers `months`; None (NO_GOAL) when there is no goal."""
    if months is None:
        return None
    for rule in rules:
        if rule.min_months <= months and (rule.max_months is None or months <= rule.max_months):
            return rule
    raise ValueError(f"no horizon rule covers {months} months")


def order_goals(goals: Sequence[GoalSnapshot]) -> tuple[GoalSnapshot, ...]:
    """Goals by priority ASC, then target_date ASC, then created_at ASC."""
    return tuple(sorted(goals, key=lambda g: (g.priority, g.target_date, g.created_at)))


def primary_goal(goals: Sequence[GoalSnapshot]) -> GoalSnapshot | None:
    """The first goal in `order_goals` order, or None when the customer has no goals."""
    ordered = order_goals(goals)
    return ordered[0] if ordered else None
