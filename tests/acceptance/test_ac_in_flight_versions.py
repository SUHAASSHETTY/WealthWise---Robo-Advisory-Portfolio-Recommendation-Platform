"""AC-10.5 / AC-10.6 — in-flight customers keep their versions (admin_versioning_spec §2.4; specs/stories/E3-S3.md).

Publishing a new template or risk policy through the admin API affects only new actions: stored recommendations and
assessments keep the version they were created under. The drift clause of AC-10.5 is deferred to the holdings sprint.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from tests.fixtures.answer_sets import ANS_16, ANS_20, AnswerSet, submission
from tests.fixtures.policy_definitions import risk_policy_v2_ac_10_1, template_v1

from app.core.clock import AnchoredClock
from app.core.config import Settings
from app.repositories.models import Recommendation

RP1 = "00000000-0000-4000-8000-000000000201"
TV1 = "00000000-0000-4000-8000-000000000101"
ADMIN = {"Authorization": "Bearer stub-token-erin"}
ALICE = {"Authorization": "Bearer stub-token-alice"}
BOB = {"Authorization": "Bearer stub-token-bob"}
TEMPLATES = "/api/v1/admin/template-versions"
RISK = "/api/v1/admin/risk-policies"
RECS = "/api/v1/recommendations"
PROFILE = "/api/v1/risk-profile"


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


def _publish(client: TestClient, base: str, definition: dict[str, Any]) -> dict[str, Any]:
    draft = client.post(f"{base}/drafts", headers=ADMIN)
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]
    assert client.put(f"{base}/{draft_id}", headers=ADMIN, json={"definition": definition}).status_code == 200
    published = client.post(f"{base}/{draft_id}/publish", headers=ADMIN)
    assert published.status_code == 200, published.text
    body: dict[str, Any] = published.json()
    return body


def _assess(client: TestClient, headers: dict[str, str], version_id: str, answers: AnswerSet) -> Any:
    return client.post(f"{PROFILE}/assessments", headers=headers, json=submission(version_id, answers))


def _template_v2_moderate_45_40() -> dict[str, Any]:
    definition = template_v1()
    definition["templates"]["MODERATE"] = {"EQUITY": "45.00", "DEBT": "40.00", "GOLD": "10.00", "CASH": "5.00"}
    return definition


@pytest.mark.ac("AC-10")
def test_ac_10_recommendation_keeps_its_template_after_v2_is_published(api: TestClient) -> None:
    """AC-10.5: alice's v1 recommendation (50/35/10/5) is unchanged after erin publishes template v2 (MODERATE
    45/40/10/5); her next recommendation uses v2, and the list shows both, v2 first."""
    assert _assess(api, ALICE, RP1, ANS_16).status_code == 201
    first = api.post(RECS, headers=ALICE, json={}).json()
    assert (first["template_version_no"], first["allocation"]) == (1, _alloc("50.00", "35.00", "10.00", "5.00"))

    v2 = _publish(api, TEMPLATES, _template_v2_moderate_45_40())
    assert v2["version_no"] == 2

    latest = api.get(f"{RECS}/latest", headers=ALICE).json()
    assert latest == first
    assert (latest["template_version_no"], latest["allocation"]) == (1, _alloc("50.00", "35.00", "10.00", "5.00"))
    assert latest["total_pct"] == "100.00"
    with api.app.state.session_factory() as session:  # type: ignore[attr-defined]
        stored = session.get(Recommendation, first["id"])
        assert stored is not None
        assert stored.template_version_id == TV1

    second = api.post(RECS, headers=ALICE, json={})

    assert second.status_code == 201, second.text
    new = second.json()
    assert (new["risk_band"], new["template_version_no"], new["horizon_rule"]) == ("MODERATE", 2, "NO_GOAL")
    assert new["allocation"] == _alloc("45.00", "40.00", "10.00", "5.00")
    assert new["total_pct"] == "100.00"
    assert api.get(f"{RECS}/latest", headers=ALICE).json() == new
    listed = api.get(RECS, headers=ALICE).json()
    assert len(listed) == 2
    assert [r["id"] for r in listed] == [new["id"], first["id"]]
    assert [r["template_version_no"] for r in listed] == [2, 1]
    assert listed[1]["allocation"] == _alloc("50.00", "35.00", "10.00", "5.00")


@pytest.mark.ac("AC-10")
def test_ac_10_assessment_keeps_its_policy_and_new_band_flows_into_recommendation(api: TestClient) -> None:
    """AC-10.6 / AC-01.8 / AC-02.2: bob ANS_20 under v1 -> MODERATE, kept after risk policy v2; v1 id now stale (409);
    resubmitting under v2 -> 20, AGGRESSIVE; his new recommendation uses AGGRESSIVE 75/15/7.50/2.50."""
    v1_result = _assess(api, BOB, RP1, ANS_20)
    assert v1_result.status_code == 201
    assert (v1_result.json()["total_score"], v1_result.json()["assigned_band"]) == (20, "MODERATE")
    first = api.post(RECS, headers=BOB, json={}).json()
    assert (first["risk_band"], first["allocation"]) == ("MODERATE", _alloc("50.00", "35.00", "10.00", "5.00"))

    rp2 = _publish(api, RISK, risk_policy_v2_ac_10_1())

    assert api.get(PROFILE, headers=BOB).json()["risk_band"] == "MODERATE"
    assert [h["policy_version_no"] for h in api.get(f"{PROFILE}/history", headers=BOB).json()] == [1]
    assert api.get(f"{PROFILE}/questionnaire", headers=BOB).json()["version_no"] == 2
    stale = _assess(api, BOB, RP1, ANS_20)
    assert (stale.status_code, stale.json()["error"]["code"]) == (409, "POLICY_VERSION_STALE")

    v2_result = _assess(api, BOB, rp2["id"], ANS_20)

    assert v2_result.status_code == 201
    body = v2_result.json()
    assert (body["total_score"], body["assigned_band"], body["policy_version_no"]) == (20, "AGGRESSIVE", 2)
    assert api.get(PROFILE, headers=BOB).json()["risk_band"] == "AGGRESSIVE"
    new = api.post(RECS, headers=BOB, json={})
    assert new.status_code == 201
    assert (new.json()["risk_band"], new.json()["template_version_no"]) == ("AGGRESSIVE", 1)
    assert new.json()["allocation"] == _alloc("75.00", "15.00", "7.50", "2.50")
    assert api.get(f"{RECS}/latest", headers=BOB).json()["id"] == new.json()["id"]
    assert api.get(RECS, headers=BOB).json()[1] == first
