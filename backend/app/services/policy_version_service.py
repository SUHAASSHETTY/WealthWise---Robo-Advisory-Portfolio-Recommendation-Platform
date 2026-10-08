"""Draft → publish lifecycle for risk-policy and template versions (admin_versioning_spec §2.1-2.3, AC-10).

Published versions are never mutated: edits create a new DRAFT copied from the active version; the ORM guard
(repositories.guards) is the last line of defence behind the 409 checks here.
"""

import copy
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.domain.policy import PolicyStatus
from app.domain.template_version_validator import validate_risk_policy, validate_template_version
from app.repositories import audit_repository, customer_repository, policy_version_repository
from app.repositories.models import RiskPolicyVersion, TemplateVersion
from app.services.errors import ServiceError, conflict, not_found

logger = logging.getLogger(__name__)
VersionRow = RiskPolicyVersion | TemplateVersion


class PolicyKind(StrEnum):
    RISK_POLICY = "risk_policy"
    TEMPLATE = "template"


@dataclass(frozen=True)
class _KindConfig:
    model: type[RiskPolicyVersion] | type[TemplateVersion]
    invalid_code: str
    validate: Callable[[Session, dict[str, Any]], list[str]]


def _validate_template(session: Session, definition: dict[str, Any]) -> list[str]:
    return validate_template_version(definition, customer_repository.active_asset_class_codes(session))


def _validate_risk(_session: Session, definition: dict[str, Any]) -> list[str]:
    return validate_risk_policy(definition)


_KINDS = {
    PolicyKind.RISK_POLICY: _KindConfig(RiskPolicyVersion, "POLICY_INVALID", _validate_risk),
    PolicyKind.TEMPLATE: _KindConfig(TemplateVersion, "TEMPLATE_INVALID", _validate_template),
}


@dataclass(frozen=True)
class Actor:
    user_id: str | None
    role: str


def _audit(session: Session, actor: Actor, action: str, kind: PolicyKind, row: VersionRow) -> None:
    audit_repository.insert_audit_event(
        session,
        actor_user_id=actor.user_id,
        actor_role=actor.role,
        action=action,
        entity_type=f"{kind.value}_version",
        entity_id=row.id,
        details={"version_no": row.version_no},
    )
    logger.info("policy version changed", extra={"action": action, "entity_id": row.id, "version_no": row.version_no})


def list_versions(session: Session, kind: PolicyKind) -> Sequence[VersionRow]:
    return policy_version_repository.list_all(session, _KINDS[kind].model)


def get_version(session: Session, kind: PolicyKind, version_id: str) -> VersionRow:
    row = policy_version_repository.get(session, _KINDS[kind].model, version_id)
    if row is None:
        raise not_found("POLICY_VERSION_NOT_FOUND", "No such policy version.")
    return row


def _require_draft(row: VersionRow) -> None:
    if row.status == PolicyStatus.PUBLISHED:
        raise conflict("POLICY_VERSION_IMMUTABLE", f"Version {row.version_no} is published and cannot change.")


def create_draft(session: Session, kind: PolicyKind, actor: Actor) -> VersionRow:
    model = _KINDS[kind].model
    if policy_version_repository.draft(session, model) is not None:
        raise conflict("DRAFT_EXISTS", "A draft already exists; edit or delete it first.")
    active = policy_version_repository.active_published(session, model)
    definition = copy.deepcopy(active.definition) if active is not None else {}
    row = policy_version_repository.insert_draft(session, model, definition, actor.user_id)
    _audit(session, actor, "POLICY_DRAFT_CREATED", kind, row)
    session.commit()
    return row


def update_draft(
    session: Session, kind: PolicyKind, version_id: str, definition: dict[str, Any], actor: Actor
) -> VersionRow:
    row = get_version(session, kind, version_id)
    _require_draft(row)
    row.definition = definition
    _audit(session, actor, "POLICY_DRAFT_UPDATED", kind, row)
    session.commit()
    return row


def delete_draft(session: Session, kind: PolicyKind, version_id: str, actor: Actor) -> None:
    row = get_version(session, kind, version_id)
    _require_draft(row)
    _audit(session, actor, "POLICY_DRAFT_DELETED", kind, row)
    session.delete(row)
    session.commit()


def publish(session: Session, kind: PolicyKind, version_id: str, actor: Actor, clock: Clock) -> VersionRow:
    config = _KINDS[kind]
    row = get_version(session, kind, version_id)
    if row.status == PolicyStatus.PUBLISHED:
        raise conflict("ALREADY_PUBLISHED", f"Version {row.version_no} is already published.")
    violations = config.validate(session, row.definition)
    if violations:
        raise ServiceError(422, config.invalid_code, "Definition fails publish validation.", {"violations": violations})
    row.status = PolicyStatus.PUBLISHED
    row.published_at = clock.now()
    row.published_by = actor.user_id
    _audit(session, actor, "POLICY_PUBLISHED", kind, row)
    session.commit()
    return row
