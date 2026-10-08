"""risk_assessments data access (risk_profile_spec §3). Append-only: add and list only, no update or delete (NFR-02)."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.bands import RiskBand
from app.repositories.models import RiskAssessment, RiskPolicyVersion


@dataclass(frozen=True)
class AssessmentRecord:
    """A stored assessment with the version number of the policy it was scored under."""

    id: str
    created_at: datetime
    assigned_band: RiskBand
    policy_version_no: int


def _utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; every stored timestamp is UTC (app_spec §5.2)."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def add(
    session: Session,
    *,
    customer_id: str,
    risk_policy_version_id: str,
    answers: list[dict[str, str]],
    total_score: int,
    computed_band: RiskBand,
    assigned_band: RiskBand,
    applied_caps: list[str],
    created_at: datetime,
) -> RiskAssessment:
    """Insert one assessment in the caller's transaction (flushed so its id is available)."""
    row = RiskAssessment(
        customer_id=customer_id,
        risk_policy_version_id=risk_policy_version_id,
        answers=answers,
        total_score=total_score,
        computed_band=computed_band,
        assigned_band=assigned_band,
        applied_caps=applied_caps,
        created_at=created_at,
    )
    session.add(row)
    session.flush()
    return row


def list_for_customer(session: Session, customer_id: str) -> list[AssessmentRecord]:
    """The customer's assessments, newest first by (created_at, id) (risk_profile_spec §2.5)."""
    stmt = (
        select(RiskAssessment.id, RiskAssessment.created_at, RiskAssessment.assigned_band, RiskPolicyVersion.version_no)
        .join(RiskPolicyVersion, RiskPolicyVersion.id == RiskAssessment.risk_policy_version_id)
        .where(RiskAssessment.customer_id == customer_id)
        .order_by(RiskAssessment.created_at.desc(), RiskAssessment.id.desc())
    )
    return [
        AssessmentRecord(id_, _utc(created), band, version_no)
        for id_, created, band, version_no in session.execute(stmt)
    ]
