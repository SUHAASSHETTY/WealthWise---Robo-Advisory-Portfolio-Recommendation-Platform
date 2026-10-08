"""Integration tests for NAV feed service (admin_versioning_spec §2.6, AC-05.3, AC-08.2)."""

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.clock import AnchoredClock
from app.core.config import Settings
from app.core.db import build_engine, build_session_factory
from app.services import nav_feed_service


@pytest.fixture
def session(settings: Settings) -> Iterator[Session]:
    engine = build_engine(settings.database_url)
    factory = build_session_factory(engine)
    with factory() as sess:
        yield sess
    engine.dispose()


@pytest.mark.ac("AC-05")
@pytest.mark.ac("AC-08")
def test_ac_05_and_08_nav_feed_service_refresh(session: Session) -> None:
    """AC-05.3 & AC-08.2: Service refresh advances date and snapshots progress."""
    clock = AnchoredClock(datetime(2026, 1, 16, 18, 0, tzinfo=UTC))
    res = nav_feed_service.refresh_nav(session, clock)
    assert res["nav_date"] == "2026-01-16"
    assert res["prices_loaded"] == 4
    assert res["goals_snapshotted"] >= 3

    # Test goal_snapshot_repository queries
    from sqlalchemy import select

    from app.repositories import goal_snapshot_repository
    from app.repositories.models.goal import Goal

    first_goal = session.scalars(select(Goal)).first()
    assert first_goal is not None
    latest_snapshot = goal_snapshot_repository.get_latest_for_goal(session, first_goal.id)
    assert latest_snapshot is not None
    assert latest_snapshot.goal_id == first_goal.id

    all_snapshots = goal_snapshot_repository.list_for_goal(session, first_goal.id)
    assert len(all_snapshots) >= 1

    # Test already loaded date
    from datetime import date

    res_loaded = nav_feed_service.refresh_nav(session, clock, target_date=date(2026, 1, 16))
    assert res_loaded["status"] == "ALREADY_LOADED"


@pytest.mark.ac("AC-05")
def test_ac_05_nav_feed_exhaustion(monkeypatch: pytest.MonkeyPatch, session: Session) -> None:
    """Service raises 409 NAV_SERIES_EXHAUSTED when no further dates are available."""
    clock = AnchoredClock(datetime(2026, 1, 16, 18, 0, tzinfo=UTC))
    from app.services.errors import ServiceError

    # Mock empty series
    monkeypatch.setattr(nav_feed_service, "_load_nav_series", lambda: {})
    with pytest.raises(ServiceError) as exc_info:
        nav_feed_service.refresh_nav(session, clock)
    assert exc_info.value.status == 409
    assert exc_info.value.code == "NAV_SERIES_EXHAUSTED"

    # Mock series where all dates are in the past
    from datetime import date

    monkeypatch.setattr(
        nav_feed_service,
        "_load_nav_series",
        lambda: {date(2020, 1, 1): {"CASH": Decimal("1.0000")}},
    )
    with pytest.raises(ServiceError) as exc_info2:
        nav_feed_service.refresh_nav(session, clock)
    assert exc_info2.value.status == 409
    assert exc_info2.value.code == "NAV_SERIES_EXHAUSTED"
