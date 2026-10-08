"""AC-09 — Advisor workbench acceptance tests (advisor_workbench_spec §2, §4, §5)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from tests.fixtures.answer_sets import ANS_16, ANS_20, submission

from app.core.clock import AnchoredClock
from app.core.config import Settings
from app.repositories.guards import AppendOnlyViolation
from app.repositories.models import RiskBandOverride

ALICE_ID = "00000000-0000-4000-8000-00000000c001"
BOB_ID = "00000000-0000-4000-8000-00000000c002"
DAN_USER_ID = "00000000-0000-4000-8000-00000000a101"
RP1 = "00000000-0000-4000-8000-000000000201"

DAN = {"Authorization": "Bearer stub-token-dan"}
ALICE = {"Authorization": "Bearer stub-token-alice"}
BOB = {"Authorization": "Bearer stub-token-bob"}
ADMIN = {"Authorization": "Bearer stub-token-erin"}


@pytest.fixture
def api(settings: Settings) -> Iterator[TestClient]:
    from app.main import create_app

    clock = AnchoredClock(datetime(2026, 1, 20, 10, 0, 0, tzinfo=UTC))
    with TestClient(create_app(settings, clock=clock)) as test_client:
        yield test_client


@pytest.mark.ac("AC-09")
def test_ac_09_1_advisor_override_changes_effective_band(api: TestClient) -> None:
    """AC-09.1 — Dan overrides Bob's band from MODERATE to CONSERVATIVE.

    Returns 201 with actor/timestamp; Bob's GET /risk-profile reflects CONSERVATIVE / ADVISOR_OVERRIDE.
    """
    # Bob takes questionnaire -> MODERATE
    assess_res = api.post("/api/v1/risk-profile/assessments", headers=BOB, json=submission(RP1, ANS_20))
    assert assess_res.status_code == 201
    assert assess_res.json()["assigned_band"] == "MODERATE"

    # Dan overrides Bob's band
    override_payload = {
        "new_band": "CONSERVATIVE",
        "reason_code": "CLIENT_CIRCUMSTANCES_CHANGED",
        "note": "Client retiring in 18 months; needs capital stability.",
    }
    res = api.post(f"/api/v1/advisor/customers/{BOB_ID}/risk-overrides", headers=DAN, json=override_payload)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["previous_band"] == "MODERATE"
    assert body["new_band"] == "CONSERVATIVE"
    assert body["reason_code"] == "CLIENT_CIRCUMSTANCES_CHANGED"
    assert body["actor_user_id"] == DAN_USER_ID
    assert "2026-01-20" in body["created_at"]

    # Bob's profile view
    profile_res = api.get("/api/v1/risk-profile", headers=BOB)
    assert profile_res.status_code == 200
    profile_body = profile_res.json()
    assert profile_body["risk_band"] == "CONSERVATIVE"
    assert profile_body["source"] == "ADVISOR_OVERRIDE"
    assert "note" not in profile_body  # note is not visible to customer


@pytest.mark.ac("AC-09")
def test_ac_09_2_override_creates_audit_record_without_note_in_details(api: TestClient) -> None:
    """AC-09.2 — Audit trail includes RISK_BAND_OVERRIDDEN with Dan's user ID and entity ID, no note in details."""
    api.post("/api/v1/risk-profile/assessments", headers=BOB, json=submission(RP1, ANS_20))

    override_res = api.post(
        f"/api/v1/advisor/customers/{BOB_ID}/risk-overrides",
        headers=DAN,
        json={
            "new_band": "CONSERVATIVE",
            "reason_code": "CLIENT_CIRCUMSTANCES_CHANGED",
            "note": "Client retiring in 18 months; needs capital stability.",
        },
    )
    override_id = override_res.json()["override_id"]

    audit_res = api.get(f"/api/v1/advisor/customers/{BOB_ID}/audit", headers=DAN)
    assert audit_res.status_code == 200
    audit_events = audit_res.json()

    override_events = [e for e in audit_events if e["action"] == "RISK_BAND_OVERRIDDEN"]
    assert len(override_events) == 1
    event = override_events[0]
    assert event["actor_role"] == "ADVISOR"
    assert event["actor_user_id"] == DAN_USER_ID
    assert event["entity_id"] == override_id
    assert "note" not in event.get("details", {})
    assert "Client retiring" not in str(event.get("details", {}))


@pytest.mark.ac("AC-09")
def test_ac_09_3_reason_and_note_validation(api: TestClient) -> None:
    """AC-09.3 — Missing reason_code -> 422; short note -> 422; no override created."""
    api.post("/api/v1/risk-profile/assessments", headers=BOB, json=submission(RP1, ANS_20))

    # Invalid reason code
    bad_reason = api.post(
        f"/api/v1/advisor/customers/{BOB_ID}/risk-overrides",
        headers=DAN,
        json={
            "new_band": "CONSERVATIVE",
            "reason_code": "INVALID_REASON",
            "note": "Client retiring in 18 months; needs capital stability.",
        },
    )
    assert bad_reason.status_code == 422
    assert bad_reason.json()["error"]["code"] == "REASON_CODE_INVALID"

    # Short note (12 chars)
    short_note = api.post(
        f"/api/v1/advisor/customers/{BOB_ID}/risk-overrides",
        headers=DAN,
        json={
            "new_band": "CONSERVATIVE",
            "reason_code": "CLIENT_CIRCUMSTANCES_CHANGED",
            "note": "Client asked",
        },
    )
    assert short_note.status_code == 422
    assert short_note.json()["error"]["code"] == "OVERRIDE_NOTE_INVALID"

    # Effective band remains MODERATE
    profile = api.get("/api/v1/risk-profile", headers=BOB).json()
    assert profile["risk_band"] == "MODERATE"


@pytest.mark.ac("AC-09")
def test_ac_09_4_same_band_rejected(api: TestClient) -> None:
    """AC-09.4 — Overriding to the same effective band returns 422 OVERRIDE_SAME_BAND."""
    api.post("/api/v1/risk-profile/assessments", headers=BOB, json=submission(RP1, ANS_20))

    same_band = api.post(
        f"/api/v1/advisor/customers/{BOB_ID}/risk-overrides",
        headers=DAN,
        json={
            "new_band": "MODERATE",
            "reason_code": "SUITABILITY_REVIEW",
            "note": "Re-affirming existing moderate risk profile with client.",
        },
    )
    assert same_band.status_code == 422
    assert same_band.json()["error"]["code"] == "OVERRIDE_SAME_BAND"


@pytest.mark.ac("AC-09")
def test_ac_09_5_history_preserved_and_append_only(api: TestClient) -> None:
    """AC-09.5 — History contains assessment + override; risk_band_overrides is append-only."""
    api.post("/api/v1/risk-profile/assessments", headers=BOB, json=submission(RP1, ANS_20))
    api.post(
        f"/api/v1/advisor/customers/{BOB_ID}/risk-overrides",
        headers=DAN,
        json={
            "new_band": "CONSERVATIVE",
            "reason_code": "CLIENT_CIRCUMSTANCES_CHANGED",
            "note": "Client retiring in 18 months; needs capital stability.",
        },
    )

    history = api.get("/api/v1/risk-profile/history", headers=BOB).json()
    assert len(history) == 2
    # newest first
    assert history[0]["band"] == "CONSERVATIVE"
    assert history[0]["type"] == "ADVISOR_OVERRIDE"
    assert history[0]["reason_code"] == "CLIENT_CIRCUMSTANCES_CHANGED"
    assert history[1]["band"] == "MODERATE"
    assert history[1]["type"] == "ASSESSMENT"

    # Attempted update on RiskBandOverride raises AppendOnlyViolation
    with api.app.state.session_factory() as session:  # type: ignore[attr-defined]
        override_row = session.query(RiskBandOverride).filter_by(customer_id=BOB_ID).first()
        assert override_row is not None
        override_row.note = "Tampered note content"
        with pytest.raises(AppendOnlyViolation):
            session.flush()


@pytest.mark.ac("AC-09")
def test_ac_09_6_role_and_assignment_boundary(api: TestClient) -> None:
    """AC-09.6 — Customer calling advisor route -> 403; advisor calling unassigned customer -> 404."""
    # Customer calling advisor route
    res_customer = api.get("/api/v1/advisor/customers", headers=BOB)
    assert res_customer.status_code == 403
    assert res_customer.json()["error"]["code"] == "FORBIDDEN_ROLE"

    # Unassigned customer lookup (e.g. non-existent customer or unassigned)
    unknown_id = "00000000-0000-4000-8000-00000000c999"
    res_unknown = api.get(f"/api/v1/advisor/customers/{unknown_id}/portfolio", headers=DAN)
    assert res_unknown.status_code == 404
    assert res_unknown.json()["error"]["code"] == "CUSTOMER_NOT_FOUND"


@pytest.mark.ac("AC-09")
def test_ac_09_8_manual_recommendation_and_validation(api: TestClient) -> None:
    """AC-09.8 — Advisor logs manual recommendation (40/40/10/10); sums != 100 rejected (422)."""
    api.post("/api/v1/risk-profile/assessments", headers=ALICE, json=submission(RP1, ANS_16))

    # Invalid sum (99.99)
    bad_alloc = [
        {"asset_class": "EQUITY", "target_pct": "39.99"},
        {"asset_class": "DEBT", "target_pct": "40.00"},
        {"asset_class": "GOLD", "target_pct": "10.00"},
        {"asset_class": "CASH", "target_pct": "10.00"},
    ]
    bad_res = api.post(
        f"/api/v1/advisor/customers/{ALICE_ID}/manual-recommendations",
        headers=DAN,
        json={"allocation": bad_alloc, "note": "Custom allocation tailored for conservative transition."},
    )
    assert bad_res.status_code == 422
    assert bad_res.json()["error"]["code"] == "ALLOCATION_SUM_INVALID"

    # Valid manual recommendation (40/40/10/10)
    valid_alloc = [
        {"asset_class": "EQUITY", "target_pct": "40.00"},
        {"asset_class": "DEBT", "target_pct": "40.00"},
        {"asset_class": "GOLD", "target_pct": "10.00"},
        {"asset_class": "CASH", "target_pct": "10.00"},
    ]
    valid_res = api.post(
        f"/api/v1/advisor/customers/{ALICE_ID}/manual-recommendations",
        headers=DAN,
        json={"allocation": valid_alloc, "note": "Custom allocation tailored for conservative transition."},
    )
    assert valid_res.status_code == 201, valid_res.text
    rec = valid_res.json()
    assert rec["source"] == "ADVISOR_MANUAL"
    assert rec["total_pct"] == "100.00"

    # Alice's latest recommendation is this manual one
    alice_latest = api.get("/api/v1/recommendations/latest", headers=ALICE).json()
    assert alice_latest["id"] == rec["id"]
    assert alice_latest["source"] == "ADVISOR_MANUAL"
    assert [a["target_pct"] for a in alice_latest["allocation"]] == ["40.00", "40.00", "10.00", "10.00"]


@pytest.mark.ac("AC-09")
def test_advisor_customer_list_and_portfolio_view(api: TestClient) -> None:
    """Advisor can list assigned customers and view deep portfolio snapshot."""
    # List customers
    customers_res = api.get("/api/v1/advisor/customers", headers=DAN)
    assert customers_res.status_code == 200
    cust_list = customers_res.json()
    assert len(cust_list) >= 3
    customer_ids = [c["customer_id"] for c in cust_list]
    assert ALICE_ID in customer_ids
    assert BOB_ID in customer_ids

    # View portfolio
    portfolio_res = api.get(f"/api/v1/advisor/customers/{ALICE_ID}/portfolio", headers=DAN)
    assert portfolio_res.status_code == 200
    portfolio = portfolio_res.json()
    assert portfolio["customer"]["id"] == ALICE_ID
    assert "goals" in portfolio
    assert "holdings" in portfolio
