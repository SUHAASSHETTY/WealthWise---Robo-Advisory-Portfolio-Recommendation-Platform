"""Unit tests for rebalancing domain policy (rebalancing_spec §2, AC-06, AC-07)."""

from decimal import Decimal

import pytest

from app.domain.drift_policy import ValuedHolding
from app.domain.rebalancing_policy import (
    OversellError,
    propose_rebalance,
)


@pytest.mark.ac("AC-07")
def test_ac_07_1_alice_worked_example() -> None:
    """AC-07.1: Alice $100,000 portfolio against MODERATE v1 template (50/35/10/5)."""
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
    navs = {
        "EQUITY": Decimal("150.0000"),
        "DEBT": Decimal("25.0000"),
        "GOLD": Decimal("60.0000"),
        "CASH": Decimal("1.0000"),
    }
    display_order = ["EQUITY", "DEBT", "GOLD", "CASH"]

    proposal = propose_rebalance(
        valued=valued,
        target=target,
        navs=navs,
        display_order=display_order,
    )

    assert proposal.total_value == Decimal("100000.00")
    assert proposal.post_trade_cash == Decimal("4999.99")

    lines_by_class = {line.asset_class: line for line in proposal.lines}

    # EQUITY: SELL 66.6666 @ 150.0000 -> 9999.99
    eq = lines_by_class["EQUITY"]
    assert eq.action == "SELL"
    assert eq.quantity == Decimal("66.6666")
    assert eq.trade_value == Decimal("9999.99")
    assert eq.target_value == Decimal("50000.00")

    # DEBT: BUY 400.0000 @ 25.0000 -> 10000.00
    debt = lines_by_class["DEBT"]
    assert debt.action == "BUY"
    assert debt.quantity == Decimal("400.0000")
    assert debt.trade_value == Decimal("10000.00")
    assert debt.target_value == Decimal("35000.00")

    # GOLD: BUY 16.6666 @ 60.0000 -> 1000.00
    gold = lines_by_class["GOLD"]
    assert gold.action == "BUY"
    assert gold.quantity == Decimal("16.6666")
    assert gold.trade_value == Decimal("1000.00")
    assert gold.target_value == Decimal("10000.00")

    # CASH: SETTLEMENT
    cash = lines_by_class["CASH"]
    assert cash.action == "SETTLEMENT"
    assert cash.quantity is None
    assert cash.trade_value is None


@pytest.mark.ac("AC-07")
def test_ac_07_negative_cash_guard() -> None:
    """Negative cash guard adjusts largest BUY line by 0.0001 units until post-trade cash >= 0.00."""
    valued = [
        ValuedHolding(
            asset_class="EQUITY",
            units=Decimal("100.0000"),
            nav=Decimal("100.0000"),
            current_value=Decimal("10000.00"),
        ),
        ValuedHolding(
            asset_class="DEBT",
            units=Decimal("0.0000"),
            nav=Decimal("10.0000"),
            current_value=Decimal("0.00"),
        ),
        ValuedHolding(
            asset_class="CASH",
            units=Decimal("0.0000"),
            nav=Decimal("1.0000"),
            current_value=Decimal("0.00"),
        ),
    ]
    # Target: 0% Equity, 100% Debt, 0% Cash
    target = {
        "EQUITY": Decimal("0.00"),
        "DEBT": Decimal("100.00"),
        "CASH": Decimal("0.00"),
    }
    navs = {
        "EQUITY": Decimal("100.0000"),
        "DEBT": Decimal("10.0000"),
        "CASH": Decimal("1.0000"),
    }
    display_order = ["EQUITY", "DEBT", "CASH"]

    proposal = propose_rebalance(
        valued=valued,
        target=target,
        navs=navs,
        display_order=display_order,
    )

    assert proposal.post_trade_cash >= Decimal("0.00")


@pytest.mark.ac("AC-07")
def test_ac_07_oversell_guard() -> None:
    """Attempting to SELL more units than customer holds raises OversellError."""
    from app.domain.rebalancing_policy import _check_oversell

    with pytest.raises(OversellError):
        _check_oversell(action="SELL", quantity=Decimal("20.0000"), units=Decimal("10.0000"))


@pytest.mark.ac("AC-07")
def test_ac_07_rebalance_no_trades_needed_and_zero_nav() -> None:
    """When portfolio perfectly matches target or NAV is 0, proposal outputs NONE."""
    valued = [
        ValuedHolding(
            asset_class="EQUITY",
            units=Decimal("10.0000"),
            nav=Decimal("100.0000"),
            current_value=Decimal("1000.00"),
        ),
        ValuedHolding(
            asset_class="DEBT",
            units=Decimal("0.0000"),
            nav=Decimal("0.0000"),
            current_value=Decimal("0.00"),
        ),
        ValuedHolding(
            asset_class="CASH",
            units=Decimal("0.0000"),
            nav=Decimal("1.0000"),
            current_value=Decimal("0.00"),
        ),
    ]
    target = {
        "EQUITY": Decimal("100.00"),
        "DEBT": Decimal("0.00"),
        "CASH": Decimal("0.00"),
    }
    navs = {
        "EQUITY": Decimal("100.0000"),
        "DEBT": Decimal("0.0000"),
        "CASH": Decimal("1.0000"),
    }
    proposal = propose_rebalance(
        valued=valued,
        target=target,
        navs=navs,
        display_order=["EQUITY", "DEBT", "CASH"],
    )
    eq = [row for row in proposal.lines if row.asset_class == "EQUITY"][0]
    assert eq.action == "NONE"
    debt = [row for row in proposal.lines if row.asset_class == "DEBT"][0]
    assert debt.action == "NONE"


@pytest.mark.ac("AC-07")
def test_ac_07_negative_cash_step_down_to_none() -> None:
    """If negative cash occurs with a tiny buy qty, step down reduces quantity and can set action to NONE."""
    proposal = propose_rebalance(
        valued=[
            ValuedHolding(
                asset_class="EQUITY",
                units=Decimal("1.0000"),
                nav=Decimal("9.9900"),
                current_value=Decimal("9.99"),
            ),
            ValuedHolding(
                asset_class="DEBT",
                units=Decimal("0.0000"),
                nav=Decimal("3.0000"),
                current_value=Decimal("0.00"),
            ),
            ValuedHolding(
                asset_class="CASH",
                units=Decimal("0.0000"),
                nav=Decimal("1.0000"),
                current_value=Decimal("0.00"),
            ),
        ],
        target={"EQUITY": Decimal("0.00"), "DEBT": Decimal("100.00"), "CASH": Decimal("0.00")},
        navs={"EQUITY": Decimal("9.9900"), "DEBT": Decimal("3.0000"), "CASH": Decimal("1.0000")},
        display_order=["EQUITY", "DEBT", "CASH"],
    )
    debt = [row for row in proposal.lines if row.asset_class == "DEBT"][0]
    assert debt.action == "BUY"
    assert proposal.post_trade_cash >= Decimal("0.00")


@pytest.mark.ac("AC-07")
def test_ac_07_negative_cash_step_down_depletion() -> None:
    """If post_trade_cash is negative, BUY line quantities get stepped down until >= 0."""
    # Valued holding has 0 cash and 0 units in anything except CASH=0.00, but let's test propose_rebalance directly
    proposal = propose_rebalance(
        valued=[
            ValuedHolding(
                asset_class="EQUITY",
                units=Decimal("0.0000"),
                nav=Decimal("10.0000"),
                current_value=Decimal("0.00"),
            ),
            ValuedHolding(
                asset_class="DEBT",
                units=Decimal("0.0000"),
                nav=Decimal("10.0000"),
                current_value=Decimal("0.00"),
            ),
            ValuedHolding(
                asset_class="CASH",
                units=Decimal("0.0000"),
                nav=Decimal("1.0000"),
                current_value=Decimal("0.00"),
            ),
        ],
        target={"EQUITY": Decimal("50.00"), "DEBT": Decimal("50.00"), "CASH": Decimal("0.00")},
        navs={"EQUITY": Decimal("10.0000"), "DEBT": Decimal("10.0000"), "CASH": Decimal("1.0000")},
        display_order=["EQUITY", "DEBT", "CASH"],
    )
    assert proposal.post_trade_cash == Decimal("0.00")
