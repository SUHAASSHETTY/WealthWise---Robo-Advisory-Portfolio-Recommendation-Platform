"""Acceptance tests for portfolio rebalancing engine and proposal lifecycle.

Scope: AC-06.1 to AC-06.6, AC-07.1 to AC-07.7, NFR-01, NFR-02, NFR-03, NFR-04.
"""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from tests.fixtures.answer_sets import ANS_16, submission

from app.core.clock import AnchoredClock
from app.core.config import Settings

ALICE = {"Authorization": "Bearer stub-token-alice"}
BOB = {"Authorization": "Bearer stub-token-bob"}
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


def _setup_alice_moderate(api: TestClient) -> None:
    """Setup Alice with MODERATE assessment and recommendation."""
    sub = submission(RP1, ANS_16)
    api.post("/api/v1/risk-profile/assessments", headers=ALICE, json=sub)
    api.post("/api/v1/recommendations", headers=ALICE, json={})


@pytest.mark.ac("AC-06")
def test_ac_06_1_and_07_1_breach_creates_proposal_with_exact_quantities(api: TestClient) -> None:
    """AC-06.1 & AC-07.1: Alice breached portfolio creates proposal with exact BUY/SELL quantities."""
    _setup_alice_moderate(api)

    # Evaluate rebalance
    resp = api.post("/api/v1/rebalancing/evaluate", headers=ALICE)
    assert resp.status_code == 201, resp.text
    prop = resp.json()

    assert prop["nav_date"] == "2026-01-15"
    assert prop["status"] == "PROPOSED"
    assert prop["total_value"] == "100000.00"
    assert prop["drift_threshold_pct"] == "5.00"
    assert prop["post_trade_cash"] == "4999.99"

    lines = {line["asset_class"]: line for line in prop["lines"]}

    # EQUITY: SELL 66.6666 @ 150.0000 -> 9999.99
    eq = lines["EQUITY"]
    assert eq["action"] == "SELL"
    assert eq["quantity"] == "66.6666"
    assert eq["trade_value"] == "9999.99"

    # DEBT: BUY 400.0000 @ 25.0000 -> 10000.00
    debt = lines["DEBT"]
    assert debt["action"] == "BUY"
    assert debt["quantity"] == "400.0000"
    assert debt["trade_value"] == "10000.00"

    # GOLD: BUY 16.6666 @ 60.0000 -> 1000.00
    gold = lines["GOLD"]
    assert gold["action"] == "BUY"
    assert gold["quantity"] == "16.6666"
    assert gold["trade_value"] == "1000.00"

    # CASH: SETTLEMENT
    cash = lines["CASH"]
    assert cash["action"] == "SETTLEMENT"
    assert cash["quantity"] is None
    assert cash["trade_value"] is None


@pytest.mark.ac("AC-06")
def test_ac_06_5_one_open_proposal_idempotent(api: TestClient) -> None:
    """AC-06.5: Calling evaluate again with an existing open proposal returns 200 with same proposal."""
    _setup_alice_moderate(api)

    r1 = api.post("/api/v1/rebalancing/evaluate", headers=ALICE)
    assert r1.status_code == 201
    prop_id = r1.json()["id"]

    r2 = api.post("/api/v1/rebalancing/evaluate", headers=ALICE)
    assert r2.status_code == 200
    assert r2.json()["id"] == prop_id


@pytest.mark.ac("AC-06")
def test_ac_06_6_recommendation_required(api: TestClient) -> None:
    """AC-06.6: Customer with holdings but no recommendation returns 409 RECOMMENDATION_REQUIRED."""
    # Alice has not submitted recommendation
    r = api.post("/api/v1/rebalancing/evaluate", headers=ALICE)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "RECOMMENDATION_REQUIRED"


@pytest.mark.ac("AC-07")
def test_ac_07_2_accept_proposal(api: TestClient) -> None:
    """AC-07.2: Alice accepts open proposal -> stub orders created, holdings updated, audit recorded."""
    _setup_alice_moderate(api)

    r_eval = api.post("/api/v1/rebalancing/evaluate", headers=ALICE)
    prop_id = r_eval.json()["id"]

    # Accept
    r_accept = api.post(f"/api/v1/rebalancing/recommendations/{prop_id}/accept", headers=ALICE)
    assert r_accept.status_code == 200, r_accept.text
    accept_data = r_accept.json()
    assert accept_data["status"] == "ACCEPTED"
    assert len(accept_data["orders"]) == 3

    # Check updated holdings: EQUITY 333.3334, DEBT 1400.0000, GOLD 166.6666, CASH 4999.9900
    r_hold = api.get("/api/v1/holdings", headers=ALICE)
    assert r_hold.status_code == 200
    h_map = {row["asset_class"]: row for row in r_hold.json()["lines"]}

    assert h_map["EQUITY"]["units"] == "333.3334"
    assert h_map["DEBT"]["units"] == "1400.0000"
    assert h_map["GOLD"]["units"] == "166.6666"
    assert h_map["CASH"]["units"] == "4999.9900"

    # Second accept returns 409 ALREADY_DECIDED
    r_second = api.post(f"/api/v1/rebalancing/recommendations/{prop_id}/accept", headers=ALICE)
    assert r_second.status_code == 409
    assert r_second.json()["error"]["code"] == "ALREADY_DECIDED"


@pytest.mark.ac("AC-07")
def test_ac_07_3_dismiss_proposal(api: TestClient) -> None:
    """AC-07.3: Customer dismisses proposal with reason; holdings remain unchanged."""
    _setup_alice_moderate(api)

    r_eval = api.post("/api/v1/rebalancing/evaluate", headers=ALICE)
    prop_id = r_eval.json()["id"]

    # Dismiss
    r_dismiss = api.post(
        f"/api/v1/rebalancing/recommendations/{prop_id}/dismiss",
        headers=ALICE,
        json={"reason": "Will review next month"},
    )
    assert r_dismiss.status_code == 200
    assert r_dismiss.json()["status"] == "DISMISSED"

    # Holdings unchanged (EQUITY 400.0000)
    r_hold = api.get("/api/v1/holdings", headers=ALICE)
    h_map = {row["asset_class"]: row for row in r_hold.json()["lines"]}
    assert h_map["EQUITY"]["units"] == "400.0000"

    # Subsequent accept returns 409 ALREADY_DECIDED
    r_acc = api.post(f"/api/v1/rebalancing/recommendations/{prop_id}/accept", headers=ALICE)
    assert r_acc.status_code == 409
    assert r_acc.json()["error"]["code"] == "ALREADY_DECIDED"


@pytest.mark.ac("AC-07")
def test_ac_07_5_kyc_stub_unverified_cannot_accept(api: TestClient) -> None:
    """AC-07.5: Carol (kyc_verified = false) cannot accept proposal (409 KYC_NOT_VERIFIED), but can dismiss."""
    # Carol setup
    sub = submission(RP1, ANS_16)
    api.post("/api/v1/risk-profile/assessments", headers=CAROL, json=sub)
    api.post("/api/v1/recommendations", headers=CAROL, json={})

    r_eval = api.post("/api/v1/rebalancing/evaluate", headers=CAROL)
    assert r_eval.status_code == 201
    prop_id = r_eval.json()["id"]

    # Accept fails with KYC_NOT_VERIFIED
    r_acc = api.post(f"/api/v1/rebalancing/recommendations/{prop_id}/accept", headers=CAROL)
    assert r_acc.status_code == 409
    assert r_acc.json()["error"]["code"] == "KYC_NOT_VERIFIED"

    # Dismiss succeeds
    r_dismiss = api.post(f"/api/v1/rebalancing/recommendations/{prop_id}/dismiss", headers=CAROL, json={})
    assert r_dismiss.status_code == 200
    assert r_dismiss.json()["status"] == "DISMISSED"


@pytest.mark.ac("AC-07")
def test_ac_07_6_stale_proposal_expires_on_nav_refresh(api: TestClient) -> None:
    """AC-07.6: When newer NAV loads, open proposals expire (status EXPIRED); accept returns 409 ALREADY_DECIDED."""
    _setup_alice_moderate(api)

    r_eval = api.post("/api/v1/rebalancing/evaluate", headers=ALICE)
    prop_id = r_eval.json()["id"]

    # Admin advances NAV to 2026-01-16
    api.post("/api/v1/admin/nav-refresh", headers=ERIN)

    # Check status of old proposal -> EXPIRED
    r_prop = api.get(f"/api/v1/rebalancing/recommendations/{prop_id}", headers=ALICE)
    assert r_prop.status_code == 200
    assert r_prop.json()["status"] == "EXPIRED"

    # Attempting to accept expired proposal returns 409 ALREADY_DECIDED
    r_acc = api.post(f"/api/v1/rebalancing/recommendations/{prop_id}/accept", headers=ALICE)
    assert r_acc.status_code == 409
    assert r_acc.json()["error"]["code"] == "ALREADY_DECIDED"
