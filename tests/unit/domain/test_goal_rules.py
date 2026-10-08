"""Unit tests for goal domain rules (goal_tracker_spec §2, AC-03, AC-08)."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domain.goal import GoalType
from app.domain.goal_rules import (
    GoalInput,
    GoalValidationError,
    order_goals,
    primary_goal,
    validate_goal,
)

TODAY = date(2026, 1, 15)


@pytest.mark.ac("AC-03")
def test_ac_03_1_validate_valid_goal() -> None:
    """AC-03.1: Valid goal inputs pass validation without error."""
    g = GoalInput(
        name="Daughter's university",
        goal_type=GoalType.EDUCATION,
        target_amount=Decimal("50000.00"),
        target_date=date(2032, 8, 31),
        priority=1,
        funding_share_pct=Decimal("40.00"),
    )
    validate_goal(g, existing_goals=[], today=TODAY)


@pytest.mark.ac("AC-03")
def test_ac_03_3_validation_rules() -> None:
    """AC-03.3: Name, type, amount, date, priority, and share validation errors."""
    # Invalid name
    with pytest.raises(GoalValidationError) as exc:
        validate_goal(
            GoalInput(
                name="   ",
                goal_type=GoalType.EDUCATION,
                target_amount=Decimal("50000.00"),
                target_date=date(2032, 8, 31),
                priority=1,
                funding_share_pct=Decimal("40.00"),
            ),
            existing_goals=[],
            today=TODAY,
        )
    assert exc.value.code == "GOAL_NAME_INVALID"

    # Name too long
    with pytest.raises(GoalValidationError) as exc:
        validate_goal(
            GoalInput(
                name="x" * 81,
                goal_type=GoalType.EDUCATION,
                target_amount=Decimal("50000.00"),
                target_date=date(2032, 8, 31),
                priority=1,
                funding_share_pct=Decimal("40.00"),
            ),
            existing_goals=[],
            today=TODAY,
        )
    assert exc.value.code == "GOAL_NAME_INVALID"

    # Target amount <= 0
    with pytest.raises(GoalValidationError) as exc:
        validate_goal(
            GoalInput(
                name="Test",
                goal_type=GoalType.HOME,
                target_amount=Decimal("0.00"),
                target_date=date(2032, 8, 31),
                priority=1,
                funding_share_pct=Decimal("40.00"),
            ),
            existing_goals=[],
            today=TODAY,
        )
    assert exc.value.code == "TARGET_AMOUNT_INVALID"

    # Target date not future
    with pytest.raises(GoalValidationError) as exc:
        validate_goal(
            GoalInput(
                name="Test",
                goal_type=GoalType.HOME,
                target_amount=Decimal("1000.00"),
                target_date=TODAY,
                priority=1,
                funding_share_pct=Decimal("40.00"),
            ),
            existing_goals=[],
            today=TODAY,
        )
    assert exc.value.code == "TARGET_DATE_NOT_FUTURE"

    # Priority invalid (<1 or >5)
    with pytest.raises(GoalValidationError) as exc:
        validate_goal(
            GoalInput(
                name="Test",
                goal_type=GoalType.HOME,
                target_amount=Decimal("1000.00"),
                target_date=date(2030, 1, 1),
                priority=6,
                funding_share_pct=Decimal("40.00"),
            ),
            existing_goals=[],
            today=TODAY,
        )
    assert exc.value.code == "PRIORITY_INVALID"

    # Funding share invalid (<0 or >100)
    with pytest.raises(GoalValidationError) as exc:
        validate_goal(
            GoalInput(
                name="Test",
                goal_type=GoalType.HOME,
                target_amount=Decimal("1000.00"),
                target_date=date(2030, 1, 1),
                priority=2,
                funding_share_pct=Decimal("-5.00"),
            ),
            existing_goals=[],
            today=TODAY,
        )
    assert exc.value.code == "FUNDING_SHARE_INVALID"


@pytest.mark.ac("AC-03")
def test_ac_03_4_funding_share_cap() -> None:
    """AC-03.4: Cumulative funding share across customer's goals cannot exceed 100.00%."""
    existing = [
        GoalInput(
            name="G1",
            goal_type=GoalType.RETIREMENT,
            target_amount=Decimal("100000.00"),
            target_date=date(2040, 1, 1),
            priority=1,
            funding_share_pct=Decimal("60.00"),
        ),
        GoalInput(
            name="G2",
            goal_type=GoalType.EDUCATION,
            target_amount=Decimal("50000.00"),
            target_date=date(2035, 1, 1),
            priority=2,
            funding_share_pct=Decimal("40.00"),
        ),
    ]
    # Adding 0.00 is valid
    g_zero = GoalInput(
        name="G3",
        goal_type=GoalType.OTHER,
        target_amount=Decimal("10000.00"),
        target_date=date(2035, 1, 1),
        priority=3,
        funding_share_pct=Decimal("0.00"),
    )
    validate_goal(g_zero, existing_goals=existing, today=TODAY)

    # Adding 0.01 exceeds 100.00
    g_over = GoalInput(
        name="G3",
        goal_type=GoalType.OTHER,
        target_amount=Decimal("10000.00"),
        target_date=date(2035, 1, 1),
        priority=3,
        funding_share_pct=Decimal("0.01"),
    )
    with pytest.raises(GoalValidationError) as exc:
        validate_goal(g_over, existing_goals=existing, today=TODAY)
    assert exc.value.code == "FUNDING_SHARE_EXCEEDS_100"


@pytest.mark.ac("AC-03")
def test_ac_03_2_order_goals_and_primary() -> None:
    """AC-03.2: Goals ordered by priority ASC, target_date ASC, created_at ASC."""
    now = datetime(2026, 1, 15, 10, 0)
    g_uni = GoalInput(
        id="g1",
        name="Daughter's university",
        goal_type=GoalType.EDUCATION,
        target_amount=Decimal("50000.00"),
        target_date=date(2032, 8, 31),
        priority=1,
        funding_share_pct=Decimal("40.00"),
        created_at=now,
    )
    g_ret = GoalInput(
        id="g2",
        name="Retirement corpus",
        goal_type=GoalType.RETIREMENT,
        target_amount=Decimal("500000.00"),
        target_date=date(2050, 3, 31),
        priority=2,
        funding_share_pct=Decimal("60.00"),
        created_at=now,
    )
    ordered = order_goals([g_ret, g_uni])
    assert ordered[0].name == "Daughter's university"
    assert ordered[1].name == "Retirement corpus"
    assert primary_goal([g_ret, g_uni]) == g_uni
    assert primary_goal([]) is None


@pytest.mark.ac("AC-03")
def test_ac_03_string_goal_type() -> None:
    g_str = GoalInput(
        name="Valid String Type",
        goal_type="RETIREMENT",
        target_amount=Decimal("1000.00"),
        target_date=date(2030, 1, 1),
        priority=1,
        funding_share_pct=Decimal("10.00"),
    )
    validate_goal(g_str, existing_goals=[], today=TODAY)

    g_invalid = GoalInput(
        name="Invalid String Type",
        goal_type="INVALID_TYPE",
        target_amount=Decimal("1000.00"),
        target_date=date(2030, 1, 1),
        priority=1,
        funding_share_pct=Decimal("10.00"),
    )
    with pytest.raises(GoalValidationError) as exc:
        validate_goal(g_invalid, existing_goals=[], today=TODAY)
    assert exc.value.code == "GOAL_TYPE_INVALID"
