"""NFR-02 append-only records; AC-10.3 published versions immutable; AC-10.7 one draft per policy type."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import build_engine, build_session_factory
from app.domain.bands import RiskBand
from app.domain.policy import PolicyStatus
from app.repositories.errors import AppendOnlyViolation, PublishedVersionMutation
from app.repositories.models import (
    AuditEvent,
    Recommendation,
    RecommendationAllocation,
    RiskAssessment,
    RiskPolicyVersion,
    TemplateVersion,
)

ALICE = "00000000-0000-4000-8000-00000000c001"
RP_V1 = "00000000-0000-4000-8000-000000000201"
TV_V1 = "00000000-0000-4000-8000-000000000101"


@pytest.fixture
def session(migrated_db_copy: Path) -> Iterator[Session]:
    engine = build_engine(f"sqlite:///{migrated_db_copy}")
    with build_session_factory(engine)() as s:
        yield s
    engine.dispose()


def _assessment() -> RiskAssessment:
    return RiskAssessment(
        customer_id=ALICE,
        risk_policy_version_id=RP_V1,
        answers=[],
        total_score=16,
        computed_band=RiskBand.MODERATE,
        assigned_band=RiskBand.MODERATE,
        applied_caps=[],
    )


def _recommendation() -> Recommendation:
    return Recommendation(
        customer_id=ALICE,
        source="SYSTEM",
        risk_band=RiskBand.MODERATE,
        risk_band_source_id=RP_V1,
        template_version_id=TV_V1,
        horizon_rule="NO_GOAL",
        as_of_date=date(2026, 1, 15),
        created_by=ALICE,
    )


@pytest.mark.ac("AC-01")
def test_ac_01_risk_assessment_update_and_delete_raise_append_only(session: Session) -> None:
    """AC-01.7 — an attempted UPDATE on risk_assessments raises AppendOnlyViolation (NFR-02)."""
    row = _assessment()
    session.add(row)
    session.commit()

    row.assigned_band = RiskBand.AGGRESSIVE
    with pytest.raises(AppendOnlyViolation):
        session.flush()
    session.rollback()
    session.delete(session.get(RiskAssessment, row.id))
    with pytest.raises(AppendOnlyViolation):
        session.flush()


@pytest.mark.parametrize("make", ["recommendation", "allocation", "audit"])
def test_recommendations_allocations_and_audit_are_append_only(session: Session, make: str) -> None:
    """NFR-02 — recommendations, their allocation rows and audit events are insert-only."""
    rec = _recommendation()
    session.add(rec)
    session.flush()
    if make == "recommendation":
        target: object = rec
    elif make == "allocation":
        target = RecommendationAllocation(
            recommendation_id=rec.id, asset_class_code="EQUITY", target_pct=Decimal("50.00")
        )
    else:
        target = AuditEvent(
            actor_role="SYSTEM", action="TEST", entity_type="recommendation", entity_id=rec.id, details={}
        )
    session.add(target)
    session.commit()

    session.delete(target)
    with pytest.raises(AppendOnlyViolation):
        session.flush()


@pytest.mark.ac("AC-10")
@pytest.mark.parametrize("model", [RiskPolicyVersion, TemplateVersion])
def test_ac_10_published_versions_reject_update_and_keep_definition(session: Session, model: type) -> None:
    """AC-10.3 — ORM update of a PUBLISHED risk policy or template raises; the stored definition is unchanged."""
    v1 = session.scalars(select(model).where(model.version_no == 1)).one()
    before = dict(v1.definition)

    v1.definition = {**before, "tampered": True}
    with pytest.raises(PublishedVersionMutation):
        session.flush()
    session.rollback()

    assert session.scalars(select(model).where(model.version_no == 1)).one().definition == before


@pytest.mark.ac("AC-10")
def test_ac_10_only_one_draft_per_policy_type(session: Session) -> None:
    """AC-10.7 — the partial unique index allows a single DRAFT row per version table."""
    session.add(RiskPolicyVersion(version_no=2, status=PolicyStatus.DRAFT, definition={}))
    session.commit()
    session.add(RiskPolicyVersion(version_no=3, status=PolicyStatus.DRAFT, definition={}))
    with pytest.raises(IntegrityError):
        session.commit()
