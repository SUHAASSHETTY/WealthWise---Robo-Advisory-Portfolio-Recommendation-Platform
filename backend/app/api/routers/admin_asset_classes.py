"""Admin asset classes API endpoints (admin_versioning_spec §4, AC-10)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db, require_role
from app.api.routers import API_V1
from app.api.schemas.asset_classes import AssetClassCreateIn, AssetClassOut, AssetClassPatchIn
from app.core.clock import Clock
from app.core.security import Principal, Role
from app.services import asset_class_service

router = APIRouter(prefix=API_V1 + "/admin/asset-classes", tags=["admin-asset-classes"])


@router.get("", response_model=list[AssetClassOut])
def list_asset_classes(
    principal: Annotated[Principal, Depends(require_role(Role.ADMIN))],
    session: Annotated[Session, Depends(get_db)],
) -> list[AssetClassOut]:
    """List all asset classes ordered by display_order (AC-10)."""
    views = asset_class_service.list_asset_classes(session)
    return [
        AssetClassOut(
            code=v.code,
            name=v.name,
            is_active=v.is_active,
            display_order=v.display_order,
            created_at=v.created_at,
        )
        for v in views
    ]


@router.post("", response_model=AssetClassOut, status_code=status.HTTP_201_CREATED)
def create_asset_class(
    payload: AssetClassCreateIn,
    principal: Annotated[Principal, Depends(require_role(Role.ADMIN))],
    session: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> AssetClassOut:
    """Create a new asset class (AC-10)."""
    v = asset_class_service.create_asset_class(
        session=session,
        clock=clock,
        principal=principal,
        code=payload.code,
        name=payload.name,
        display_order=payload.display_order,
    )
    return AssetClassOut(
        code=v.code,
        name=v.name,
        is_active=v.is_active,
        display_order=v.display_order,
        created_at=v.created_at,
    )


@router.patch("/{code}", response_model=AssetClassOut)
def patch_asset_class(
    code: str,
    payload: AssetClassPatchIn,
    principal: Annotated[Principal, Depends(require_role(Role.ADMIN))],
    session: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> AssetClassOut:
    """Update asset class attributes, checking if in use before deactivating (AC-10)."""
    v = asset_class_service.patch_asset_class(
        session=session,
        clock=clock,
        principal=principal,
        code=code.upper(),
        name=payload.name,
        is_active=payload.is_active,
        display_order=payload.display_order,
    )
    return AssetClassOut(
        code=v.code,
        name=v.name,
        is_active=v.is_active,
        display_order=v.display_order,
        created_at=v.created_at,
    )
