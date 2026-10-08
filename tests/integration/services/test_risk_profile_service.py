"""E2-S2: risk_profile_service use cases below HTTP (risk_profile_spec §2.4-2.5, §3-4; AC-01).

Fixed clock, migrated + seeded SQLite copy; asserts final state and exact row counts.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.fixtures.answer_sets import ANS_16, ANS_28, ANS_CAP24, AnswerSet, replaced, without
from tests.fixtures.policy_definitions import risk_policy_v2_ac_10_1

from app.core.clock import FixedClock
from app.core.db import build_engine, build_session_factory
from app.core.security import Principal, Role
from app.domain.bands import RiskBand
from app.domain.policy import PolicyStatus
from app.domain.risk_band_rules import Answer
from app.repositories.errors import AppendOnlyViolation
from app.repositories.models import AuditEvent, RiskAssessment, RiskPolicyVersion
from app.services import risk_profile_service
from app.services.errors import ServiceError

V1_ID = "00000000-0000-4000-8000-000000000201"
ALICE = "00000000-0000-4000-8000-00000000c001"
BOB = "00000000-0000-4000-8000-00000000c002"
ALICE_PRINCIPAL = Principal("alice.customer", Role.CUSTOMER)
NOW = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)


@pytest.fixture
def session(migrated_db_copy: Path) -> Iterator[Session]:
    engine = build_engine(f"sqlite:///{migrated_db_copy}")
    with build_session_factory(engine)() as s:
        yield s
    engine.dispose()


def _submit(
    session: Session, answers: AnswerSet, at: datetime = NOW, version_id: str = V1_ID
) -> risk_profile_service.SubmittedAssessment:
    return risk_profile_service.submit_assessment(
        session,
        FixedClock(at),
        ALICE_PRINCIPAL,
        ALICE,
        version_id,
        [Answer(q, o) for q, o in answers],
    )


def _count(session: Session, model: type[RiskAssessment] | type[AuditEvent]) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


@pytest.mark.ac("AC-01")
def test_ac_01_questionnaire_exposes_no_points(session: Session) -> None:
    """AC-01.1: active v1 questionnaire has 7 questions in order, 5 options each, and no point values."""
    q = risk_profile_service.questionnaire(session)

    assert (q.policy_version_id, q.version_no) == (V1_ID, 1)
    assert [x.code for x in q.questions] == [
        "AGE",
        "HORIZON",
        "INCOME_STABILITY",
        "EMERGENCY_FUND",
        "LOSS_REACTION",
        "EXPERIENCE",
        "OBJECTIVE",
    ]
    assert [x.order for x in q.questions] == [1, 2, 3, 4, 5, 6, 7]
    assert all(len(x.options) == 5 for x in q.questions)
    assert not any(hasattr(o, "points") for x in q.questions for o in x.options)


@pytest.mark.ac("AC-01")
def test_ac_01_submit_persists_one_assessment_and_one_audit_row(session: Session) -> None:
    """AC-01.2 / AC-01.4: ANS_CAP24 -> 24, AGGRESSIVE -> MODERATE, NO_EMERGENCY_FUND; 1 row + 1 audit row."""
    result = risk_profile_service.submit_assessment(
        session, FixedClock(NOW), ALICE_PRINCIPAL, ALICE, V1_ID, [Answer(q, o) for q, o in reversed(ANS_CAP24)]
    )

    assert (result.total_score, result.computed_band, result.assigned_band) == (24, "AGGRESSIVE", "MODERATE")
    assert list(result.applied_caps) == ["NO_EMERGENCY_FUND"]
    assert (result.policy_version_no, result.created_at) == (1, NOW)
    session.expire_all()
    assert _count(session, RiskAssessment) == 1
    row = session.get(RiskAssessment, result.assessment_id)
    assert row is not None
    assert row.customer_id == ALICE
    assert row.risk_policy_version_id == V1_ID
    assert row.answers == [{"question_code": q, "option_code": o} for q, o in ANS_CAP24]
    assert (row.total_score, row.computed_band, row.assigned_band) == (24, RiskBand.AGGRESSIVE, RiskBand.MODERATE)
    assert row.applied_caps == ["NO_EMERGENCY_FUND"]
    audits = session.scalars(select(AuditEvent)).all()
    assert len(audits) == 1
    assert (audits[0].action, audits[0].entity_type, audits[0].entity_id) == (
        "RISK_ASSESSMENT_SUBMITTED",
        "risk_assessment",
        result.assessment_id,
    )
    assert audits[0].actor_role == "CUSTOMER"
    assert audits[0].actor_user_id is not None
    assert audits[0].details == {"policy_version_no": 1}


@pytest.mark.ac("AC-01")
@pytest.mark.parametrize(
    ("answers", "code"),
    [(without(ANS_16, "OBJECTIVE"), "ANSWER_MISSING"), (replaced(ANS_16, "AGE", "GT_10Y"), "OPTION_INVALID")],
)
def test_ac_01_invalid_submission_is_422_and_writes_nothing(session: Session, answers: AnswerSet, code: str) -> None:
    """AC-01.6: missing OBJECTIVE -> 422 ANSWER_MISSING; AGE=GT_10Y -> 422 OPTION_INVALID; no rows created."""
    with pytest.raises(ServiceError) as raised:
        _submit(session, answers)

    assert (raised.value.status, raised.value.code) == (422, code)
    session.rollback()
    assert (_count(session, RiskAssessment), _count(session, AuditEvent)) == (0, 0)


@pytest.mark.ac("AC-01")
def test_ac_01_stale_policy_version_is_409_and_writes_nothing(session: Session) -> None:
    """AC-01.8: v2 published after the client fetched v1 -> submitting v1's id is 409 POLICY_VERSION_STALE."""
    session.add(RiskPolicyVersion(version_no=2, status=PolicyStatus.PUBLISHED, definition=risk_policy_v2_ac_10_1()))
    session.commit()

    with pytest.raises(ServiceError) as raised:
        _submit(session, ANS_16)

    assert (raised.value.status, raised.value.code) == (409, "POLICY_VERSION_STALE")
    session.rollback()
    assert (_count(session, RiskAssessment), _count(session, AuditEvent)) == (0, 0)


@pytest.mark.ac("AC-01")
def test_ac_01_effective_band_and_history_follow_the_newest_assessment(session: Session) -> None:
    """AC-01.7 / AC-01.5: two assessments both persist; the second band is effective; history is newest first."""
    assert risk_profile_service.effective_band(session, ALICE) is None
    assert risk_profile_service.history(session, ALICE) == []

    first = _submit(session, ANS_16, at=NOW)
    second = _submit(session, ANS_28, at=NOW + timedelta(minutes=5))

    effective = risk_profile_service.effective_band(session, ALICE)
    assert effective == risk_profile_service.EffectiveBand(
        band=RiskBand.AGGRESSIVE,
        source="ASSESSMENT",
        source_id=second.assessment_id,
        as_of=NOW + timedelta(minutes=5),
        policy_version_no=1,
    )
    entries = risk_profile_service.history(session, ALICE)
    assert [(e.type, e.id, e.band, e.policy_version_no) for e in entries] == [
        ("ASSESSMENT", second.assessment_id, RiskBand.AGGRESSIVE, 1),
        ("ASSESSMENT", first.assessment_id, RiskBand.MODERATE, 1),
    ]
    assert entries[0].created_at == NOW + timedelta(minutes=5)
    assert _count(session, RiskAssessment) == 2
    assert risk_profile_service.history(session, BOB) == []
    assert risk_profile_service.effective_band(session, BOB) is None


@pytest.mark.ac("AC-01")
def test_ac_01_update_on_risk_assessments_raises_append_only_violation(session: Session) -> None:
    """AC-01.7: an attempted UPDATE on risk_assessments raises AppendOnlyViolation; the row is unchanged."""
    result = _submit(session, ANS_16)
    row = session.get(RiskAssessment, result.assessment_id)
    assert row is not None

    row.assigned_band = RiskBand.AGGRESSIVE
    with pytest.raises(AppendOnlyViolation):
        session.flush()
    session.rollback()

    session.expire_all()
    reloaded = session.get(RiskAssessment, result.assessment_id)
    assert reloaded is not None
    assert reloaded.assigned_band == RiskBand.MODERATE
