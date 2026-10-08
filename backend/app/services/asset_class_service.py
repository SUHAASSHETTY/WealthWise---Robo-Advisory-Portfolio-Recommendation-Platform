"""Admin asset classes service (admin_versioning_spec §2.5, §4, AC-10)."""

import json
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.security import Principal
from app.repositories import asset_class_repository, audit_repository, policy_version_repository
from app.repositories.models.reference import AssetClass
from app.repositories.models.template_version import TemplateVersion
from app.services.customer_resolver import user_id_for
from app.services.errors import conflict, not_found, unprocessable

logger = logging.getLogger(__name__)

CODE_RE = re.compile(r"^[A-Z_]{2,20}$")
ACTION_CHANGED = "ASSET_CLASS_CHANGED"
ENTITY_TYPE = "asset_class"


@dataclass(frozen=True)
class AssetClassView:
    code: str
    name: str
    is_active: bool
    display_order: int
    created_at: datetime


def list_asset_classes(session: Session) -> Sequence[AssetClassView]:
    """List all asset classes ordered by display_order."""
    classes = asset_class_repository.list_all(session)
    return [
        AssetClassView(
            code=c.code,
            name=c.name,
            is_active=c.is_active,
            display_order=c.display_order,
            created_at=c.created_at,
        )
        for c in classes
    ]


def create_asset_class(
    session: Session,
    clock: Clock,
    principal: Principal,
    code: str,
    name: str,
    display_order: int,
) -> AssetClassView:
    """Create a new asset class (AC-10)."""
    code_upper = code.strip().upper()
    if not CODE_RE.match(code_upper):
        raise unprocessable(
            "ASSET_CLASS_CODE_INVALID",
            "Asset class code must be 2-20 uppercase letters or underscores.",
        )

    name_clean = name.strip()
    if not name_clean or len(name_clean) > 80:
        raise unprocessable("ASSET_CLASS_NAME_INVALID", "Name must be between 1 and 80 characters.")

    existing = asset_class_repository.get_by_code(session, code_upper)
    if existing is not None:
        raise conflict("ASSET_CLASS_EXISTS", f"Asset class {code_upper} already exists.")

    now = clock.now()
    ac = AssetClass(
        code=code_upper,
        name=name_clean,
        is_active=True,
        display_order=display_order,
        created_at=now,
    )
    asset_class_repository.create(session, ac)

    audit_repository.insert_audit_event(
        session,
        actor_user_id=user_id_for(session, principal),
        actor_role=principal.role.value,
        action=ACTION_CHANGED,
        entity_type=ENTITY_TYPE,
        entity_id=ac.code,
        details={"code": ac.code, "is_active": True},
    )
    session.commit()

    logger.info("asset class created", extra={"code": ac.code})
    return AssetClassView(
        code=ac.code,
        name=ac.name,
        is_active=ac.is_active,
        display_order=ac.display_order,
        created_at=ac.created_at,
    )


def patch_asset_class(
    session: Session,
    clock: Clock,
    principal: Principal,
    code: str,
    name: str | None = None,
    is_active: bool | None = None,
    display_order: int | None = None,
) -> AssetClassView:
    """Update asset class attributes, checking if in use before deactivating (AC-10)."""
    ac = asset_class_repository.get_by_code(session, code)
    if ac is None:
        raise not_found("ASSET_CLASS_NOT_FOUND", f"Asset class {code} not found.")

    if is_active is False:
        # Check if active published template version references this class
        active_template = policy_version_repository.active_published(session, TemplateVersion)
        if active_template is not None:
            defn = active_template.definition
            if isinstance(defn, str):
                defn = json.loads(defn)
            templates = defn.get("templates", {})
            in_use = any(code in band_alloc for band_alloc in templates.values())
            if in_use:
                raise conflict(
                    "ASSET_CLASS_IN_USE",
                    f"Cannot deactivate asset class '{code}' as it is referenced by the active template version.",
                )

    if name is not None:
        name_clean = name.strip()
        if not name_clean or len(name_clean) > 80:
            raise unprocessable("ASSET_CLASS_NAME_INVALID", "Name must be between 1 and 80 characters.")
        ac.name = name_clean

    if is_active is not None:
        ac.is_active = is_active

    if display_order is not None:
        ac.display_order = display_order

    audit_repository.insert_audit_event(
        session,
        actor_user_id=user_id_for(session, principal),
        actor_role=principal.role.value,
        action=ACTION_CHANGED,
        entity_type=ENTITY_TYPE,
        entity_id=ac.code,
        details={"code": ac.code, "is_active": ac.is_active},
    )
    session.commit()

    logger.info("asset class updated", extra={"code": ac.code})
    return AssetClassView(
        code=ac.code,
        name=ac.name,
        is_active=ac.is_active,
        display_order=ac.display_order,
        created_at=ac.created_at,
    )
