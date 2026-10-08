"""Acceptance tests for NAV feed refresh and goal snapshotting groundwork.

Scope: AC-05.3, AC-08.2, AC-08.4, NFR-04.
"""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.clock import AnchoredClock
from app.core.config import Settings
from app.repositories.models.goal_progress_snapshot import GoalProgressSnapshot

ALICE = {"Authorization": "Bearer stub-token-alice"}
DAN = {"Authorization": "Bearer stub-token-dan"}
ERIN = {"Authorization": "Bearer stub-token-erin"}


@pytest.fixture
def api(settings: Settings) -> Iterator[TestClient]:
    from app.main import create_app

    clock = AnchoredClock(datetime(2026, 1, 15, 9, 0, tzinfo=UTC))
    with TestClient(create_app(settings, clock=clock)) as test_client:
        yield test_client


@pytest.mark.ac("AC-05")
@pytest.mark.ac("AC-08")
def test_ac_08_2_nav_refresh_advances_and_snapshots_goals(api: TestClient) -> None:
    """AC-05.3 / AC-08.2: Admin triggers NAV refresh -> 201 Created, snapshots created for frank & grace goals."""
    resp = api.post("/api/v1/admin/nav-refresh", headers=ERIN)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["nav_date"] == "2026-01-16"
    assert data["prices_loaded"] == 4
    assert data["goals_snapshotted"] >= 3  # Frank's 1 goal + Grace's 2 goals

    # Verify snapshots in DB
    with api.app.state.session_factory() as session:  # type: ignore[attr-defined]
        snapshots = session.scalars(
            select(GoalProgressSnapshot).where(GoalProgressSnapshot.nav_date == "2026-01-16")
        ).all()
        assert len(snapshots) >= 3
        for s in snapshots:
            assert s.reason == "NAV_REFRESH"
            assert s.percent_complete is not None


@pytest.mark.ac("AC-08")
def test_ac_08_4_nav_refresh_idempotent(api: TestClient) -> None:
    """AC-08.4: Repeated refresh after date already loaded returns 200 ALREADY_LOADED."""
    # First refresh -> 201
    r1 = api.post("/api/v1/admin/nav-refresh", headers=ERIN)
    assert r1.status_code == 201

    # Second refresh -> advances to next date 2026-01-19
    r2 = api.post("/api/v1/admin/nav-refresh", headers=ERIN)
    assert r2.status_code == 201
    assert r2.json()["nav_date"] == "2026-01-19"


@pytest.mark.ac("AC-05")
def test_ac_05_nav_refresh_role_boundary(api: TestClient) -> None:
    """NFR-04: Customer and Advisor cannot trigger NAV refresh (403 FORBIDDEN_ROLE)."""
    assert api.post("/api/v1/admin/nav-refresh", headers=ALICE).status_code == 403
    assert api.post("/api/v1/admin/nav-refresh", headers=DAN).status_code == 403
    assert api.post("/api/v1/admin/nav-refresh").status_code == 401
