"""AC-01 — risk profile API: questionnaire, assessments, effective band, history (risk_profile_spec §4-5).

Expected values are copied verbatim from risk_profile_spec §5 and specs/stories/E2-S2.md.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from tests.fixtures.answer_sets import ANS_0, ANS_16, ANS_28, ANS_CAP24, AnswerSet, replaced, submission, without
from tests.fixtures.policy_definitions import risk_policy_v2_ac_10_1

from app.domain.policy import PolicyStatus
from app.repositories.models import AuditEvent, RiskAssessment, RiskPolicyVersion

V1_ID = "00000000-0000-4000-8000-000000000201"
ALICE_ID = "00000000-0000-4000-8000-00000000c001"
BASE = "/api/v1/risk-profile"
ALICE = {"Authorization": "Bearer stub-token-alice"}
BOB = {"Authorization": "Bearer stub-token-bob"}
DAN = {"Authorization": "Bearer stub-token-dan"}
FORBIDDEN_KEYS = {"points", "bands", "min_score", "max_score", "caps"}


def _keys(node: Any) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in _keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in _keys(v)}
    return set()


def _post(client: TestClient, answers: AnswerSet, headers: dict[str, str] = ALICE) -> Any:
    return client.post(f"{BASE}/assessments", headers=headers, json=submission(V1_ID, answers))


def _counts(client: TestClient) -> tuple[int, int]:
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        assessments = session.scalar(select(func.count()).select_from(RiskAssessment))
        audits = session.scalar(
            select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "RISK_ASSESSMENT_SUBMITTED")
        )
        return int(assessments or 0), int(audits or 0)


@pytest.mark.ac("AC-01")
def test_ac_01_questionnaire_has_7_questions_5_options_and_no_points(client: TestClient) -> None:
    """AC-01.1: GET questionnaire -> v1, 7 questions (orders 1-7), 5 options each, no points or thresholds."""
    response = client.get(f"{BASE}/questionnaire", headers=ALICE)

    assert response.status_code == 200
    body = response.json()
    assert (body["policy_version_id"], body["version_no"]) == (V1_ID, 1)
    assert [(q["order"], q["code"]) for q in body["questions"]] == [
        (1, "AGE"),
        (2, "HORIZON"),
        (3, "INCOME_STABILITY"),
        (4, "EMERGENCY_FUND"),
        (5, "LOSS_REACTION"),
        (6, "EXPERIENCE"),
        (7, "OBJECTIVE"),
    ]
    assert all(len(q["options"]) == 5 for q in body["questions"])
    assert set(body["questions"][0]) == {"code", "prompt", "order", "options"}
    assert set(body["questions"][0]["options"][0]) == {"code", "label"}
    assert _keys(body).isdisjoint(FORBIDDEN_KEYS)


@pytest.mark.ac("AC-01")
@pytest.mark.parametrize(
    ("method", "path", "headers", "status", "code"),
    [
        ("GET", "/questionnaire", {}, 401, "UNAUTHENTICATED"),
        ("GET", "/questionnaire", DAN, 403, "FORBIDDEN_ROLE"),
        ("POST", "/assessments", DAN, 403, "FORBIDDEN_ROLE"),
        ("GET", "", DAN, 403, "FORBIDDEN_ROLE"),
        ("GET", "/history", {}, 401, "UNAUTHENTICATED"),
    ],
)
def test_ac_01_routes_are_customer_only(
    client: TestClient, method: str, path: str, headers: dict[str, str], status: int, code: str
) -> None:
    """AC-01.1 (NFR-04): no token -> 401 UNAUTHENTICATED; ADVISOR token -> 403 FORBIDDEN_ROLE; nothing written."""
    response = client.request(method, f"{BASE}{path}", headers=headers, json=submission(V1_ID, ANS_16))

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert _counts(client) == (0, 0)


@pytest.mark.ac("AC-01")
def test_ac_01_moderate_example_returns_201_with_score_16(client: TestClient) -> None:
    """AC-01.2: ANS_16 -> 201, total_score 16, MODERATE/MODERATE, no caps, policy_version_no 1; 1 row + 1 audit."""
    response = _post(client, ANS_16)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {
        "assessment_id",
        "total_score",
        "computed_band",
        "assigned_band",
        "applied_caps",
        "policy_version_no",
        "created_at",
    }
    assert body["total_score"] == 16
    assert body["computed_band"] == "MODERATE"
    assert body["assigned_band"] == "MODERATE"
    assert body["applied_caps"] == []
    assert body["policy_version_no"] == 1
    assert _counts(client) == (1, 1)


@pytest.mark.ac("AC-01")
@pytest.mark.parametrize(
    ("answers", "total", "band"), [(ANS_0, 0, "CONSERVATIVE"), (ANS_28, 28, "AGGRESSIVE")], ids=["0", "28"]
)
def test_ac_01_band_boundaries_through_the_api(client: TestClient, answers: AnswerSet, total: int, band: str) -> None:
    """AC-01.3 (API spot check): total 0 -> CONSERVATIVE (EMERGENCY_FUND=NONE, cap no effect); 28 -> AGGRESSIVE."""
    body = _post(client, answers).json()

    assert (body["total_score"], body["computed_band"], body["assigned_band"]) == (total, band, band)
    assert body["applied_caps"] == []


@pytest.mark.ac("AC-01")
def test_ac_01_cap_applies_through_the_api(client: TestClient) -> None:
    """AC-01.4: max points except EMERGENCY_FUND=NONE -> 24, computed AGGRESSIVE, assigned MODERATE, cap listed."""
    response = _post(client, ANS_CAP24)

    assert response.status_code == 201
    body = response.json()
    assert body["total_score"] == 24
    assert body["computed_band"] == "AGGRESSIVE"
    assert body["assigned_band"] == "MODERATE"
    assert body["applied_caps"] == ["NO_EMERGENCY_FUND"]


@pytest.mark.ac("AC-01")
def test_ac_01_same_answers_submitted_twice_give_identical_results(client: TestClient) -> None:
    """AC-01.5 (API half): ANS_16 twice -> identical total/computed/assigned, distinct assessment_ids, two rows."""
    first, second = _post(client, ANS_16).json(), _post(client, ANS_16).json()

    fields = ("total_score", "computed_band", "assigned_band")
    assert [first[f] for f in fields] == [second[f] for f in fields] == [16, "MODERATE", "MODERATE"]
    assert first["assessment_id"] != second["assessment_id"]
    assert _counts(client) == (2, 2)


@pytest.mark.ac("AC-01")
@pytest.mark.parametrize(
    ("answers", "code"),
    [(without(ANS_16, "OBJECTIVE"), "ANSWER_MISSING"), (replaced(ANS_16, "AGE", "GT_10Y"), "OPTION_INVALID")],
    ids=["missing-objective", "age-gt-10y"],
)
def test_ac_01_invalid_submissions_are_422_and_persist_nothing(
    client: TestClient, answers: AnswerSet, code: str
) -> None:
    """AC-01.6: omitting OBJECTIVE -> 422 ANSWER_MISSING; AGE=GT_10Y -> 422 OPTION_INVALID; no assessment row."""
    response = _post(client, answers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    assert _counts(client) == (0, 0)


@pytest.mark.ac("AC-01")
def test_ac_01_second_assessment_becomes_effective_and_history_keeps_both(client: TestClient) -> None:
    """AC-01.7: before any assessment risk_band is null; after ANS_16 then ANS_28 the second is effective,
    history lists both newest first, both rows exist, and bob's history is empty."""
    assert client.get(BASE, headers=ALICE).json() == {"risk_band": None}

    first = _post(client, ANS_16).json()
    second = _post(client, ANS_28).json()

    profile = client.get(BASE, headers=ALICE).json()
    assert profile == {
        "risk_band": "AGGRESSIVE",
        "source": "ASSESSMENT",
        "source_id": second["assessment_id"],
        "as_of": second["created_at"],
    }
    history = client.get(f"{BASE}/history", headers=ALICE).json()
    assert history == [
        {
            "type": "ASSESSMENT",
            "id": second["assessment_id"],
            "band": "AGGRESSIVE",
            "created_at": second["created_at"],
            "policy_version_no": 1,
        },
        {
            "type": "ASSESSMENT",
            "id": first["assessment_id"],
            "band": "MODERATE",
            "created_at": first["created_at"],
            "policy_version_no": 1,
        },
    ]
    assert _counts(client) == (2, 2)
    assert client.get(f"{BASE}/history", headers=BOB).json() == []
    assert client.get(BASE, headers=BOB).json() == {"risk_band": None}


@pytest.mark.ac("AC-01")
def test_ac_01_stale_policy_version_is_409(client: TestClient) -> None:
    """AC-01.8: v2 published after the client fetched v1 -> submitting with v1's id is 409 POLICY_VERSION_STALE."""
    fetched = client.get(f"{BASE}/questionnaire", headers=ALICE).json()
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        session.add(RiskPolicyVersion(version_no=2, status=PolicyStatus.PUBLISHED, definition=risk_policy_v2_ac_10_1()))
        session.commit()

    response = client.post(f"{BASE}/assessments", headers=ALICE, json=submission(fetched["policy_version_id"], ANS_16))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "POLICY_VERSION_STALE"
    assert _counts(client) == (0, 0)
    assert client.get(f"{BASE}/questionnaire", headers=ALICE).json()["version_no"] == 2


@pytest.mark.ac("AC-01")
def test_ac_01_logs_carry_ids_only(capsys: pytest.CaptureFixture[str], client: TestClient) -> None:
    """AC-01.2 / AC-01.6 (NFR-03, §4 side effects): the submit log line has assessment_id and customer_id only;
    no username, option code, band name or score appears anywhere in the captured logs."""
    capsys.readouterr()
    accepted = _post(client, ANS_CAP24).json()
    _post(client, without(ANS_16, "OBJECTIVE"))
    client.get(BASE, headers=ALICE)
    client.get(f"{BASE}/history", headers=ALICE)

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    submitted = [r for r in lines if r.get("entity_id") == accepted["assessment_id"]]
    assert len(submitted) == 1
    assert submitted[0]["customer_id"] == ALICE_ID
    text = "\n".join(json.dumps(r) for r in lines)
    forbidden = ["alice", "MODERATE", "AGGRESSIVE", "CONSERVATIVE", "NO_EMERGENCY_FUND", "score", "answers"]
    forbidden += [o for _, o in ANS_CAP24 + ANS_16]
    assert [word for word in forbidden if word in text] == []
