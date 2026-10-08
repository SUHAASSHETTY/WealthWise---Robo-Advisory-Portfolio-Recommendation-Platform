"""Queries shared by both versioned-policy tables (risk_policy_versions, template_versions)."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.policy import PolicyStatus
from app.repositories.models import RiskPolicyVersion, TemplateVersion


def active_published[V: RiskPolicyVersion | TemplateVersion](session: Session, model: type[V]) -> V | None:
    """The PUBLISHED version with the highest version_no (admin_versioning_spec §2.1)."""
    stmt = select(model).where(model.status == PolicyStatus.PUBLISHED).order_by(model.version_no.desc()).limit(1)
    return session.scalars(stmt).first()


def get[V: RiskPolicyVersion | TemplateVersion](session: Session, model: type[V], version_id: str) -> V | None:
    return session.get(model, version_id)


def list_all[V: RiskPolicyVersion | TemplateVersion](session: Session, model: type[V]) -> list[V]:
    return list(session.scalars(select(model).order_by(model.version_no)))


def draft[V: RiskPolicyVersion | TemplateVersion](session: Session, model: type[V]) -> V | None:
    return session.scalars(select(model).where(model.status == PolicyStatus.DRAFT)).first()


def next_version_no[V: RiskPolicyVersion | TemplateVersion](session: Session, model: type[V]) -> int:
    return int(session.scalar(select(func.coalesce(func.max(model.version_no), 0))) or 0) + 1


def insert_draft[V: RiskPolicyVersion | TemplateVersion](
    session: Session, model: type[V], definition: dict[str, Any], created_by: str | None
) -> V:
    row = model(
        version_no=next_version_no(session, model),
        status=PolicyStatus.DRAFT,
        definition=definition,
        created_by=created_by,
    )
    session.add(row)
    session.flush()
    return row
