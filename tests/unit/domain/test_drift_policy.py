"""Unit tests for holdings valuation and drift calculation domain rules.

Scope: AC-05.1 to AC-05.6, AC-08.1, AC-08.3, AC-08.5.
"""

from decimal import Decimal

import pytest

from app.domain.drift_policy import (
    HoldingInput,
    ValuedHolding,
    calculate_goal_progress,
    compute_drift,
    value_holdings,
)


@pytest.mark.ac("AC-05")
def test_ac_05_1_valuation_per_class_alice_example() -> None:
    """AC-05.1: Alice holdings (400 equity, 1000 debt, 150 gold, 6000 cash) valued at 2026-01-15 NAVs."""
    holdings = [
        HoldingInput(asset_class="EQUITY", units=Decimal("400.0000")),
        HoldingInput(asset_class="DEBT", units=Decimal("1000.0000")),
        HoldingInput(asset_class="GOLD", units=Decimal("150.0000")),
        HoldingInput(asset_class="CASH", units=Decimal("6000.0000")),
    ]
    navs = {
        "EQUITY": Decimal("150.0000"),
        "DEBT": Decimal("25.0000"),
        "GOLD": Decimal("60.0000"),
        "CASH": Decimal("1.0000"),
    }

    valued = value_holdings(holdings, navs)

    assert len(valued) == 4
    val_map = {v.asset_class: v.current_value for v in valued}
    assert val_map["EQUITY"] == Decimal("60000.00")
    assert val_map["DEBT"] == Decimal("25000.00")
    assert val_map["GOLD"] == Decimal("9000.00")
    assert val_map["CASH"] == Decimal("6000.00")
    assert sum(v.current_value for v in valued) == Decimal("100000.00")


@pytest.mark.ac("AC-05")
def test_ac_05_2_drift_per_class_alice_moderate_v1() -> None:
    """AC-05.2: Alice drift against MODERATE v1 template (50/35/10/5), threshold 5.00."""
    valued = [
        ValuedHolding(
            asset_class="EQUITY",
            units=Decimal("400.0000"),
            nav=Decimal("150.0000"),
            current_value=Decimal("60000.00"),
        ),
        ValuedHolding(
            asset_class="DEBT",
            units=Decimal("1000.0000"),
            nav=Decimal("25.0000"),
            current_value=Decimal("25000.00"),
        ),
        ValuedHolding(
            asset_class="GOLD",
            units=Decimal("150.0000"),
            nav=Decimal("60.0000"),
            current_value=Decimal("9000.00"),
        ),
        ValuedHolding(
            asset_class="CASH",
            units=Decimal("6000.0000"),
            nav=Decimal("1.0000"),
            current_value=Decimal("6000.00"),
        ),
    ]
    target = {
        "EQUITY": Decimal("50.00"),
        "DEBT": Decimal("35.00"),
        "GOLD": Decimal("10.00"),
        "CASH": Decimal("5.00"),
    }

    report = compute_drift(valued, target=target, threshold=Decimal("5.00"))

    assert report.total_value == Decimal("100000.00")
    assert report.has_target is True
    assert report.drift_threshold_pct == Decimal("5.00")
    assert report.portfolio_breached is True

    line_map = {line.asset_class: line for line in report.lines}
    assert (line_map["EQUITY"].current_pct, line_map["EQUITY"].drift_pct, line_map["EQUITY"].breached) == (
        Decimal("60.00"),
        Decimal("10.00"),
        True,
    )
    assert (line_map["DEBT"].current_pct, line_map["DEBT"].drift_pct, line_map["DEBT"].breached) == (
        Decimal("25.00"),
        Decimal("10.00"),
        True,
    )
    assert (line_map["GOLD"].current_pct, line_map["GOLD"].drift_pct, line_map["GOLD"].breached) == (
        Decimal("9.00"),
        Decimal("1.00"),
        False,
    )
    assert (line_map["CASH"].current_pct, line_map["CASH"].drift_pct, line_map["CASH"].breached) == (
        Decimal("6.00"),
        Decimal("1.00"),
        False,
    )


@pytest.mark.ac("AC-05")
def test_ac_05_3_value_follows_nav_equity_165() -> None:
    """AC-05.3: NAV refresh with EQUITY at 165.0000 -> total 106000.00, equity % 62.26, drift 12.26."""
    holdings = [
        HoldingInput(asset_class="EQUITY", units=Decimal("400.0000")),
        HoldingInput(asset_class="DEBT", units=Decimal("1000.0000")),
        HoldingInput(asset_class="GOLD", units=Decimal("150.0000")),
        HoldingInput(asset_class="CASH", units=Decimal("6000.0000")),
    ]
    navs = {
        "EQUITY": Decimal("165.0000"),
        "DEBT": Decimal("25.0000"),
        "GOLD": Decimal("60.0000"),
        "CASH": Decimal("1.0000"),
    }
    target = {
        "EQUITY": Decimal("50.00"),
        "DEBT": Decimal("35.00"),
        "GOLD": Decimal("10.00"),
        "CASH": Decimal("5.00"),
    }

    valued = value_holdings(holdings, navs)
    report = compute_drift(valued, target=target, threshold=Decimal("5.00"))

    assert report.total_value == Decimal("106000.00")
    line_map = {line.asset_class: line for line in report.lines}
    assert line_map["EQUITY"].current_value == Decimal("66000.00")
    assert line_map["EQUITY"].current_pct == Decimal("62.26")
    assert line_map["EQUITY"].drift_pct == Decimal("12.26")
    assert line_map["EQUITY"].breached is True

    assert line_map["DEBT"].current_pct == Decimal("23.58")
    assert line_map["DEBT"].drift_pct == Decimal("11.42")
    assert line_map["DEBT"].breached is True


@pytest.mark.ac("AC-05")
def test_ac_05_4_half_even_rounding_2dp() -> None:
    """AC-05.4: 33.3333 units * 3.0000 NAV = 100.00; ratio 12.345% rounds to 12.34%."""
    holdings = [HoldingInput(asset_class="EQUITY", units=Decimal("33.3333"))]
    navs = {"EQUITY": Decimal("3.0000")}
    valued = value_holdings(holdings, navs)
    assert valued[0].current_value == Decimal("100.00")

    # Ratio test with custom values: value 123.45 on total 1000.00 -> 12.345% -> 12.34%
    valued_test = [
        ValuedHolding(asset_class="EQUITY", units=Decimal("1"), nav=Decimal("123.45"), current_value=Decimal("123.45")),
        ValuedHolding(asset_class="DEBT", units=Decimal("1"), nav=Decimal("876.55"), current_value=Decimal("876.55")),
    ]
    report = compute_drift(valued_test, target=None, threshold=None)
    line_map = {line.asset_class: line for line in report.lines}
    assert line_map["EQUITY"].current_pct == Decimal("12.34")


@pytest.mark.ac("AC-05")
def test_ac_05_5_no_target_recommendation() -> None:
    """AC-05.5: Customer has holdings but no recommendation -> has_target=false, target and drift are None."""
    valued = [
        ValuedHolding(
            asset_class="EQUITY",
            units=Decimal("100.0000"),
            nav=Decimal("10.0000"),
            current_value=Decimal("1000.00"),
        ),
    ]
    report = compute_drift(valued, target=None, threshold=None)

    assert report.total_value == Decimal("1000.00")
    assert report.has_target is False
    assert report.drift_threshold_pct is None
    assert report.portfolio_breached is False
    assert report.lines[0].current_pct == Decimal("100.00")
    assert report.lines[0].target_pct is None
    assert report.lines[0].drift_pct is None
    assert report.lines[0].breached is None


@pytest.mark.ac("AC-05")
def test_ac_05_zero_holdings_total_value_zero() -> None:
    """Edge case: zero holdings -> total_value is 0.00, percentages are None."""
    valued = [
        ValuedHolding(
            asset_class="EQUITY",
            units=Decimal("0.0000"),
            nav=Decimal("100.0000"),
            current_value=Decimal("0.00"),
        ),
        ValuedHolding(
            asset_class="DEBT",
            units=Decimal("0.0000"),
            nav=Decimal("20.0000"),
            current_value=Decimal("0.00"),
        ),
    ]
    target = {"EQUITY": Decimal("50.00"), "DEBT": Decimal("50.00")}
    report = compute_drift(valued, target=target, threshold=Decimal("5.00"))

    assert report.total_value == Decimal("0.00")
    assert report.portfolio_breached is False
    for line in report.lines:
        assert line.current_pct is None
        assert line.drift_pct is None
        assert line.breached is None


@pytest.mark.ac("AC-05")
def test_ac_05_target_without_threshold() -> None:
    """Target provided but threshold is None -> breached is False."""
    valued = [
        ValuedHolding(
            asset_class="EQUITY",
            units=Decimal("100.0000"),
            nav=Decimal("10.0000"),
            current_value=Decimal("1000.00"),
        ),
    ]
    target = {"EQUITY": Decimal("100.00")}
    report = compute_drift(valued, target=target, threshold=None)
    assert report.lines[0].breached is False
    assert report.portfolio_breached is False


@pytest.mark.ac("AC-08")
def test_ac_08_goal_progress_calculation() -> None:
    """AC-08.1 / AC-08.3 / AC-08.5: Goal progress math with Decimal precision."""
    # Alice Retirement goal: 60% share of 100000.00 portfolio on 500000.00 target
    res1 = calculate_goal_progress(
        total_value=Decimal("100000.00"),
        funding_share_pct=Decimal("60.00"),
        target_amount=Decimal("500000.00"),
    )
    assert res1.current_goal_value == Decimal("60000.00")
    assert res1.percent_complete == Decimal("12.00")
    assert res1.status == "IN_PROGRESS"

    # Achieved goal: 40% share of 100000.00 on 30000.00 target -> 40000.00 / 30000.00 = 133.33%
    res2 = calculate_goal_progress(
        total_value=Decimal("100000.00"),
        funding_share_pct=Decimal("40.00"),
        target_amount=Decimal("30000.00"),
    )
    assert res2.current_goal_value == Decimal("40000.00")
    assert res2.percent_complete == Decimal("133.33")
    assert res2.status == "ACHIEVED"

    # Zero target amount
    res3 = calculate_goal_progress(
        total_value=Decimal("100000.00"),
        funding_share_pct=Decimal("40.00"),
        target_amount=Decimal("0.00"),
    )
    assert res3.percent_complete == Decimal("0.00")
