"""Acceptance tests for customer holdings and drift calculation.

Scope: AC-05.1 to AC-05.7, NFR-01, NFR-03, NFR-04.
"""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from tests.fixtures.answer_sets import ANS_16, submission

from app.core.clock import AnchoredClock
from app.core.config import Settings

ALICE = {"Authorization": "Bearer stub-token-alice"}
CAROL = {"Authorization": "Bearer stub-token-carol"}
DAN = {"Authorization": "Bearer stub-token-dan"}
ERIN = {"Authorization": "Bearer stub-token-erin"}
RP1 = "00000000-0000-4000-8000-000000000201"


@pytest.fixture
def api(settings: Settings) -> Iterator[TestClient]:
    from app.main import create_app

    clock = AnchoredClock(datetime(2026, 1, 15, 9, 0, tzinfo=UTC))
    with TestClient(create_app(settings, clock=clock)) as test_client:
        yield test_client


@pytest.mark.ac("AC-05")
def test_ac_05_1_and_05_2_alice_holdings_and_drift(api: TestClient) -> None:
    """AC-05.1 & AC-05.2: Alice initial holdings valued at 2026-01-15 NAVs with MODERATE recommendation."""
    # Alice completes risk assessment -> MODERATE
    sub = submission(RP1, ANS_16)
    assert api.post("/api/v1/risk-profile/assessments", headers=ALICE, json=sub).status_code == 201
    # Alice generates recommendation
    assert api.post("/api/v1/recommendations", headers=ALICE, json={}).status_code == 201

    # Fetch holdings
    resp = api.get("/api/v1/holdings", headers=ALICE)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["nav_date"] == "2026-01-15"
    assert data["total_value"] == "100000.00"
    assert data["has_target"] is True
    assert data["template_version_no"] == 1
    assert data["drift_threshold_pct"] == "5.00"
    assert data["portfolio_breached"] is True

    line_map = {line["asset_class"]: line for line in data["lines"]}

    # EQUITY: 400 * 150 = 60000.00 (60.00% vs 50.00% target -> 10.00% drift, breached)
    eq = line_map["EQUITY"]
    assert eq["units"] == "400.0000"
    assert eq["nav"] == "150.0000"
    assert eq["current_value"] == "60000.00"
    assert eq["current_pct"] == "60.00"
    assert eq["target_pct"] == "50.00"
    assert eq["drift_pct"] == "10.00"
    assert eq["breached"] is True

    # DEBT: 1000 * 25 = 25000.00 (25.00% vs 35.00% target -> 10.00% drift, breached)
    debt = line_map["DEBT"]
    assert debt["units"] == "1000.0000"
    assert debt["nav"] == "25.0000"
    assert debt["current_value"] == "25000.00"
    assert debt["current_pct"] == "25.00"
    assert debt["target_pct"] == "35.00"
    assert debt["drift_pct"] == "10.00"
    assert debt["breached"] is True

    # GOLD: 150 * 60 = 9000.00 (9.00% vs 10.00% target -> 1.00% drift, not breached)
    gold = line_map["GOLD"]
    assert gold["units"] == "150.0000"
    assert gold["nav"] == "60.0000"
    assert gold["current_value"] == "9000.00"
    assert gold["current_pct"] == "9.00"
    assert gold["target_pct"] == "10.00"
    assert gold["drift_pct"] == "1.00"
    assert gold["breached"] is False

    # CASH: 6000 * 1 = 6000.00 (6.00% vs 5.00% target -> 1.00% drift, not breached)
    cash = line_map["CASH"]
    assert cash["units"] == "6000.0000"
    assert cash["nav"] == "1.0000"
    assert cash["current_value"] == "6000.00"
    assert cash["current_pct"] == "6.00"
    assert cash["target_pct"] == "5.00"
    assert cash["drift_pct"] == "1.00"
    assert cash["breached"] is False


@pytest.mark.ac("AC-05")
def test_ac_05_3_holdings_value_follows_nav_refresh(api: TestClient) -> None:
    """AC-05.3: NAV refresh with EQUITY at 165.0000 -> total 106000.00, equity % 62.26, drift 12.26."""
    sub = submission(RP1, ANS_16)
    assert api.post("/api/v1/risk-profile/assessments", headers=ALICE, json=sub).status_code == 201
    assert api.post("/api/v1/recommendations", headers=ALICE, json={}).status_code == 201

    # Admin refreshes NAVs -> advances to 2026-01-16 (EQUITY 165.0000)
    refresh_resp = api.post("/api/v1/admin/nav-refresh", headers=ERIN)
    assert refresh_resp.status_code == 201
    assert refresh_resp.json()["nav_date"] == "2026-01-16"

    # Alice fetches holdings again
    resp = api.get("/api/v1/holdings", headers=ALICE)
    assert resp.status_code == 200
    data = resp.json()

    assert data["nav_date"] == "2026-01-16"
    assert data["total_value"] == "106000.00"

    eq = next(line for line in data["lines"] if line["asset_class"] == "EQUITY")
    assert eq["nav"] == "165.0000"
    assert eq["current_value"] == "66000.00"
    assert eq["current_pct"] == "62.26"
    assert eq["drift_pct"] == "12.26"
    assert eq["breached"] is True


@pytest.mark.ac("AC-05")
def test_ac_05_5_customer_without_recommendation(api: TestClient) -> None:
    """AC-05.5: Carol has holdings but no recommendation -> has_target=false, null target & drift."""
    resp = api.get("/api/v1/holdings", headers=CAROL)
    assert resp.status_code == 200
    data = resp.json()

    assert data["has_target"] is False
    assert data["recommendation_id"] is None
    assert data["template_version_no"] is None
    assert data["drift_threshold_pct"] is None
    assert data["portfolio_breached"] is False

    for line in data["lines"]:
        assert line["target_pct"] is None
        assert line["drift_pct"] is None
        assert line["breached"] is None


@pytest.mark.ac("AC-05")
def test_ac_05_6_threshold_source_pinned_to_recommendation_template_version(api: TestClient) -> None:
    """AC-05.6: Alice recommended under v1 (5.00); admin publishes v2 (3.00) -> holdings still uses 5.00."""
    sub = submission(RP1, ANS_16)
    assert api.post("/api/v1/risk-profile/assessments", headers=ALICE, json=sub).status_code == 201
    assert api.post("/api/v1/recommendations", headers=ALICE, json={}).status_code == 201

    # Admin publishes template v2 with threshold 3.00
    draft = api.post("/api/v1/admin/template-versions/drafts", headers=ERIN).json()
    draft_id = draft["id"]
    draft_def = draft["definition"]
    draft_def["drift_threshold_pct"] = "3.00"
    put_resp = api.put(
        f"/api/v1/admin/template-versions/{draft_id}",
        headers=ERIN,
        json={"definition": draft_def},
    )
    assert put_resp.status_code == 200
    assert api.post(f"/api/v1/admin/template-versions/{draft_id}/publish", headers=ERIN).status_code == 200

    # Alice's holdings must still reflect template v1 with threshold 5.00
    resp = api.get("/api/v1/holdings", headers=ALICE)
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_version_no"] == 1
    assert data["drift_threshold_pct"] == "5.00"


@pytest.mark.ac("AC-05")
def test_ac_05_7_role_boundary_and_json_decimal_types(api: TestClient) -> None:
    """NFR-04: Non-customers rejected with 403; NFR-01: All numbers in JSON response are strings."""
    # Advisor rejected
    assert api.get("/api/v1/holdings", headers=DAN).status_code == 403
    # Unauthenticated rejected
    assert api.get("/api/v1/holdings").status_code == 401

    # Check decimal strings in JSON
    resp = api.get("/api/v1/holdings", headers=ALICE)
    raw = resp.json()
    assert isinstance(raw["total_value"], str)
    for line in raw["lines"]:
        assert isinstance(line["units"], str)
        assert isinstance(line["nav"], str)
        assert isinstance(line["current_value"], str)
        if line["current_pct"] is not None:
            assert isinstance(line["current_pct"], str)
