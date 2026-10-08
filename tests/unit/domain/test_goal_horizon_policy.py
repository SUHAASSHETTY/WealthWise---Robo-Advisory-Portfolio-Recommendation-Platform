"""AC-04 — goal horizon: completed calendar months, rule selection, primary goal (recommendation_spec §2.2)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from tests.fixtures.policy_definitions import ASSET_CLASSES, template_v1

from app.domain.goal import GoalSnapshot
from app.domain.goal_horizon_policy import horizon_months, order_goals, primary_goal, select_rule
from app.domain.template_version_validator import HorizonRule, TemplateVersionDefinition, parse_template_version


def _v1() -> TemplateVersionDefinition:
    return parse_template_version(template_v1(), ASSET_CLASSES)


def _goal(goal_id: str, priority: int, target: date, created: datetime | None = None) -> GoalSnapshot:
    return GoalSnapshot(
        id=goal_id,
        priority=priority,
        target_date=target,
        target_amount=Decimal("100000.00"),
        created_at=created or datetime(2026, 1, 1, 9, 0, 0),
    )


# ---------------------------------------------------------------- horizon_months


@pytest.mark.ac("AC-04")
@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (date(2026, 2, 28), 0),
        (date(2027, 1, 31), 12),
        (date(2025, 12, 1), 0),
    ],
)
def test_ac_04_horizon_months_counts_completed_calendar_months(target: date, expected: int) -> None:
    """AC-04.5 — as_of 2026-01-31: 2026-02-28 → 0, 2027-01-31 → 12, 2025-12-01 → 0."""
    assert horizon_months(date(2026, 1, 31), target) == expected


@pytest.mark.ac("AC-04")
@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (date(2030, 1, 15), 48),
        (date(2028, 6, 30), 29),
    ],
)
def test_ac_04_horizon_months_from_mid_month_clock(target: date, expected: int) -> None:
    """AC-04.1 / AC-04.3 — as_of 2026-01-15: 2030-01-15 → 48, 2028-06-30 → 29."""
    assert horizon_months(date(2026, 1, 15), target) == expected


@pytest.mark.ac("AC-04")
def test_ac_04_horizon_months_is_zero_when_target_equals_as_of() -> None:
    """AC-04.5 — target_date ≤ as_of_date gives 0 (equality boundary)."""
    assert horizon_months(date(2026, 1, 31), date(2026, 1, 31)) == 0


@pytest.mark.ac("AC-04")
def test_ac_04_horizon_months_one_day_short_of_a_month_is_not_completed() -> None:
    """AC-04.5 — 2026-01-15 → 2026-02-14 is 0 completed months; → 2026-02-15 is 1."""
    assert horizon_months(date(2026, 1, 15), date(2026, 2, 14)) == 0
    assert horizon_months(date(2026, 1, 15), date(2026, 2, 15)) == 1


# ---------------------------------------------------------------- select_rule


@pytest.mark.ac("AC-02")
@pytest.mark.parametrize(
    ("months", "code"),
    [
        (0, "H_0_11"),
        (1, "H_0_11"),
        (11, "H_0_11"),
        (12, "H_12_35"),
        (35, "H_12_35"),
        (36, "H_36_59"),
        (59, "H_36_59"),
        (60, "H_60_83"),
        (83, "H_60_83"),
        (84, "H_84_PLUS"),
        (240, "H_84_PLUS"),
    ],
)
def test_ac_02_select_rule_boundaries_on_both_sides(months: int, code: str) -> None:
    """AC-02.3 / AC-04.2 — boundary months 11/12, 35/36, 59/60, 83/84 select the v1 horizon rule."""
    rule = select_rule(_v1().horizon_rules, months)

    assert rule is not None
    assert rule.code == code


@pytest.mark.ac("AC-02")
def test_ac_02_select_rule_without_goal_is_no_goal() -> None:
    """AC-02.1 — no goal (months None) → no horizon rule, i.e. NO_GOAL."""
    assert select_rule(_v1().horizon_rules, None) is None


@pytest.mark.ac("AC-04")
def test_ac_04_select_rule_raises_when_no_rule_covers_months() -> None:
    """AC-04.2 — rules that do not cover the horizon are a policy error, never a silent NO_GOAL."""
    rules = (HorizonRule("H_12_PLUS", 12, None, Decimal("0.00"), "EQUITY", "DEBT"),)

    with pytest.raises(ValueError, match="no horizon rule covers 5 months"):
        select_rule(rules, 5)


# ---------------------------------------------------------------- primary goal


@pytest.mark.ac("AC-04")
def test_ac_04_primary_goal_is_lowest_priority_number() -> None:
    """AC-04.3 — A (P2, 2040-01-01) and B (P1, 2028-06-30), clock 2026-01-15 → B, 29 months, H_12_35."""
    goal_a = _goal("A", 2, date(2040, 1, 1))
    goal_b = _goal("B", 1, date(2028, 6, 30))

    primary = primary_goal([goal_a, goal_b])

    assert primary == goal_b
    months = horizon_months(date(2026, 1, 15), goal_b.target_date)
    assert months == 29
    rule = select_rule(_v1().horizon_rules, months)
    assert rule is not None
    assert rule.code == "H_12_35"


@pytest.mark.ac("AC-04")
def test_ac_04_goal_order_ties_break_on_target_date_then_created_at() -> None:
    """AC-04.3 — priority ASC, then target_date ASC, then created_at ASC."""
    late = _goal("late", 1, date(2031, 1, 1), datetime(2025, 1, 1, 9, 0, 0))
    early_newer = _goal("early_newer", 1, date(2030, 1, 1), datetime(2025, 6, 1, 9, 0, 0))
    early_older = _goal("early_older", 1, date(2030, 1, 1), datetime(2025, 3, 1, 9, 0, 0))
    low = _goal("low", 3, date(2027, 1, 1), datetime(2024, 1, 1, 9, 0, 0))

    ordered = order_goals([low, late, early_newer, early_older])

    assert [g.id for g in ordered] == ["early_older", "early_newer", "late", "low"]
    assert primary_goal([low, late, early_newer, early_older]) == early_older


@pytest.mark.ac("AC-04")
def test_ac_04_primary_goal_of_no_goals_is_none() -> None:
    """AC-04.3 — a customer with no goals has no primary goal (rule NO_GOAL)."""
    assert primary_goal([]) is None
    assert order_goals([]) == ()
