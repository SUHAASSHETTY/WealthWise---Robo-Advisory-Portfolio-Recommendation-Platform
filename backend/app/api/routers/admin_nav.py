"""Admin NAV feed API endpoints (admin_versioning_spec §4, AC-05.3, AC-08.2)."""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db, require_role
from app.api.routers import API_V1
from app.core.clock import Clock
from app.core.security import Principal, Role
from app.services import nav_feed_service

router = APIRouter(prefix=API_V1 + "/admin/nav-refresh", tags=["admin-nav"])


@router.post("")
def refresh_nav_feed(
    principal: Annotated[Principal, Depends(require_role(Role.ADMIN))],
    session: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
    response: Response,
    target_date: date | None = None,
) -> dict[str, Any]:
    """Trigger daily NAV refresh from nav_series.csv and snapshot goal progress."""
    result = nav_feed_service.refresh_nav(session, clock, target_date=target_date)
    if result.get("status") == "ALREADY_LOADED":
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_201_CREATED
    return result
