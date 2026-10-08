"""AC-02 / AC-04 — recommendation API: generate, latest, list (recommendation_spec §2, §4-5; specs/stories/E3-S2.md).

Expected values are copied verbatim from recommendation_spec §2.1/§2.3/§5 and sprint-1 api checks. The clock is
anchored at 2026-01-15T09:00Z (date pinned, time advancing) exactly as in the evaluator setup.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from tests.fixtures.answer_sets import ANS_0, ANS_16, ANS_28, AnswerSet, submission
from tests.fixtures.policy_definitions import template_with

from app.core.clock import AnchoredClock
from app.core.config import Settings
from app.domain.policy import PolicyStatus
from app.repositories.models import AuditEvent, Recommendation, RecommendationAllocation, TemplateVersion

RP1 = "00000000-0000-4000-8000-000000000201"
TV1 = "00000000-0000-4000-8000-000000000101"
FRANK_GOAL = "00000000-0000-4000-8000-0000000f0001"
GRACE_GOAL_B = "00000000-0000-4000-8000-0000000b0001"
BASE = "/api/v1/recommendations"
RESPONSE_KEYS = {
    "id",
    "source",
    "risk_band",
    "template_version_no",
    "goal_id",
    "horizon_months",
    "horizon_rule",
    "as_of_date",
    "allocation",
    "total_pct",
    "created_at",
}


def _auth(user: str) -> dict[str, str]:
    return {"Authorization": f"Bearer stub-token-{user}"}


def _alloc(*values: str) -> list[dict[str, str]]:
    return [
        {"asset_class": c, "target_pct": v} for c, v in zip(("EQUITY", "DEBT", "GOLD", "CASH"), values, strict=True)
    ]


@pytest.fixture
def api(settings: Settings) -> Iterator[TestClient]:
    from app.main import create_app

    clock = AnchoredClock(datetime(2026, 1, 15, 9, 0, tzinfo=UTC))
    with TestClient(create_app(settings, clock=clock)) as test_client:
        yield test_client


def _assess(client: TestClient, user: str, answers: AnswerSet) -> None:
    response = client.post("/api/v1/risk-profile/assessments", headers=_auth(user), json=submission(RP1, answers))
    assert response.status_code == 201, response.text


def _recommend(client: TestClient, user: str, body: dict[str, Any] | None = None) -> Any:
    return client.post(BASE, headers=_auth(user), json={} if body is None else body)


def _counts(client: TestClient) -> tuple[int, int, int]:
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        recs = session.scalar(select(func.count()).select_from(Recommendation))
        rows = session.scalar(select(func.count()).select_from(RecommendationAllocation))
        audits = session.scalar(
            select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "RECOMMENDATION_CREATED")
        )
        return int(recs or 0), int(rows or 0), int(audits or 0)


@pytest.mark.ac("AC-02")
@pytest.mark.parametrize(
    ("method", "path", "headers", "status", "code"),
    [
        ("POST", "", {}, 401, "UNAUTHENTICATED"),
        ("GET", "", {}, 401, "UNAUTHENTICATED"),
        ("GET", "/latest", {}, 401, "UNAUTHENTICATED"),
        ("POST", "", _auth("dan"), 403, "FORBIDDEN_ROLE"),
        ("GET", "", _auth("erin"), 403, "FORBIDDEN_ROLE"),
        ("GET", "/latest", _auth("dan"), 403, "FORBIDDEN_ROLE"),
    ],
)
def test_ac_02_recommendation_routes_require_customer_role(
    api: TestClient, method: str, path: str, headers: dict[str, str], status: int, code: str
) -> None:
    """AC-02.1 (recommendation §4, NFR-04): no token -> 401; ADVISOR/ADMIN -> 403 FORBIDDEN_ROLE; nothing written."""
    response = api.request(method, f"{BASE}{path}", headers=headers, json={})

    assert (response.status_code, response.json()["error"]["code"]) == (status, code)
    assert _counts(api) == (0, 0, 0)


@pytest.mark.ac("AC-02")
def test_ac_02_moderate_no_goal_returns_v1_row_as_strings(api: TestClient) -> None:
    """AC-02.1: alice MODERATE, no goals -> 201, v1 50/35/10/5, NO_GOAL, total_pct "100.00"; v1 pinned + audited."""
    _assess(api, "alice", ANS_16)

    response = _recommend(api, "alice")

    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == RESPONSE_KEYS
    assert {k: body[k] for k in RESPONSE_KEYS - {"id", "created_at"}} == {
        "source": "SYSTEM",
        "risk_band": "MODERATE",
        "template_version_no": 1,
        "goal_id": None,
        "horizon_months": None,
        "horizon_rule": "NO_GOAL",
        "as_of_date": "2026-01-15",
        "allocation": _alloc("50.00", "35.00", "10.00", "5.00"),
        "total_pct": "100.00",
    }
    assert body["created_at"].startswith("2026-01-15T09:00")
    assert _counts(api) == (1, 4, 1)
    with api.app.state.session_factory() as session:  # type: ignore[attr-defined]
        stored = session.get(Recommendation, body["id"])
        assert stored is not None
        assert stored.template_version_id == TV1


@pytest.mark.ac("AC-02")
def test_ac_02_each_band_gets_its_v1_row(api: TestClient) -> None:
    """AC-02.2: bob ANS_0 -> CONSERVATIVE 20/60/10/10; bob ANS_28 -> AGGRESSIVE 75/15/7.50/2.50 (newest wins)."""
    _assess(api, "bob", ANS_0)
    conservative = _recommend(api, "bob").json()
    _assess(api, "bob", ANS_28)
    aggressive = _recommend(api, "bob").json()

    assert (conservative["risk_band"], conservative["allocation"]) == (
        "CONSERVATIVE",
        _alloc("20.00", "60.00", "10.00", "10.00"),
    )
    assert (aggressive["risk_band"], aggressive["allocation"]) == (
        "AGGRESSIVE",
        _alloc("75.00", "15.00", "7.50", "2.50"),
    )
    assert conservative["horizon_rule"] == aggressive["horizon_rule"] == "NO_GOAL"
    assert conservative["total_pct"] == aggressive["total_pct"] == "100.00"


@pytest.mark.ac("AC-02")
def test_ac_02_no_risk_profile_is_409_and_persists_nothing(api: TestClient) -> None:
    """AC-02.5: carol has no assessment or override -> 409 RISK_PROFILE_REQUIRED; counts unchanged."""
    response = _recommend(api, "carol")

    assert (response.status_code, response.json()["error"]["code"]) == (409, "RISK_PROFILE_REQUIRED")
    assert _counts(api) == (0, 0, 0)


@pytest.mark.ac("AC-04")
def test_ac_04_goal_not_owned_is_404_and_persists_nothing(api: TestClient) -> None:
    """recommendation §2.2 / AC-04.1: alice naming grace's goal B -> 404 GOAL_NOT_FOUND; counts unchanged."""
    _assess(api, "alice", ANS_16)

    response = _recommend(api, "alice", {"goal_id": GRACE_GOAL_B})

    assert (response.status_code, response.json()["error"]["code"]) == (404, "GOAL_NOT_FOUND")
    assert _counts(api) == (0, 0, 0)


@pytest.mark.ac("AC-04")
def test_ac_04_malformed_goal_id_is_422(api: TestClient) -> None:
    """AC-04.1 (recommendation §4: goal_id is a uuid): a non-uuid goal_id -> 422 VALIDATION_FAILED; nothing written."""
    _assess(api, "alice", ANS_16)

    response = _recommend(api, "alice", {"goal_id": "not-a-goal"})

    assert (response.status_code, response.json()["error"]["code"]) == (422, "VALIDATION_FAILED")
    assert _counts(api) == (0, 0, 0)


@pytest.mark.ac("AC-02")
def test_ac_02_corrupted_active_template_is_an_error_and_persists_nothing(api: TestClient) -> None:
    """AC-02.4: active PUBLISHED template with MODERATE summing to 99.99 -> 422 TEMPLATE_INVALID; nothing stored."""
    _assess(api, "alice", ANS_16)
    with api.app.state.session_factory() as session:  # type: ignore[attr-defined]
        definition = template_with("MODERATE", "CASH", "4.99")
        session.add(TemplateVersion(version_no=2, status=PolicyStatus.PUBLISHED, definition=definition))
        session.commit()

    response = _recommend(api, "alice")

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "TEMPLATE_INVALID"
    assert "MODERATE sum=99.99" in error["message"]
    assert _counts(api) == (0, 0, 0)


@pytest.mark.ac("AC-04")
def test_ac_04_named_goal_48_months_moves_20_points(api: TestClient) -> None:
    """AC-04.1: clock 2026-01-15, frank MODERATE, goal 2030-01-15 -> 48 months, H_36_59, 30/55/10/5."""
    _assess(api, "frank", ANS_16)

    response = _recommend(api, "frank", {"goal_id": FRANK_GOAL})

    assert response.status_code == 201, response.text
    body = response.json()
    assert {k: body[k] for k in ("goal_id", "horizon_months", "horizon_rule", "as_of_date", "template_version_no")} == {
        "goal_id": FRANK_GOAL,
        "horizon_months": 48,
        "horizon_rule": "H_36_59",
        "as_of_date": "2026-01-15",
        "template_version_no": 1,
    }
    assert body["risk_band"] == "MODERATE"
    assert body["allocation"] == _alloc("30.00", "55.00", "10.00", "5.00")
    assert body["total_pct"] == "100.00"


@pytest.mark.ac("AC-04")
def test_ac_04_primary_goal_is_used_without_goal_id(api: TestClient) -> None:
    """AC-04.3: grace goals A (P2, 2040-01-01), B (P1, 2028-06-30), clock 2026-01-15 -> B, 29 months, H_12_35."""
    _assess(api, "grace", ANS_16)

    body = _recommend(api, "grace").json()

    assert (body["goal_id"], body["horizon_months"], body["horizon_rule"]) == (GRACE_GOAL_B, 29, "H_12_35")
    assert body["allocation"] == _alloc("20.00", "65.00", "10.00", "5.00")
    assert (body["as_of_date"], body["template_version_no"], body["total_pct"]) == ("2026-01-15", 1, "100.00")


@pytest.mark.ac("AC-04")
def test_ac_04_identical_requests_are_deterministic_and_append_only(api: TestClient) -> None:
    """AC-04.4: two identical POSTs -> identical allocation/horizon/rule/version, distinct ids; latest + list order."""
    _assess(api, "frank", ANS_16)
    latest_before = api.get(f"{BASE}/latest", headers=_auth("frank"))
    assert (latest_before.status_code, latest_before.json()["error"]["code"]) == (404, "RECOMMENDATION_NOT_FOUND")
    assert api.get(BASE, headers=_auth("frank")).json() == []

    first = _recommend(api, "frank", {"goal_id": FRANK_GOAL}).json()
    second = _recommend(api, "frank", {"goal_id": FRANK_GOAL}).json()

    assert first["id"] != second["id"]
    for key in ("allocation", "horizon_months", "horizon_rule", "template_version_no", "as_of_date", "total_pct"):
        assert first[key] == second[key], key
    assert _counts(api) == (2, 8, 2)
    latest = api.get(f"{BASE}/latest", headers=_auth("frank"))
    assert latest.status_code == 200
    assert latest.json() == second
    listed = api.get(BASE, headers=_auth("frank"))
    assert listed.status_code == 200
    assert listed.json() == [second, first]
    assert api.get(BASE, headers=_auth("alice")).json() == []
