"""Holdings and drift API endpoints (holdings_spec §4, AC-05)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db, require_role
from app.api.routers import API_V1
from app.api.schemas.holdings import HoldingLineResponse, HoldingsResponse, fmt2, fmt4
from app.core.clock import Clock
from app.core.security import Principal, Role
from app.services import holdings_service
from app.services.customer_resolver import customer_id_for

router = APIRouter(prefix=API_V1 + "/holdings", tags=["holdings"])


@router.get("", response_model=HoldingsResponse)
def get_customer_holdings(
    principal: Annotated[Principal, Depends(require_role(Role.CUSTOMER))],
    session: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> HoldingsResponse:
    """Return the customer's holdings, values, and allocation drift against latest recommendation."""
    customer_id = customer_id_for(session, principal)
    view = holdings_service.get_holdings(session, customer_id)

    lines = [
        HoldingLineResponse(
            asset_class=line.asset_class,
            units=fmt4(line.units) or "0.0000",
            nav=fmt4(line.nav) or "0.0000",
            current_value=fmt2(line.current_value) or "0.00",
            current_pct=fmt2(line.current_pct),
            target_pct=fmt2(line.target_pct),
            drift_pct=fmt2(line.drift_pct),
            breached=line.breached,
        )
        for line in view.lines
    ]

    return HoldingsResponse(
        nav_date=view.nav_date,
        total_value=fmt2(view.total_value) or "0.00",
        has_target=view.has_target,
        recommendation_id=view.recommendation_id,
        template_version_no=view.template_version_no,
        drift_threshold_pct=fmt2(view.drift_threshold_pct),
        portfolio_breached=view.portfolio_breached,
        lines=lines,
    )
