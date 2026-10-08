"""Architecture tests for append-only tables (NFR-02, app_spec §5.3).

Asserts that ORM UPDATE or DELETE on any append-only table raises AppendOnlyViolation.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db import build_engine, build_session_factory
from app.repositories.errors import AppendOnlyViolation
from app.repositories.models import (
    GoalProgressSnapshot,
    RebalancingDecision,
    RebalancingLine,
    RebalancingRecommendation,
    RiskBandOverride,
    StubOrder,
)


@pytest.fixture
def session(settings: Settings) -> Session:
    engine = build_engine(settings.database_url)
    factory = build_session_factory(engine)
    sess = factory()
    yield sess
    sess.rollback()
    sess.close()
    engine.dispose()


def test_goal_progress_snapshots_is_append_only(session: Session) -> None:
    """NFR-02: UPDATE and DELETE on goal_progress_snapshots raise AppendOnlyViolation."""
    snap = GoalProgressSnapshot(
        id=str(uuid.uuid4()),
        goal_id="00000000-0000-4000-8000-0000000f0001",
        nav_date=date(2026, 1, 15),
        total_value=Decimal("100000.00"),
        funding_share_pct=Decimal("100.00"),
        current_goal_value=Decimal("100000.00"),
        percent_complete=Decimal("13.33"),
        status="IN_PROGRESS",
        reason="NAV_REFRESH",
        created_at=datetime.now(UTC),
    )
    session.add(snap)
    session.flush()

    snap.status = "ACHIEVED"
    with pytest.raises(AppendOnlyViolation):
        session.flush()

    session.rollback()

    snap = GoalProgressSnapshot(
        id=str(uuid.uuid4()),
        goal_id="00000000-0000-4000-8000-0000000f0001",
        nav_date=date(2026, 1, 15),
        total_value=Decimal("100000.00"),
        funding_share_pct=Decimal("100.00"),
        current_goal_value=Decimal("100000.00"),
        percent_complete=Decimal("13.33"),
        status="IN_PROGRESS",
        reason="NAV_REFRESH",
        created_at=datetime.now(UTC),
    )
    session.add(snap)
    session.flush()

    session.delete(snap)
    with pytest.raises(AppendOnlyViolation):
        session.flush()


def test_risk_band_overrides_is_append_only(session: Session) -> None:
    """NFR-02: UPDATE and DELETE on risk_band_overrides raise AppendOnlyViolation."""
    override = RiskBandOverride(
        id=str(uuid.uuid4()),
        customer_id="00000000-0000-4000-8000-000000000001",
        previous_band="MODERATE",
        new_band="CONSERVATIVE",
        reason_code="CLIENT_CIRCUMSTANCES_CHANGED",
        note="Client requested conservative allocation due to imminent retirement.",
        actor_user_id="00000000-0000-4000-8000-00000000a101",
        actor_role="ADVISOR",
        created_at=datetime.now(UTC),
    )
    session.add(override)
    session.flush()

    override.note = "Updated note."
    with pytest.raises(AppendOnlyViolation):
        session.flush()

    session.rollback()

    override = RiskBandOverride(
        id=str(uuid.uuid4()),
        customer_id="00000000-0000-4000-8000-000000000001",
        previous_band="MODERATE",
        new_band="CONSERVATIVE",
        reason_code="CLIENT_CIRCUMSTANCES_CHANGED",
        note="Client requested conservative allocation due to imminent retirement.",
        actor_user_id="00000000-0000-4000-8000-00000000a101",
        actor_role="ADVISOR",
        created_at=datetime.now(UTC),
    )
    session.add(override)
    session.flush()

    session.delete(override)
    with pytest.raises(AppendOnlyViolation):
        session.flush()


def test_rebalancing_recommendation_and_lines_are_append_only(session: Session) -> None:
    """NFR-02: RebalancingRecommendation and RebalancingLine are append-only."""
    rec_id = str(uuid.uuid4())
    rec = RebalancingRecommendation(
        id=rec_id,
        customer_id="00000000-0000-4000-8000-000000000001",
        based_on_recommendation_id="00000000-0000-4000-8000-000000000001",
        template_version_id="00000000-0000-4000-8000-000000000001",
        nav_date=date(2026, 1, 15),
        drift_threshold_pct=Decimal("5.00"),
        total_value=Decimal("100000.00"),
        post_trade_cash=Decimal("5000.00"),
        created_at=datetime.now(UTC),
    )
    line = RebalancingLine(
        id=str(uuid.uuid4()),
        rebalancing_recommendation_id=rec_id,
        asset_class_code="EQUITY",
        current_value=Decimal("60000.00"),
        current_pct=Decimal("60.00"),
        target_pct=Decimal("50.00"),
        drift_pct=Decimal("10.00"),
        target_value=Decimal("50000.00"),
        nav=Decimal("150.0000"),
        action="SELL",
        quantity=Decimal("66.6666"),
        trade_value=Decimal("9999.99"),
    )
    session.add(rec)
    session.add(line)
    session.flush()

    line.action = "BUY"
    with pytest.raises(AppendOnlyViolation):
        session.flush()

    session.rollback()

    rec = RebalancingRecommendation(
        id=rec_id,
        customer_id="00000000-0000-4000-8000-000000000001",
        based_on_recommendation_id="00000000-0000-4000-8000-000000000001",
        template_version_id="00000000-0000-4000-8000-000000000001",
        nav_date=date(2026, 1, 15),
        drift_threshold_pct=Decimal("5.00"),
        total_value=Decimal("100000.00"),
        post_trade_cash=Decimal("5000.00"),
        created_at=datetime.now(UTC),
    )
    session.add(rec)
    session.flush()

    session.delete(rec)
    with pytest.raises(AppendOnlyViolation):
        session.flush()


def test_rebalancing_decision_and_stub_order_are_append_only(session: Session) -> None:
    """NFR-02: RebalancingDecision and StubOrder are append-only."""
    dec = RebalancingDecision(
        id=str(uuid.uuid4()),
        rebalancing_recommendation_id=str(uuid.uuid4()),
        decision="ACCEPTED",
        actor_user_id="00000000-0000-4000-8000-000000000001",
        actor_role="CUSTOMER",
        created_at=datetime.now(UTC),
    )
    order = StubOrder(
        id=str(uuid.uuid4()),
        rebalancing_recommendation_id=dec.rebalancing_recommendation_id,
        asset_class_code="EQUITY",
        side="SELL",
        quantity=Decimal("66.6666"),
        nav=Decimal("150.0000"),
        trade_value=Decimal("9999.99"),
        status="FILLED_STUB",
        created_at=datetime.now(UTC),
    )

    session.add(dec)
    session.add(order)
    session.flush()

    dec.decision = "DISMISSED"
    with pytest.raises(AppendOnlyViolation):
        session.flush()

    session.rollback()

    dec = RebalancingDecision(
        id=str(uuid.uuid4()),
        rebalancing_recommendation_id=str(uuid.uuid4()),
        decision="ACCEPTED",
        actor_user_id="00000000-0000-4000-8000-000000000001",
        actor_role="CUSTOMER",
        created_at=datetime.now(UTC),
    )
    session.add(dec)
    session.flush()
    session.delete(dec)
    with pytest.raises(AppendOnlyViolation):
        session.flush()
