"""E3-S2: recommendation_service use cases below HTTP (recommendation_spec §2.2, §2.4-2.5, §3-4; AC-02, AC-04).

Fixed clock, migrated + seeded SQLite copy; asserts final state and exact row counts.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.fixtures.answer_sets import ANS_0, ANS_16, ANS_28, AnswerSet
from tests.fixtures.policy_definitions import template_with

from app.core.clock import FixedClock
from app.core.config import Settings
from app.core.db import build_engine, build_session_factory
from app.core.security import Principal, Role
from app.domain.bands import RiskBand
from app.domain.policy import PolicyStatus
from app.domain.risk_band_rules import Answer
from app.repositories.errors import AppendOnlyViolation
from app.repositories.models import AuditEvent, Recommendation, RecommendationAllocation, TemplateVersion, User
from app.services import recommendation_service, risk_profile_service
from app.services.errors import ServiceError

RP1 = "00000000-0000-4000-8000-000000000201"
TV1 = "00000000-0000-4000-8000-000000000101"
ALICE = "00000000-0000-4000-8000-00000000c001"
BOB = "00000000-0000-4000-8000-00000000c002"
CAROL = "00000000-0000-4000-8000-00000000c003"
FRANK = "00000000-0000-4000-8000-00000000c004"
GRACE = "00000000-0000-4000-8000-00000000c005"
FRANK_GOAL = "00000000-0000-4000-8000-0000000f0001"
GRACE_GOAL_B = "00000000-0000-4000-8000-0000000b0001"
PRINCIPALS = {
    ALICE: Principal("alice.customer", Role.CUSTOMER),
    BOB: Principal("bob.customer", Role.CUSTOMER),
    CAROL: Principal("carol.customer", Role.CUSTOMER),
    FRANK: Principal("frank.customer", Role.CUSTOMER),
    GRACE: Principal("grace.customer", Role.CUSTOMER),
}
NOW = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)


def _row(*values: str) -> tuple[tuple[str, Decimal], ...]:
    return tuple(zip(("EQUITY", "DEBT", "GOLD", "CASH"), (Decimal(v) for v in values), strict=True))


@pytest.fixture
def session(settings: Settings) -> Iterator[Session]:
    engine = build_engine(settings.database_url)
    with build_session_factory(engine)() as s:
        yield s
    engine.dispose()


def _assess(session: Session, customer_id: str, answers: AnswerSet, at: datetime = NOW) -> None:
    risk_profile_service.submit_assessment(
        session, FixedClock(at), PRINCIPALS[customer_id], customer_id, RP1, [Answer(q, o) for q, o in answers]
    )


def _recommend(
    session: Session, customer_id: str, goal_id: str | None = None, at: datetime = NOW
) -> recommendation_service.RecommendationView:
    return recommendation_service.create_recommendation(
        session, FixedClock(at), PRINCIPALS[customer_id], customer_id, goal_id
    )


def _counts(session: Session) -> tuple[int, int, int]:
    session.expire_all()
    recs = session.scalar(select(func.count()).select_from(Recommendation))
    rows = session.scalar(select(func.count()).select_from(RecommendationAllocation))
    audits = session.scalar(
        select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "RECOMMENDATION_CREATED")
    )
    return int(recs or 0), int(rows or 0), int(audits or 0)


@pytest.mark.ac("AC-02")
def test_ac_02_moderate_no_goal_persists_v1_row_allocation_and_audit(session: Session) -> None:
    """AC-02.1: MODERATE, no goals -> 50/35/10/5, v1, NO_GOAL; 1 recommendation + 4 rows + 1 audit row, v1 pinned."""
    _assess(session, ALICE, ANS_16)

    view = _recommend(session, ALICE)

    assert (view.source, view.risk_band, view.template_version_no) == ("SYSTEM", RiskBand.MODERATE, 1)
    assert (view.goal_id, view.horizon_months, view.horizon_rule) == (None, None, "NO_GOAL")
    assert view.allocation == _row("50.00", "35.00", "10.00", "5.00")
    assert view.total_pct == Decimal("100.00")
    assert (view.as_of_date, view.created_at) == (date(2026, 1, 15), NOW)
    assert _counts(session) == (1, 4, 1)
    stored = session.get(Recommendation, view.id)
    assert stored is not None
    assert (stored.customer_id, stored.template_version_id, stored.source) == (ALICE, TV1, "SYSTEM")
    assert stored.risk_band_source_id == risk_profile_service.effective_band(session, ALICE).source_id  # type: ignore[union-attr]
    alice_user = session.scalars(select(User).where(User.username == "alice.customer")).one()
    assert stored.created_by == alice_user.id
    audit = session.scalars(select(AuditEvent).where(AuditEvent.action == "RECOMMENDATION_CREATED")).one()
    assert (audit.entity_type, audit.entity_id, audit.actor_role) == ("recommendation", view.id, "CUSTOMER")
    assert audit.details == {"template_version_no": 1, "horizon_rule": "NO_GOAL"}


@pytest.mark.ac("AC-02")
def test_ac_02_band_follows_newest_assessment(session: Session) -> None:
    """AC-02.2: ANS_0 -> CONSERVATIVE 20/60/10/10; then ANS_28 -> AGGRESSIVE 75/15/7.50/2.50."""
    _assess(session, BOB, ANS_0)
    first = _recommend(session, BOB)
    _assess(session, BOB, ANS_28, NOW + timedelta(minutes=1))
    second = _recommend(session, BOB, at=NOW + timedelta(minutes=2))

    assert (first.risk_band, first.allocation) == (RiskBand.CONSERVATIVE, _row("20.00", "60.00", "10.00", "10.00"))
    assert (second.risk_band, second.allocation) == (RiskBand.AGGRESSIVE, _row("75.00", "15.00", "7.50", "2.50"))
    assert _counts(session) == (2, 8, 2)


@pytest.mark.ac("AC-02")
def test_ac_02_no_effective_band_is_409_and_persists_nothing(session: Session) -> None:
    """AC-02.5: carol has no assessment or override -> 409 RISK_PROFILE_REQUIRED; no rows written."""
    with pytest.raises(ServiceError) as raised:
        _recommend(session, CAROL)

    assert (raised.value.status, raised.value.code) == (409, "RISK_PROFILE_REQUIRED")
    session.rollback()
    assert _counts(session) == (0, 0, 0)


@pytest.mark.ac("AC-04")
def test_ac_04_goal_of_another_customer_is_404_and_persists_nothing(session: Session) -> None:
    """recommendation §2.2 (AC-04.1 precondition): alice naming grace's goal B -> 404 GOAL_NOT_FOUND; no rows."""
    _assess(session, ALICE, ANS_16)

    with pytest.raises(ServiceError) as raised:
        _recommend(session, ALICE, GRACE_GOAL_B)

    assert (raised.value.status, raised.value.code) == (404, "GOAL_NOT_FOUND")
    session.rollback()
    assert _counts(session) == (0, 0, 0)


@pytest.mark.ac("AC-02")
def test_ac_02_corrupted_published_template_raises_and_persists_nothing(session: Session) -> None:
    """AC-02.4: active PUBLISHED template whose MODERATE row sums to 99.99 -> 422 TEMPLATE_INVALID; no rows."""
    _assess(session, ALICE, ANS_16)
    corrupted = template_with("MODERATE", "CASH", "4.99")
    session.add(TemplateVersion(version_no=2, status=PolicyStatus.PUBLISHED, definition=corrupted))
    session.commit()

    with pytest.raises(ServiceError) as raised:
        _recommend(session, ALICE)

    assert (raised.value.status, raised.value.code) == (422, "TEMPLATE_INVALID")
    assert "MODERATE sum=99.99" in raised.value.message
    session.rollback()
    assert _counts(session) == (0, 0, 0)


@pytest.mark.ac("AC-04")
def test_ac_04_named_goal_48_months_shifts_20_points(session: Session) -> None:
    """AC-04.1: MODERATE, clock 2026-01-15, frank's goal 2030-01-15 -> 48 months, H_36_59, 30/55/10/5."""
    _assess(session, FRANK, ANS_16)

    view = _recommend(session, FRANK, FRANK_GOAL)

    assert (view.goal_id, view.horizon_months, view.horizon_rule) == (FRANK_GOAL, 48, "H_36_59")
    assert view.allocation == _row("30.00", "55.00", "10.00", "5.00")
    assert view.as_of_date == date(2026, 1, 15)
    stored = session.get(Recommendation, view.id)
    assert stored is not None
    assert (stored.goal_id, stored.horizon_months, stored.horizon_rule) == (FRANK_GOAL, 48, "H_36_59")


@pytest.mark.ac("AC-04")
def test_ac_04_primary_goal_used_when_goal_id_omitted(session: Session) -> None:
    """AC-04.3: grace's goals A (P2, 2040-01-01) and B (P1, 2028-06-30), clock 2026-01-15 -> B, 29, H_12_35."""
    _assess(session, GRACE, ANS_16)

    view = _recommend(session, GRACE)

    assert (view.goal_id, view.horizon_months, view.horizon_rule) == (GRACE_GOAL_B, 29, "H_12_35")
    assert view.allocation == _row("20.00", "65.00", "10.00", "5.00")


@pytest.mark.ac("AC-04")
def test_ac_04_two_identical_requests_store_two_identical_rows_newest_first(session: Session) -> None:
    """AC-04.4: same clock date, band and goal -> identical outputs, distinct ids; latest/list newest first."""
    _assess(session, FRANK, ANS_16)
    assert recommendation_service.latest_for(session, FRANK) is None
    assert recommendation_service.list_for(session, FRANK) == []

    first = _recommend(session, FRANK, FRANK_GOAL, NOW)
    second = _recommend(session, FRANK, FRANK_GOAL, NOW + timedelta(seconds=1))

    assert first.id != second.id
    same = ("allocation", "horizon_months", "horizon_rule", "template_version_no", "risk_band", "as_of_date")
    assert all(getattr(first, f) == getattr(second, f) for f in same)
    assert _counts(session) == (2, 8, 2)
    assert recommendation_service.latest_for(session, FRANK) == second
    assert [v.id for v in recommendation_service.list_for(session, FRANK)] == [second.id, first.id]
    assert recommendation_service.list_for(session, FRANK) == [second, first]
    assert recommendation_service.list_for(session, ALICE) == []


@pytest.mark.ac("AC-04")
def test_ac_04_stored_recommendation_is_append_only(session: Session) -> None:
    """AC-04.4 (NFR-02): an UPDATE on a stored recommendation raises AppendOnlyViolation."""
    _assess(session, ALICE, ANS_16)
    view = _recommend(session, ALICE)
    stored = session.get(Recommendation, view.id)
    assert stored is not None

    stored.horizon_rule = "H_0_11"
    with pytest.raises(AppendOnlyViolation):
        session.flush()
