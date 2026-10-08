"""Audit writer (app_spec §5.4). Called inside the caller's transaction; `details` must hold no PII or values."""

from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_correlation_id
from app.repositories.models import AuditEvent


def insert_audit_event(
    session: Session,
    *,
    actor_user_id: str | None,
    actor_role: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict[str, Any],
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        correlation_id=get_correlation_id(),
        details=details,
    )
    session.add(event)
    return event
