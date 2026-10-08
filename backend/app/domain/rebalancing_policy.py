"""Rebalancing math and proposal generation (rebalancing_spec §2, AC-06, AC-07)."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.drift_policy import ValuedHolding, compute_drift
from app.domain.money import q2, q4_down

Q4_UNIT = Decimal("0.0001")


class OversellError(ValueError):
    """Raised when SELL quantity exceeds held units."""


def _check_oversell(action: str, quantity: Decimal | None, units: Decimal) -> None:
    if action == "SELL" and quantity is not None and quantity > units:
        raise OversellError(f"Cannot sell {quantity} units when customer holds {units} units.")


@dataclass(frozen=True)
class RebalanceLineProposal:
    asset_class: str
    current_value: Decimal
    current_pct: Decimal | None
    target_pct: Decimal | None
    drift_pct: Decimal | None
    target_value: Decimal | None
    nav: Decimal
    action: str  # BUY | SELL | NONE | SETTLEMENT
    quantity: Decimal | None
    trade_value: Decimal | None


@dataclass(frozen=True)
class RebalanceProposal:
    total_value: Decimal
    post_trade_cash: Decimal
    lines: Sequence[RebalanceLineProposal]


@dataclass
class _WorkingLine:
    asset_class: str
    current_value: Decimal
    current_pct: Decimal | None
    target_pct: Decimal | None
    drift_pct: Decimal | None
    target_value: Decimal
    nav: Decimal
    action: str
    quantity: Decimal
    trade_value: Decimal
    units: Decimal


def propose_rebalance(
    valued: Sequence[ValuedHolding],
    target: Mapping[str, Decimal],
    navs: Mapping[str, Decimal],
    display_order: Sequence[str],
    settlement_class: str = "CASH",
) -> RebalanceProposal:
    """Calculate BUY/SELL quantities per asset class to realign portfolio with target allocation."""
    valued_map = {v.asset_class: v for v in valued}
    total_value = sum((v.current_value for v in valued), Decimal("0.00"))

    drift_report = compute_drift(valued, target=target, threshold=None)
    drift_lines_by_class = {line.asset_class: line for line in drift_report.lines}

    # Step 1: Initial trade computation for non-settlement classes
    working_lines: dict[str, _WorkingLine] = {}

    for code in display_order:
        if code == settlement_class:
            continue

        v = valued_map.get(code)
        curr_val = v.current_value if v else Decimal("0.00")
        held_units = v.units if v else Decimal("0.0000")
        nav_val = navs.get(code, Decimal("1.0000"))
        tgt_pct = target.get(code, Decimal("0.00"))

        target_value = q2(total_value * tgt_pct / Decimal("100"))
        delta = target_value - curr_val

        quantity = Decimal("0.0000") if nav_val <= Decimal("0.0000") else q4_down(abs(delta) / nav_val)

        if delta > Decimal("0.00") and quantity > Decimal("0.0000"):
            action = "BUY"
        elif delta < Decimal("0.00") and quantity > Decimal("0.0000"):
            action = "SELL"
        else:
            action = "NONE"
            quantity = Decimal("0.0000")

        _check_oversell(action, quantity, held_units)
        trade_val = q2(quantity * nav_val)

        d_line = drift_lines_by_class.get(code)
        working_lines[code] = _WorkingLine(
            asset_class=code,
            current_value=curr_val,
            current_pct=d_line.current_pct if d_line else None,
            target_pct=d_line.target_pct if d_line else None,
            drift_pct=d_line.drift_pct if d_line else None,
            target_value=target_value,
            nav=nav_val,
            action=action,
            quantity=quantity,
            trade_value=trade_val,
            units=held_units,
        )

    # Step 2: Calculate CASH change and post_trade_cash
    cash_val = valued_map.get(settlement_class)
    curr_cash = cash_val.current_value if cash_val else Decimal("0.00")

    def calc_cash() -> tuple[Decimal, Decimal]:
        sell_sum = sum(
            (line.trade_value for line in working_lines.values() if line.action == "SELL"),
            Decimal("0.00"),
        )
        buy_sum = sum(
            (line.trade_value for line in working_lines.values() if line.action == "BUY"),
            Decimal("0.00"),
        )
        change = sell_sum - buy_sum
        return change, curr_cash + change

    cash_change, post_trade_cash = calc_cash()

    # Step 3: Negative cash guard
    # If post_trade_cash < 0, reduce largest BUY line by 0.0001 units
    while post_trade_cash < Decimal("0.00"):
        buy_lines = [
            buy_item
            for buy_item in working_lines.values()
            if buy_item.action == "BUY" and buy_item.quantity > Decimal("0.0000")
        ]
        if not buy_lines:
            break

        # Max trade_value, tie-breaker: lowest display_order index
        buy_lines.sort(
            key=lambda item: (
                item.trade_value,
                -display_order.index(item.asset_class),
            ),
            reverse=True,
        )
        target_buy = buy_lines[0]
        qty = target_buy.quantity - Q4_UNIT
        nav = target_buy.nav
        if qty <= Decimal("0.0000"):
            target_buy.quantity = Decimal("0.0000")
            target_buy.action = "NONE"
            target_buy.trade_value = Decimal("0.00")
        else:
            target_buy.quantity = qty
            target_buy.trade_value = q2(qty * nav)

        cash_change, post_trade_cash = calc_cash()

    # Step 4: Build final proposal lines following display_order
    final_lines: list[RebalanceLineProposal] = []
    for code in display_order:
        if code == settlement_class:
            d_line = drift_lines_by_class.get(code)
            cash_h = valued_map.get(settlement_class)
            final_lines.append(
                RebalanceLineProposal(
                    asset_class=settlement_class,
                    current_value=cash_h.current_value if cash_h else Decimal("0.00"),
                    current_pct=d_line.current_pct if d_line else None,
                    target_pct=d_line.target_pct if d_line else None,
                    drift_pct=d_line.drift_pct if d_line else None,
                    target_value=None,
                    nav=navs.get(settlement_class, Decimal("1.0000")),
                    action="SETTLEMENT",
                    quantity=None,
                    trade_value=None,
                )
            )
        else:
            wl = working_lines[code]
            final_lines.append(
                RebalanceLineProposal(
                    asset_class=code,
                    current_value=wl.current_value,
                    current_pct=wl.current_pct,
                    target_pct=wl.target_pct,
                    drift_pct=wl.drift_pct,
                    target_value=wl.target_value,
                    nav=wl.nav,
                    action=wl.action,
                    quantity=wl.quantity if wl.action != "NONE" else Decimal("0.0000"),
                    trade_value=wl.trade_value if wl.action != "NONE" else Decimal("0.00"),
                )
            )

    return RebalanceProposal(
        total_value=total_value,
        post_trade_cash=post_trade_cash,
        lines=final_lines,
    )
