"""Acceptance tests for financial goals CRUD and progress tracking.

Scope: AC-03.1 to AC-03.5, AC-08.1 to AC-08.5, NFR-01, NFR-02, NFR-03, NFR-04.
"""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.core.clock import AnchoredClock
from app.core.config import Settings

ALICE = {"Authorization": "Bearer stub-token-alice"}
BOB = {"Authorization": "Bearer stub-token-bob"}
DAN = {"Authorization": "Bearer stub-token-dan"}
ERIN = {"Authorization": "Bearer stub-token-erin"}


@pytest.fixture
def api(settings: Settings) -> Iterator[TestClient]:
    from app.main import create_app

    clock = AnchoredClock(datetime(2026, 1, 15, 9, 0, tzinfo=UTC))
    with TestClient(create_app(settings, clock=clock)) as test_client:
        yield test_client


@pytest.mark.ac("AC-03")
def test_ac_03_1_create_goal_with_progress(api: TestClient) -> None:
    """AC-03.1: Alice creates Daughter's university goal and receives 201 with progress block."""
    resp = api.post(
        "/api/v1/goals",
        headers=ALICE,
        json={
            "name": "Daughter's university",
            "goal_type": "EDUCATION",
            "target_amount": "50000.00",
            "target_date": "2032-08-31",
            "priority": 1,
            "funding_share_pct": "40.00",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == "Daughter's university"
    assert data["goal_type"] == "EDUCATION"
    assert data["target_amount"] == "50000.00"
    assert data["target_date"] == "2032-08-31"
    assert data["priority"] == 1
    assert data["funding_share_pct"] == "40.00"
    assert data["progress"] is not None
    assert data["progress"]["nav_date"] == "2026-01-15"
    assert data["progress"]["current_goal_value"] == "40000.00"
    assert data["progress"]["percent_complete"] == "80.00"
    assert data["progress"]["status"] == "IN_PROGRESS"


@pytest.mark.ac("AC-03")
def test_ac_03_2_multiple_goals_ordering(api: TestClient) -> None:
    """AC-03.2: Alice creates multiple goals; GET /goals returns them in priority order."""
    # Goal 2: Retirement (priority 2)
    resp2 = api.post(
        "/api/v1/goals",
        headers=ALICE,
        json={
            "name": "Retirement corpus",
            "goal_type": "RETIREMENT",
            "target_amount": "500000.00",
            "target_date": "2050-03-31",
            "priority": 2,
            "funding_share_pct": "60.00",
        },
    )
    assert resp2.status_code == 201

    # Goal 1: University (priority 1)
    resp1 = api.post(
        "/api/v1/goals",
        headers=ALICE,
        json={
            "name": "Daughter's university",
            "goal_type": "EDUCATION",
            "target_amount": "50000.00",
            "target_date": "2032-08-31",
            "priority": 1,
            "funding_share_pct": "40.00",
        },
    )
    assert resp1.status_code == 201

    list_resp = api.get("/api/v1/goals", headers=ALICE)
    assert list_resp.status_code == 200
    goals = list_resp.json()
    assert len(goals) == 2
    assert goals[0]["name"] == "Daughter's university"
    assert goals[0]["priority"] == 1
    assert goals[1]["name"] == "Retirement corpus"
    assert goals[1]["priority"] == 2


@pytest.mark.ac("AC-03")
def test_ac_03_3_validation_errors(api: TestClient) -> None:
    """AC-03.3: Target date, target amount, priority, and funding share validations."""
    # Target date not in future
    r = api.post(
        "/api/v1/goals",
        headers=ALICE,
        json={
            "name": "Past goal",
            "goal_type": "OTHER",
            "target_amount": "1000.00",
            "target_date": "2026-01-15",
            "priority": 1,
            "funding_share_pct": "10.00",
        },
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "TARGET_DATE_NOT_FUTURE"

    # Target amount <= 0.00
    r = api.post(
        "/api/v1/goals",
        headers=ALICE,
        json={
            "name": "Zero amount",
            "goal_type": "OTHER",
            "target_amount": "0.00",
            "target_date": "2030-01-01",
            "priority": 1,
            "funding_share_pct": "10.00",
        },
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "TARGET_AMOUNT_INVALID"

    # Priority invalid (>5)
    r = api.post(
        "/api/v1/goals",
        headers=ALICE,
        json={
            "name": "Bad priority",
            "goal_type": "OTHER",
            "target_amount": "1000.00",
            "target_date": "2030-01-01",
            "priority": 6,
            "funding_share_pct": "10.00",
        },
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "PRIORITY_INVALID"


@pytest.mark.ac("AC-03")
def test_ac_03_4_funding_share_cap(api: TestClient) -> None:
    """AC-03.4: Total funding share cannot exceed 100.00%."""
    api.post(
        "/api/v1/goals",
        headers=ALICE,
        json={
            "name": "G1",
            "goal_type": "RETIREMENT",
            "target_amount": "100000.00",
            "target_date": "2040-01-01",
            "priority": 1,
            "funding_share_pct": "60.00",
        },
    )
    api.post(
        "/api/v1/goals",
        headers=ALICE,
        json={
            "name": "G2",
            "goal_type": "EDUCATION",
            "target_amount": "50000.00",
            "target_date": "2035-01-01",
            "priority": 2,
            "funding_share_pct": "40.00",
        },
    )
    # Adding 0.01% exceeds 100.00%
    r = api.post(
        "/api/v1/goals",
        headers=ALICE,
        json={
            "name": "G3",
            "goal_type": "OTHER",
            "target_amount": "10000.00",
            "target_date": "2035-01-01",
            "priority": 3,
            "funding_share_pct": "0.01",
        },
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "FUNDING_SHARE_EXCEEDS_100"

    # Share of 0.00% succeeds
    r_zero = api.post(
        "/api/v1/goals",
        headers=ALICE,
        json={
            "name": "G3",
            "goal_type": "OTHER",
            "target_amount": "10000.00",
            "target_date": "2035-01-01",
            "priority": 3,
            "funding_share_pct": "0.00",
        },
    )
    assert r_zero.status_code == 201


@pytest.mark.ac("AC-03")
def test_ac_03_5_customer_isolation(api: TestClient) -> None:
    """AC-03.5: Bob cannot view or update Alice's goal (returns 404)."""
    r = api.post(
        "/api/v1/goals",
        headers=ALICE,
        json={
            "name": "Alice Goal",
            "goal_type": "HOME",
            "target_amount": "50000.00",
            "target_date": "2032-01-01",
            "priority": 1,
            "funding_share_pct": "50.00",
        },
    )
    goal_id = r.json()["id"]

    # Bob requests Alice's goal
    get_r = api.get(f"/api/v1/goals/{goal_id}", headers=BOB)
    assert get_r.status_code == 404

    # Bob updates Alice's goal
    put_r = api.put(
        f"/api/v1/goals/{goal_id}",
        headers=BOB,
        json={
            "name": "Hacked Goal",
            "goal_type": "HOME",
            "target_amount": "50000.00",
            "target_date": "2032-01-01",
            "priority": 1,
            "funding_share_pct": "50.00",
        },
    )
    assert put_r.status_code == 404


@pytest.mark.ac("AC-08")
def test_ac_08_1_and_08_2_worked_example_and_nav_refresh(api: TestClient) -> None:
    """AC-08.1 & AC-08.2: Progress formula and update upon daily NAV refresh."""
    # Create Retirement and University goals for Alice (total_value = 100,000.00)
    r_ret = api.post(
        "/api/v1/goals",
        headers=ALICE,
        json={
            "name": "Retirement corpus",
            "goal_type": "RETIREMENT",
            "target_amount": "500000.00",
            "target_date": "2050-03-31",
            "priority": 2,
            "funding_share_pct": "60.00",
        },
    )
    ret_id = r_ret.json()["id"]
    assert r_ret.json()["progress"]["current_goal_value"] == "60000.00"
    assert r_ret.json()["progress"]["percent_complete"] == "12.00"

    r_uni = api.post(
        "/api/v1/goals",
        headers=ALICE,
        json={
            "name": "Daughter's university",
            "goal_type": "EDUCATION",
            "target_amount": "50000.00",
            "target_date": "2032-08-31",
            "priority": 1,
            "funding_share_pct": "40.00",
        },
    )
    assert r_uni.json()["progress"]["current_goal_value"] == "40000.00"
    assert r_uni.json()["progress"]["percent_complete"] == "80.00"

    # Admin triggers NAV refresh -> advances to 2026-01-16 (total_value = 106,000.00)
    refresh_r = api.post("/api/v1/admin/nav-refresh", headers=ERIN)
    assert refresh_r.status_code == 201

    # Fetch updated goals
    goals = api.get("/api/v1/goals", headers=ALICE).json()
    goals_by_name = {g["name"]: g for g in goals}

    ret = goals_by_name["Retirement corpus"]
    assert ret["progress"]["nav_date"] == "2026-01-16"
    assert ret["progress"]["current_goal_value"] == "63600.00"
    assert ret["progress"]["percent_complete"] == "12.72"

    uni = goals_by_name["Daughter's university"]
    assert uni["progress"]["nav_date"] == "2026-01-16"
    assert uni["progress"]["current_goal_value"] == "42400.00"
    assert uni["progress"]["percent_complete"] == "84.80"

    # Check progress snapshot history
    prog_r = api.get(f"/api/v1/goals/{ret_id}/progress", headers=ALICE)
    assert prog_r.status_code == 200
    prog_data = prog_r.json()
    assert len(prog_data["history"]) >= 2
    assert prog_data["latest"]["nav_date"] == "2026-01-16"


@pytest.mark.ac("AC-08")
def test_ac_08_3_achieved_status(api: TestClient) -> None:
    """AC-08.3: When percent_complete >= 100.00%, status becomes ACHIEVED without being capped."""
    r = api.post(
        "/api/v1/goals",
        headers=ALICE,
        json={
            "name": "Small goal",
            "goal_type": "OTHER",
            "target_amount": "30000.00",
            "target_date": "2030-01-01",
            "priority": 1,
            "funding_share_pct": "40.00",
        },
    )
    assert r.status_code == 201
    prog = r.json()["progress"]
    assert prog["current_goal_value"] == "40000.00"
    assert prog["percent_complete"] == "133.33"
    assert prog["status"] == "ACHIEVED"
