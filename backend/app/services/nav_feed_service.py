"""NAV feed refresh and goal progress snapshotting (admin_versioning_spec §2.6, goal_tracker_spec §2.3)."""

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.domain.drift_policy import HoldingInput, calculate_goal_progress, value_holdings
from app.repositories import (
    audit_repository,
    customer_repository,
    goal_snapshot_repository,
    holding_repository,
    nav_repository,
    rebalancing_repository,
)
from app.repositories.models.goal import Goal
from app.repositories.models.goal_progress_snapshot import GoalProgressSnapshot
from app.repositories.models.nav_price import NavPrice
from app.services import rebalancing_service
from app.services.errors import ServiceError

NAV_SERIES_PATH = Path(__file__).resolve().parents[1] / "seed" / "nav_series.csv"


def _load_nav_series() -> dict[date, dict[str, Decimal]]:
    """Parse nav_series.csv into date -> {asset_class: nav}."""
    series: dict[date, dict[str, Decimal]] = {}
    if not NAV_SERIES_PATH.exists():
        return series

    with NAV_SERIES_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = date.fromisoformat(row["nav_date"].strip())
            c = row["asset_class_code"].strip()
            v = Decimal(row["nav"].strip())
            if d not in series:
                series[d] = {}
            series[d][c] = v
    return series


def refresh_nav(session: Session, clock: Clock, target_date: date | None = None) -> dict[str, Any]:
    """Advance NAV prices to next date, snapshot goal progress, auto-evaluate rebalancing (AC-06, AC-08, AC-10)."""
    series = _load_nav_series()
    if not series:
        raise ServiceError(409, "NAV_SERIES_EXHAUSTED", "No NAV series data available.")

    if target_date is not None:
        if target_date not in series:
            raise ServiceError(409, "NAV_SERIES_EXHAUSTED", f"Target date {target_date} not in NAV series.")
        next_date = target_date
    else:
        latest_loaded_date = nav_repository.get_latest_nav_date(session)
        available_dates = sorted(d for d in series if latest_loaded_date is None or d > latest_loaded_date)
        if not available_dates:
            raise ServiceError(409, "NAV_SERIES_EXHAUSTED", "No further dates available in NAV series.")
        next_date = available_dates[0]

    if nav_repository.has_date(session, next_date):
        return {"status": "ALREADY_LOADED", "nav_date": str(next_date)}

    now = clock.now()

    # Expire any currently open proposals before advancing date
    rebalancing_repository.expire_all_open_proposals(session, now)

    prices_map = dict(series[next_date])
    if "CASH" not in prices_map:
        prices_map["CASH"] = Decimal("1.0000")

    nav_price_rows = [
        NavPrice(
            asset_class_code=code,
            nav_date=next_date,
            nav=price,
            created_at=now,
        )
        for code, price in prices_map.items()
    ]
    nav_repository.add_nav_prices(session, nav_price_rows)

    # AC-08: snapshot progress for all customer goals
    active_classes = customer_repository.active_asset_class_codes(session)
    goals = session.scalars(select(Goal)).all()
    goals_by_customer: dict[str, list[Goal]] = {}
    for g in goals:
        goals_by_customer.setdefault(g.customer_id, []).append(g)

    snapshots: list[GoalProgressSnapshot] = []
    for customer_id, cust_goals in goals_by_customer.items():
        holdings_map = {h.asset_class_code: h.units for h in holding_repository.list_for_customer(session, customer_id)}
        holding_inputs = [
            HoldingInput(asset_class=code, units=holdings_map.get(code, Decimal("0.0000"))) for code in active_classes
        ]
        valued_holdings = value_holdings(holding_inputs, prices_map)
        total_val = sum((v.current_value for v in valued_holdings), Decimal("0.00"))

        for goal in cust_goals:
            res = calculate_goal_progress(
                total_value=total_val,
                funding_share_pct=goal.funding_share_pct,
                target_amount=goal.target_amount,
            )
            snapshots.append(
                GoalProgressSnapshot(
                    goal_id=goal.id,
                    nav_date=next_date,
                    total_value=total_val,
                    funding_share_pct=goal.funding_share_pct,
                    current_goal_value=res.current_goal_value,
                    percent_complete=res.percent_complete,
                    status=res.status,
                    reason="NAV_REFRESH",
                    created_at=now,
                )
            )

    if snapshots:
        goal_snapshot_repository.add_snapshots(session, snapshots)

    # AC-06.4: Auto-evaluate rebalancing for all customers
    all_customers = customer_repository.list_all_customers(session)
    rebalances_proposed = 0
    for cust in all_customers:
        try:
            eval_res = rebalancing_service.evaluate_customer_rebalancing(session, clock, cust.id)
            if eval_res.created:
                rebalances_proposed += 1
        except Exception:
            pass

    audit_repository.insert_audit_event(
        session,
        actor_user_id=None,
        actor_role="ADMIN",
        action="NAV_REFRESHED",
        entity_type="nav_prices",
        entity_id=str(next_date),
        details={
            "nav_date": str(next_date),
            "prices_loaded": len(nav_price_rows),
            "goals_snapshotted": len(snapshots),
            "rebalances_proposed": rebalances_proposed,
        },
    )
    session.commit()

    return {
        "nav_date": str(next_date),
        "prices_loaded": len(nav_price_rows),
        "goals_snapshotted": len(snapshots),
        "rebalances_proposed": rebalances_proposed,
    }
