"""E1-S3 / E1-S1 foundation: clock injection, principal → customer, ServiceError envelope, shared repositories."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import FixedClock, SystemClock
from app.core.config import Settings
from app.core.db import build_engine, build_session_factory
from app.core.security import Principal, Role, resolve_stub_token
from app.domain.policy import PolicyStatus
from app.main import create_app
from app.repositories import audit_repository, customer_repository, goal_repository, policy_version_repository
from app.repositories.models import AuditEvent, RiskPolicyVersion, TemplateVersion
from app.services.customer_resolver import customer_id_for
from app.services.errors import ServiceError

CUSTOMERS = {
    "alice.customer": "00000000-0000-4000-8000-00000000c001",
    "bob.customer": "00000000-0000-4000-8000-00000000c002",
    "carol.customer": "00000000-0000-4000-8000-00000000c003",
    "frank.customer": "00000000-0000-4000-8000-00000000c004",
    "grace.customer": "00000000-0000-4000-8000-00000000c005",
}


@pytest.fixture
def session(migrated_db_copy: Path) -> Iterator[Session]:
    engine = build_engine(f"sqlite:///{migrated_db_copy}")
    with build_session_factory(engine)() as s:
        yield s
    engine.dispose()


def test_app_clock_defaults_to_system_and_honours_fixed_clock_setting(settings: Settings) -> None:
    assert isinstance(create_app(settings).state.clock, SystemClock)

    pinned = settings.model_copy(update={"fixed_clock": datetime(2026, 1, 15, 9, 0, tzinfo=UTC)})
    assert create_app(pinned).state.clock.today() == date(2026, 1, 15)

    explicit = create_app(settings, clock=FixedClock(datetime(2026, 1, 31, tzinfo=UTC)))
    assert explicit.state.clock.today() == date(2026, 1, 31)


def test_fixed_clock_parses_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEALTHWISE_FIXED_CLOCK", "2026-01-15T09:00:00Z")
    assert Settings(_env_file=None).fixed_clock == datetime(2026, 1, 15, 9, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("token", "username"), [("stub-token-frank", "frank.customer"), ("stub-token-grace", "grace.customer")]
)
def test_frank_and_grace_stub_tokens_are_customers(token: str, username: str) -> None:
    assert resolve_stub_token(token, enabled=True) == Principal(username, Role.CUSTOMER)


@pytest.mark.parametrize(("username", "customer_id"), sorted(CUSTOMERS.items()))
def test_customer_principal_resolves_to_seeded_customer(session: Session, username: str, customer_id: str) -> None:
    assert customer_id_for(session, Principal(username, Role.CUSTOMER)) == customer_id


@pytest.mark.parametrize(
    "principal", [Principal("dan.advisor", Role.ADVISOR), Principal("ghost.customer", Role.CUSTOMER)]
)
def test_non_customer_principal_is_rejected(session: Session, principal: Principal) -> None:
    with pytest.raises(ServiceError) as excinfo:
        customer_id_for(session, principal)
    assert excinfo.value.status == 403


def test_service_error_maps_to_error_envelope(settings: Settings) -> None:
    app = create_app(settings)
    router = APIRouter()

    @router.get("/probe/conflict")
    def conflict() -> None:
        raise ServiceError(409, "POLICY_VERSION_STALE", "Refetch the questionnaire.", {"active_version_no": 2})

    app.include_router(router)
    with TestClient(app) as client:
        response = client.get("/probe/conflict")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "POLICY_VERSION_STALE",
            "message": "Refetch the questionnaire.",
            "details": {"active_version_no": 2},
        }
    }


def test_active_published_is_highest_published_version(session: Session) -> None:
    session.add(TemplateVersion(version_no=2, status=PolicyStatus.DRAFT, definition={}))
    session.commit()

    active = policy_version_repository.active_published(session, TemplateVersion)
    assert active is not None and active.version_no == 1
    assert policy_version_repository.next_version_no(session, TemplateVersion) == 3
    assert policy_version_repository.draft(session, TemplateVersion) is not None
    assert policy_version_repository.draft(session, RiskPolicyVersion) is None


def test_goals_and_customers_are_scoped_reads(session: Session) -> None:
    grace = CUSTOMERS["grace.customer"]
    assert {g.id[-6:] for g in goal_repository.list_for_customer(session, grace)} == {"0a0001", "0b0001"}
    assert (
        goal_repository.get_for_customer(session, CUSTOMERS["alice.customer"], "00000000-0000-4000-8000-0000000b0001")
        is None
    )
    assert customer_repository.get_by_username(session, "carol.customer").kyc_verified is False  # type: ignore[union-attr]


def test_audit_event_carries_correlation_id(session: Session) -> None:
    from app.core.logging import reset_correlation_id, set_correlation_id

    token = set_correlation_id("req-audit-1")
    try:
        audit_repository.insert_audit_event(
            session,
            actor_user_id="u-1",
            actor_role="ADMIN",
            action="POLICY_PUBLISHED",
            entity_type="template_version",
            entity_id="t-1",
            details={"version_no": 2},
        )
        session.commit()
    finally:
        reset_correlation_id(token)

    event = session.scalars(select(AuditEvent)).one()
    assert (event.action, event.correlation_id, event.details) == ("POLICY_PUBLISHED", "req-audit-1", {"version_no": 2})
    assert session.scalar(select(func.count()).select_from(AuditEvent)) == 1


def test_fixed_clock_setting_anchors_date_but_keeps_time_moving(settings: Settings) -> None:
    """app_spec §5.2 — evaluator runs pin today() yet keep created_at strictly increasing (newest is unambiguous)."""
    pinned = settings.model_copy(update={"fixed_clock": datetime(2026, 1, 15, 9, 0, tzinfo=UTC)})
    clock = create_app(pinned).state.clock

    first, second = clock.now(), clock.now()

    assert second > first
    assert first >= datetime(2026, 1, 15, 9, 0, tzinfo=UTC)
    assert clock.today() == date(2026, 1, 15)
