"""AC-10 — admin draft → publish API for template and risk-policy versions (admin_versioning_spec §2, §4)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from tests.fixtures.policy_definitions import risk_policy_v2_ac_10_1, template_v1, template_with

TV1 = "00000000-0000-4000-8000-000000000101"
RP1 = "00000000-0000-4000-8000-000000000201"
ADMIN = {"Authorization": "Bearer stub-token-erin"}
TEMPLATES = "/api/v1/admin/template-versions"
RISK = "/api/v1/admin/risk-policies"


def _draft(client: TestClient, base: str) -> dict[str, Any]:
    response = client.post(f"{base}/drafts", headers=ADMIN)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def _audit_actions(client: TestClient) -> list[str]:
    from sqlalchemy import select

    from app.repositories.models import AuditEvent

    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        return [e.action for e in session.scalars(select(AuditEvent).order_by(AuditEvent.occurred_at))]


@pytest.mark.ac("AC-10")
@pytest.mark.parametrize(
    ("token", "method", "path"),
    [
        ("stub-token-alice", "GET", TEMPLATES),
        ("stub-token-dan", "GET", TEMPLATES),
        ("stub-token-alice", "POST", f"{RISK}/drafts"),
        ("stub-token-dan", "PUT", f"{TEMPLATES}/{TV1}"),
    ],
)
def test_ac_10_admin_routes_reject_customer_and_advisor(client: TestClient, token: str, method: str, path: str) -> None:
    """AC-10.8 — CUSTOMER or ADVISOR token on /api/v1/admin/* → 403 FORBIDDEN_ROLE; nothing created."""
    response = client.request(method, path, headers={"Authorization": f"Bearer {token}"}, json={"definition": {}})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN_ROLE"
    assert client.get(RISK, headers=ADMIN).json()[-1]["version_no"] == 1


def test_admin_route_without_token_is_401(client: TestClient) -> None:
    assert client.post(f"{RISK}/drafts").json()["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.ac("AC-10")
def test_ac_10_published_template_is_immutable_via_api(client: TestClient) -> None:
    """AC-10.2 — PUT and DELETE on published v1 → 409 POLICY_VERSION_IMMUTABLE; definition byte-identical."""
    before = client.get(f"{TEMPLATES}/{TV1}", headers=ADMIN).json()

    put = client.put(f"{TEMPLATES}/{TV1}", headers=ADMIN, json={"definition": template_v1()})
    delete = client.delete(f"{TEMPLATES}/{TV1}", headers=ADMIN)

    assert (put.status_code, put.json()["error"]["code"]) == (409, "POLICY_VERSION_IMMUTABLE")
    assert (delete.status_code, delete.json()["error"]["code"]) == (409, "POLICY_VERSION_IMMUTABLE")
    assert client.get(f"{TEMPLATES}/{TV1}", headers=ADMIN).json() == before
    assert before["definition"]["templates"]["MODERATE"] == {
        "EQUITY": "50.00",
        "DEBT": "35.00",
        "GOLD": "10.00",
        "CASH": "5.00",
    }


@pytest.mark.ac("AC-10")
def test_ac_10_risk_policy_v2_published_alongside_unchanged_v1(client: TestClient) -> None:
    """AC-10.1 — draft copied from v1, bands changed to 12-19 / 20-28, published; v1 still PUBLISHED and unchanged."""
    draft = _draft(client, RISK)
    assert (draft["version_no"], draft["status"]) == (2, "DRAFT")
    assert draft["definition"]["bands"][1] == {"band": "MODERATE", "min_score": 12, "max_score": 20}

    assert (
        client.put(f"{RISK}/{draft['id']}", headers=ADMIN, json={"definition": risk_policy_v2_ac_10_1()}).status_code
        == 200
    )
    published = client.post(f"{RISK}/{draft['id']}/publish", headers=ADMIN)

    assert published.status_code == 200
    assert (published.json()["version_no"], published.json()["status"]) == (2, "PUBLISHED")
    listing = client.get(RISK, headers=ADMIN).json()
    assert [(v["version_no"], v["status"]) for v in listing] == [(1, "PUBLISHED"), (2, "PUBLISHED")]
    v1 = client.get(f"{RISK}/{RP1}", headers=ADMIN).json()
    assert [(b["min_score"], b["max_score"]) for b in v1["definition"]["bands"]] == [(0, 11), (12, 20), (21, 28)]
    assert _audit_actions(client) == ["POLICY_DRAFT_CREATED", "POLICY_DRAFT_UPDATED", "POLICY_PUBLISHED"]


@pytest.mark.ac("AC-10")
def test_ac_10_publish_validation_names_band_and_sum(client: TestClient) -> None:
    """AC-10.4 — AGGRESSIVE row summing to 100.01 → 422 TEMPLATE_INVALID naming AGGRESSIVE sum=100.01; stays DRAFT."""
    draft = _draft(client, TEMPLATES)
    client.put(
        f"{TEMPLATES}/{draft['id']}", headers=ADMIN, json={"definition": template_with("AGGRESSIVE", "GOLD", "7.51")}
    )

    response = client.post(f"{TEMPLATES}/{draft['id']}/publish", headers=ADMIN)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "TEMPLATE_INVALID"
    assert any("AGGRESSIVE" in v and "sum=100.01" in v for v in error["details"]["violations"])
    assert client.get(f"{TEMPLATES}/{draft['id']}", headers=ADMIN).json()["status"] == "DRAFT"


@pytest.mark.ac("AC-10")
@pytest.mark.parametrize("base", [TEMPLATES, RISK])
def test_ac_10_only_one_draft_at_a_time(client: TestClient, base: str) -> None:
    """AC-10.7 — a second draft request while one exists → 409 DRAFT_EXISTS."""
    _draft(client, base)
    response = client.post(f"{base}/drafts", headers=ADMIN)

    assert (response.status_code, response.json()["error"]["code"]) == (409, "DRAFT_EXISTS")


def test_json_number_for_a_decimal_is_rejected(client: TestClient) -> None:
    """NFR-01 / app_spec §5.1 — decimals must be strings; JSON numbers → 422 DECIMAL_MUST_BE_STRING."""
    draft = _draft(client, TEMPLATES)
    bad = {**template_v1(), "drift_threshold_pct": 5.0}

    response = client.put(f"{TEMPLATES}/{draft['id']}", headers=ADMIN, json={"definition": bad})

    assert (response.status_code, response.json()["error"]["code"]) == (422, "DECIMAL_MUST_BE_STRING")


def test_draft_can_be_deleted_and_unknown_id_is_404(client: TestClient) -> None:
    draft = _draft(client, TEMPLATES)

    assert client.delete(f"{TEMPLATES}/{draft['id']}", headers=ADMIN).status_code == 204
    missing = client.get(f"{TEMPLATES}/{draft['id']}", headers=ADMIN)
    assert (missing.status_code, missing.json()["error"]["code"]) == (404, "POLICY_VERSION_NOT_FOUND")
    assert _draft(client, TEMPLATES)["version_no"] == 2  # the deleted draft's number is reused only while unpublished


def test_publishing_twice_is_409_already_published(client: TestClient) -> None:
    draft = _draft(client, TEMPLATES)
    client.post(f"{TEMPLATES}/{draft['id']}/publish", headers=ADMIN)

    again = client.post(f"{TEMPLATES}/{draft['id']}/publish", headers=ADMIN)

    assert (again.status_code, again.json()["error"]["code"]) == (409, "ALREADY_PUBLISHED")
