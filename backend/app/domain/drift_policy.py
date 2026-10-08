"""Holdings valuation, allocation share, drift calculation and goal progress rules.

Source of truth: specs/holdings_spec.md §2 and specs/goal_tracker_spec.md §2.
Pure domain module: Decimal only, half-even rounding, zero I/O, zero framework dependencies.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.money import q2


@dataclass(frozen=True)
class HoldingInput:
    """Raw customer holding unit count for an asset class."""

    asset_class: str
    units: Decimal


@dataclass(frozen=True)
class ValuedHolding:
    """Valued holding per asset class (units * nav)."""

    asset_class: str
    units: Decimal
    nav: Decimal
    current_value: Decimal


@dataclass(frozen=True)
class HoldingLine:
    """Line item in a customer holdings and drift report."""

    asset_class: str
    units: Decimal
    nav: Decimal
    current_value: Decimal
    current_pct: Decimal | None
    target_pct: Decimal | None
    drift_pct: Decimal | None
    breached: bool | None


@dataclass(frozen=True)
class DriftReport:
    """Overall portfolio valuation and allocation drift report."""

    total_value: Decimal
    has_target: bool
    drift_threshold_pct: Decimal | None
    portfolio_breached: bool
    lines: list[HoldingLine]


@dataclass(frozen=True)
class GoalProgressResult:
    """Calculated progress for a financial goal."""

    current_goal_value: Decimal
    percent_complete: Decimal
    status: str


def value_holdings(
    holdings: Sequence[HoldingInput],
    navs: Mapping[str, Decimal],
) -> list[ValuedHolding]:
    """Value each holding line: value = q2(units * nav)."""
    result: list[ValuedHolding] = []
    for h in holdings:
        nav = navs.get(h.asset_class, Decimal("0.0000"))
        val = q2(h.units * nav)
        result.append(
            ValuedHolding(
                asset_class=h.asset_class,
                units=h.units,
                nav=nav,
                current_value=val,
            )
        )
    return result


def current_allocation(valued: Sequence[ValuedHolding]) -> dict[str, Decimal | None]:
    """Compute current % share for each valued holding: q2(value / total * 100)."""
    total = sum((v.current_value for v in valued), Decimal("0.00"))
    if total <= Decimal("0.00"):
        return {v.asset_class: None for v in valued}

    return {v.asset_class: q2(v.current_value / total * Decimal("100")) for v in valued}


def compute_drift(
    valued: Sequence[ValuedHolding],
    target: Mapping[str, Decimal] | None,
    threshold: Decimal | None,
) -> DriftReport:
    """Calculate portfolio value, current allocation shares, and drift vs. target."""
    total_val = sum((v.current_value for v in valued), Decimal("0.00"))
    alloc_map = current_allocation(valued)

    lines: list[HoldingLine] = []
    portfolio_breached = False

    has_target = target is not None

    for v in valued:
        curr_pct = alloc_map.get(v.asset_class)

        if has_target and target is not None:
            # target percentage for class, default 0.00 if absent
            tgt_pct: Decimal | None = target.get(v.asset_class, Decimal("0.00"))
        else:
            tgt_pct = None

        if curr_pct is not None and tgt_pct is not None:
            diff: Decimal = abs(curr_pct - tgt_pct)
            drift: Decimal | None = diff
            breached: bool | None = (diff > threshold) if threshold is not None else False
        else:
            drift = None
            breached = None

        if breached is True:
            portfolio_breached = True

        lines.append(
            HoldingLine(
                asset_class=v.asset_class,
                units=v.units,
                nav=v.nav,
                current_value=v.current_value,
                current_pct=curr_pct,
                target_pct=tgt_pct,
                drift_pct=drift,
                breached=breached,
            )
        )

    return DriftReport(
        total_value=total_val,
        has_target=has_target,
        drift_threshold_pct=threshold if has_target else None,
        portfolio_breached=portfolio_breached,
        lines=lines,
    )


def calculate_goal_progress(
    total_value: Decimal,
    funding_share_pct: Decimal,
    target_amount: Decimal,
) -> GoalProgressResult:
    """Compute goal progress: current_value = total * share / 100, pct = current / target * 100."""
    current_val = q2(total_value * funding_share_pct / Decimal("100"))
    if target_amount <= Decimal("0.00"):
        percent_comp = Decimal("0.00")
    else:
        percent_comp = q2(current_val / target_amount * Decimal("100"))

    status = "ACHIEVED" if percent_comp >= Decimal("100.00") else "IN_PROGRESS"

    return GoalProgressResult(
        current_goal_value=current_val,
        percent_complete=percent_comp,
        status=status,
    )
